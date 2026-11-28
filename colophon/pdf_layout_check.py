# Copyright (C) 2026 Inkmirage (Endleaf render worker modifications)
# SPDX-License-Identifier: AGPL-3.0-or-later
"""ENDLEAF-R81. Warn-only read of the rendered PDF, after the final TeX pass.

Vector-native (ENDLEAF-R81-VECTOR): glyph and path geometry come from the PDF
content stream through pdfminer.six (layout analysis off, so paint order is
kept). shapely 2 answers overlap and containment, scipy's cKDTree gives the
nearest neighbours for grouping. No rasteriser, no ML model and no AGPL PDF
library (a test asserts none is imported). Lengths are PDF points (1/72 in) with a
top-left origin; ``em`` is the glyph's own font size.

Eight codes, all warn-only (``REFUSE_ENABLED`` stays false): pdf_margin_escape,
pdf_caption_overlap, pdf_label_on_stroke, pdf_text_escapes_node,
pdf_text_overlap, pdf_label_gutter, pdf_stray_source, pdf_empty_page. A
finding is one job-warning item::

  {"code": "pdf_text_overlap", "packages": ["pdf"], "message": "pg3: 'a' overlaps 'b'",
   "page": 3, "box": [x0, top, x1, bottom], "regionCount": 1,
   "overMm": 0.4,        # where the code has one
   "partId": "p2",       # fulldoc, from the layout marks
   "fenceNumber": 2}     # document-shell fence on that page

The message has no Fix line: the gate appends the code's Fix. At most
``MAX_FINDINGS`` are listed; ``pdf_more_findings`` counts the rest. An overrun
of the time budget or any exception ends the checks and adds one
``pdf_check_skipped`` note. The worker sends the items as one
``ENDLEAF_PDFLAYOUT`` stderr line; the runner appends them to the job's
``warnings`` beside ``layout_overhang``.
"""

import io
import json
import logging
import math
import re
import time
import unicodedata
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

PDF_PREFIX = "ENDLEAF_PDFLAYOUT "
PDF_LOG_PREFIX = "ENDLEAF_PDFLOG "
PACKAGES = ["pdf"]
SKIP_CODE = "pdf_check_skipped"
MORE_CODE = "pdf_more_findings"
CODES = (
    "pdf_margin_escape",
    "pdf_caption_overlap",
    "pdf_label_on_stroke",
    "pdf_text_escapes_node",
    "pdf_text_overlap",
    "pdf_label_gutter",
    "pdf_stray_source",
    "pdf_empty_page",
)
# ENDLEAF-R81-WARN. No code refuses; a later requirement turns one on.
REFUSE_ENABLED = {code: False for code in CODES}
IMPORTS_AGPL_PDF_LIBRARY = False  # OD-PDF-13: permissive libraries only

# PdfLayoutChecker attributes (ENDLEAF-R81-GROUP, -REGION, -CHECKS, -BUDGET).
BEZIER_CHORDS = 8
WORD_GAP_EM = 0.10
LINE_JOIN_EM = 1.5
LINE_NEIGHBOURS = 24
WORD_NEIGHBOURS = 12
# Glyphs that overlap by more than this are two words (heavy kerning such as V-a stays one
# word), and a word has one size.
OVERPRINT_EM = 0.2  # inside one word only an overlap wider than this counts
WORD_OVERLAP_EM = 0.35
SAME_SIZE_PT = 0.1
BLOCK_EXTRA_LEADING_EM = 0.25
GUARD_LOW_EM = 0.03
GUARD_HIGH_EM = 0.17
FIGURE_REGION_GAP_PT = 3.0 * 72.0 / 25.4
MARGIN_ESCAPE_MIN_PT = 1.0
OVERLAP_MIN_PT = 0.4
CORE_SHRINK_V_EM = 0.2
CORE_SHRINK_H_EM = 0.05
NODE_ESCAPE_MIN_PT = 0.5
NODE_INSIDE_MIN = 0.05
NODE_INSIDE_MAX = 0.95
NODE_MIN_WIDTH_EM = 2.0
SAME_BASELINE_PT = 0.1
LABEL_GUTTER_PT = 0.5 * 72.0 / 25.4
GUTTER_BASELINE_SHIFT_PT = 0.5
GUTTER_SIZE_SHIFT_PT = 0.1
NEAR_EMPTY_MAX_WORDS = 5
PAGE_BUDGET_SEC = 0.250
DOCUMENT_BUDGET_SEC = 2.0
MAX_FINDINGS = 10
GUTTER_KINDS = frozenset({"sysml"})  # OD-PDF-6
STRAY_SOURCE_KINDS = frozenset({"document-shell", "fulldoc"})  # OD-PDF-7
TEX_PT_TO_BP = 72.0 / 72.27
_MM_PER_PT = 25.4 / 72.0
_COS_SAME_ANGLE = 0.995

_CAPTION = re.compile(r"^(Figure|Table|圖|表)\s*\d+[:：.]")
# TeX prints a typed backtick as a left quote, so a run of those is a fence too.
_STRAY = re.compile(r"([`‘]{3,}|~~~+)\s*\w*|\\(?:[A-Za-z]{2,}|[\[\]])(?:\{[^}]*\})?")
_FOLIO = re.compile(r"^\d{1,4}$")
_MONO_FONT = re.compile(r"mono|courier|typewriter|cursor|consol|menlo", re.IGNORECASE)
# Pieces TeX overlaps to build long arrows and rules.
_EXTENSIBLE = frozenset("-−‐‑‒–—―=⁼←→↔↑↓⇐⇒⇔⟵⟶⟷⟸⟹⟺↦⟼⟻⟽↼⇀↽⇁─━│┃⎯")


class CheckSkipped(Exception):
    """The budget ran out; the findings so far are kept."""


@dataclass
class Hit:
    code: str
    page: int
    box: tuple
    message: str
    over_mm: float | None = None
    pitch: float = 12.0
    count: int = 1
    severity: float = 0.0


@dataclass
class _Glyph:
    text: str
    size: float
    quad: object
    u: object
    v: object
    origin: object
    width: float
    z: int
    font: str


@dataclass
class _Path:
    z: int
    bbox: tuple
    polylines: list
    closed: bool
    single: bool
    stroke: bool
    fill: bool
    white: bool
    image: bool = False


@dataclass
class _Budget:
    clock: object
    page_sec: float
    document_sec: float
    start: float = 0.0
    page_start: float = 0.0
    last_page: int = 0

    def begin(self):
        self.start = self.page_start = self.clock()

    def begin_page(self):
        self.page_start = self.clock()

    def check(self):
        now = self.clock()
        if (
            now - self.page_start > self.page_sec
            or now - self.start > self.document_sec
        ):
            raise CheckSkipped("time budget")


@dataclass
class CheckResult:
    items: list = field(default_factory=list)
    log_lines: list = field(default_factory=list)


def _np():
    import numpy

    return numpy


def _normalise(text):
    return unicodedata.normalize("NFKC", text)


def _is_white(color):
    if color is None:
        return True
    values = color if isinstance(color, (tuple, list)) else (color,)
    values = [v for v in values if isinstance(v, (int, float))]
    if len(values) == 1:
        return values[0] >= 0.999
    if len(values) == 3:
        return min(values) >= 0.999
    if len(values) == 4:
        return max(values) <= 0.001
    return False


# ---- ENDLEAF-R81-VECTOR: extraction -------------------------------------------------


def _flatten(original, pts, height, y0, x0=0.0):
    """(polylines, closed, single) from a pdfminer path, Beziers cut to 8 chords."""
    polylines, current, closed_flags = [], [], []

    def flip(point):
        return (float(point[0] - x0), float(height - (point[1] - y0)))

    def end_current(closed):
        nonlocal current
        if len(current) >= 2:
            polylines.append(current)
            closed_flags.append(closed)
        current = []

    if not original:
        current = [flip(p) for p in pts]
        end_current(len(pts) > 2 and tuple(pts[0]) == tuple(pts[-1]))
    else:
        for segment in original:
            op = segment[0]
            coords = [flip(p) for p in segment[1:]]
            if op == "m":
                end_current(False)
                current = coords[:1]
            elif op == "l" and coords:
                current.append(coords[0])
            elif op == "c" and len(coords) >= 3 and current:
                p0, p1, p2, p3 = current[-1], coords[0], coords[1], coords[2]
                for step in range(1, BEZIER_CHORDS + 1):
                    t = step / BEZIER_CHORDS
                    s = 1 - t
                    current.append(
                        (
                            s**3 * p0[0]
                            + 3 * s * s * t * p1[0]
                            + 3 * s * t * t * p2[0]
                            + t**3 * p3[0],
                            s**3 * p0[1]
                            + 3 * s * s * t * p1[1]
                            + 3 * s * t * t * p2[1]
                            + t**3 * p3[1],
                        )
                    )
            elif op in ("v", "y") and len(coords) >= 2 and current:
                p0 = current[-1]
                p1 = p0 if op == "v" else coords[0]
                p2, p3 = (coords[0], coords[1]) if op == "v" else (coords[1], coords[1])
                for step in range(1, BEZIER_CHORDS + 1):
                    t = step / BEZIER_CHORDS
                    s = 1 - t
                    current.append(
                        (
                            s**3 * p0[0]
                            + 3 * s * s * t * p1[0]
                            + 3 * s * t * t * p2[0]
                            + t**3 * p3[0],
                            s**3 * p0[1]
                            + 3 * s * s * t * p1[1]
                            + 3 * s * t * t * p2[1]
                            + t**3 * p3[1],
                        )
                    )
            elif op == "h" and current:
                current.append(current[0])
                end_current(True)
        end_current(False)
    return polylines, bool(closed_flags) and all(closed_flags), len(polylines) == 1


def _aggregator_class():
    from pdfminer.converter import PDFPageAggregator

    class _Aggregator(PDFPageAggregator):
        """Keeps the font size, descent and rise of each glyph (the quad needs them)."""

        def render_char(
            self, matrix, font, fontsize, scaling, rise, cid, ncs, graphicstate
        ):
            adv = super().render_char(
                matrix, font, fontsize, scaling, rise, cid, ncs, graphicstate
            )
            try:
                item = self.cur_item._objs[-1]
                item.endleaf_fs = fontsize
                item.endleaf_desc = font.get_descent() * fontsize
                item.endleaf_rise = rise
            except (AttributeError, IndexError):
                pass
            return adv

    return _Aggregator


def _pages(data):
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdfparser import PDFParser

    return PDFPage.create_pages(PDFDocument(PDFParser(io.BytesIO(data))))


def extract_pages(data):
    """Yield ``(index, width, height, glyphs, paths, offpage)`` per page, in paint order.

    laparams is None, so objects keep their paint order (z). Each glyph's quad is
    rebuilt from its text matrix, font size and descent (plus rise). Text is NFKC.
    """
    from pdfminer.layout import LTChar, LTCurve, LTFigure, LTImage
    from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
    from pdfminer.utils import apply_matrix_pt

    np = _np()
    manager = PDFResourceManager()
    device = _aggregator_class()(manager, laparams=None)
    interpreter = PDFPageInterpreter(manager, device)
    for index, page in enumerate(_pages(data), start=1):
        interpreter.process_page(page)
        layout = device.get_result()
        x0, y0, x1, y1 = layout.bbox
        width, height = x1 - x0, y1 - y0
        glyphs, paths = [], []
        counter = [0]
        offpage = [0]

        def box_of(item):
            return (
                item.x0 - x0,
                height - (item.y1 - y0),
                item.x1 - x0,
                height - (item.y0 - y0),
            )

        def add_glyph(char, z):
            text = _normalise(char.get_text())
            if not text.strip():
                return
            fontsize = getattr(char, "endleaf_fs", None)
            if not fontsize:
                return
            desc = getattr(char, "endleaf_desc", 0.0) + getattr(
                char, "endleaf_rise", 0.0
            )
            rise = getattr(char, "endleaf_rise", 0.0)
            adv = char.adv

            def point(px, py):
                qx, qy = apply_matrix_pt(char.matrix, (px, py))
                return (qx - x0, height - (qy - y0))

            p00, p10 = point(0, desc), point(adv, desc)
            p11, p01 = point(adv, desc + fontsize), point(0, desc + fontsize)
            b0, b1 = point(0, rise), point(adv, rise)
            span = math.hypot(b1[0] - b0[0], b1[1] - b0[1])
            size = math.hypot(p01[0] - p00[0], p01[1] - p00[1])
            if size <= 0 or span <= 0:
                return
            quad = np.array([p00, p10, p11, p01], dtype=float)
            if (
                quad[:, 0].max() < 0
                or quad[:, 0].min() > width
                or quad[:, 1].max() < 0
                or quad[:, 1].min() > height
            ):
                offpage[0] += 1  # OD-PDF-8: counted in the worker log, never reported
                return
            u = np.array([(b1[0] - b0[0]) / span, (b1[1] - b0[1]) / span])
            v = np.array([(p01[0] - p00[0]) / size, (p01[1] - p00[1]) / size])
            glyphs.append(
                _Glyph(
                    text, size, quad, u, v, np.array(b0), span, z, str(char.fontname)
                )
            )

        def visit(items):
            for item in items:
                counter[0] += 1
                if isinstance(item, LTChar):
                    add_glyph(item, counter[0])
                elif isinstance(item, LTCurve):
                    lines, closed, single = _flatten(
                        item.original_path, item.pts, height, y0, x0
                    )
                    if lines:
                        paths.append(
                            _Path(
                                counter[0],
                                box_of(item),
                                lines,
                                closed,
                                single,
                                bool(item.stroke),
                                bool(item.fill),
                                bool(item.fill) and _is_white(item.non_stroking_color),
                            )
                        )
                elif isinstance(item, LTImage):
                    paths.append(
                        _Path(
                            counter[0],
                            box_of(item),
                            [],
                            False,
                            False,
                            False,
                            True,
                            False,
                            True,
                        )
                    )
                elif isinstance(item, LTFigure):
                    visit(item)

        visit(layout)
        yield index, width, height, glyphs, paths, offpage[0]


# ---- ENDLEAF-R81-GROUP: words, lines, blocks ---------------------------------------


@dataclass
class _Word:
    text: str
    members: list
    u: object
    v: object
    size: float
    origin: object
    extent: float
    center: object
    box: tuple
    core: object
    z: int
    font: str
    baseline: float


@dataclass
class _Line:
    text: str
    words: list
    box: tuple
    size: float
    upright: bool
    fonts: set
    u: object
    v: object


def _link(
    center,
    u,
    v,
    size,
    extent,
    origin,
    k,
    gap_em,
    tolerance_em,
    min_cost=-1e9,
    size_tolerance=None,
):
    """Single-linkage groups: a Kruskal MST over k-nearest-neighbour edges, cut at the threshold.

    The cost of an edge is the gap along the frame's baseline in em of the smaller size. An
    MST cut at a threshold has the same groups as the connected components of the edges at or
    under it, so the components are taken directly. Returns ``(labels, edges)``.
    """
    np = _np()
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree

    n = len(center)
    if n < 2:
        return np.arange(n), None
    kk = min(k + 1, n)
    _, near = cKDTree(center).query(center, k=kk)
    near = np.atleast_2d(near)
    i = np.repeat(np.arange(n), kk - 1)
    j = near[:, 1:].ravel()
    d = center[j] - center[i]
    smin = np.minimum(size[i], size[j])
    along = (d * u[i]).sum(axis=1)
    gap = np.abs(along) - (extent[i] + extent[j]) / 2
    cost = gap / smin
    same_angle = (u[i] * u[j]).sum(axis=1) > _COS_SAME_ANGLE
    baseline = np.abs(((origin[j] - origin[i]) * v[i]).sum(axis=1))
    on_line = same_angle & (baseline <= tolerance_em * smin)
    if size_tolerance is not None:
        on_line &= np.abs(size[i] - size[j]) <= size_tolerance
    keep = on_line & (cost <= gap_em) & (cost >= min_cost)
    graph = coo_matrix((np.ones(int(keep.sum())), (i[keep], j[keep])), shape=(n, n))
    _, labels = connected_components(graph, directed=False)
    return labels, (i, j, cost, on_line & (along > 0))


def _glyph_core(glyph):
    np = _np()
    size = glyph.size
    sh = CORE_SHRINK_H_EM * size
    sv = CORE_SHRINK_V_EM * size
    lo, hi = sh, glyph.width - sh
    if hi <= lo:
        lo = hi = glyph.width / 2
    base = glyph.quad[0]
    return np.array(
        [
            base + glyph.u * lo + glyph.v * sv,
            base + glyph.u * hi + glyph.v * sv,
            base + glyph.u * hi + glyph.v * (size - sv),
            base + glyph.u * lo + glyph.v * (size - sv),
        ]
    )


def _group_words(glyphs, cores, labels):
    np = _np()
    import shapely

    words = []
    for label in range(int(labels.max()) + 1 if len(labels) else 0):
        idx = [n for n in range(len(glyphs)) if labels[n] == label]
        if not idx:
            continue
        first = glyphs[idx[0]]
        u, v = first.u, first.v
        idx.sort(key=lambda n: float(glyphs[n].origin @ u))
        members = [glyphs[n] for n in idx]
        quads = np.concatenate([g.quad for g in members])
        pts = quads @ u
        extent = float(pts.max() - pts.min())
        corner = np.concatenate([cores[n] for n in idx])
        cu, cv = corner @ u, corner @ v
        umin, umax, vmin, vmax = cu.min(), cu.max(), cv.min(), cv.max()
        # u and v are orthonormal for upright and rotated text; a skewed v is close enough.
        core = np.array(
            [
                u * umin + v * vmin,
                u * umax + v * vmin,
                u * umax + v * vmax,
                u * umin + v * vmax,
            ]
        )
        box = (
            float(quads[:, 0].min()),
            float(quads[:, 1].min()),
            float(quads[:, 0].max()),
            float(quads[:, 1].max()),
        )
        sizes = sorted(g.size for g in members)
        words.append(
            _Word(
                text="".join(g.text for g in members),
                members=idx,
                u=u,
                v=v,
                size=sizes[len(sizes) // 2],
                origin=members[0].origin,
                extent=extent,
                center=np.array([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2]),
                box=box,
                core=shapely.polygons(core),
                z=min(g.z for g in members),
                font=members[0].font,
                baseline=float(members[0].origin @ v),
            )
        )
    return words


def _group_lines(words):
    np = _np()
    if not words:
        return []
    center = np.array([w.center for w in words])
    u = np.array([w.u for w in words])
    v = np.array([w.v for w in words])
    size = np.array([w.size for w in words])
    extent = np.array([w.extent for w in words])
    origin = np.array([w.origin for w in words])
    labels, _ = _link(
        center, u, v, size, extent, origin, LINE_NEIGHBOURS, LINE_JOIN_EM, 0.5
    )
    lines = []
    for label in range(int(labels.max()) + 1):
        members = [words[n] for n in range(len(words)) if labels[n] == label]
        if not members:
            continue
        u0 = members[0].u
        members.sort(key=lambda w: float(w.origin @ u0))
        box = (
            min(w.box[0] for w in members),
            min(w.box[1] for w in members),
            max(w.box[2] for w in members),
            max(w.box[3] for w in members),
        )
        sizes = sorted(w.size for w in members)
        lines.append(
            _Line(
                text=" ".join(w.text for w in members),
                words=members,
                box=box,
                size=sizes[len(sizes) // 2],
                upright=abs(float(u0[0])) > _COS_SAME_ANGLE and abs(float(u0[1])) < 0.1,
                fonts={w.font for w in members},
                u=u0,
                v=members[0].v,
            )
        )
    return lines


def _count_blocks(lines):
    """Lines to blocks: the box gap across the lines is at most 0.25 em (9 of 9 in the prototype)."""
    np = _np()
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree

    n = len(lines)
    if n < 2:
        return n
    center = np.array(
        [[(ln.box[0] + ln.box[2]) / 2, (ln.box[1] + ln.box[3]) / 2] for ln in lines]
    )
    kk = min(9, n)
    _, near = cKDTree(center).query(center, k=kk)
    near = np.atleast_2d(near)
    rows, cols = [], []
    for a in range(n):
        for b in near[a, 1:]:
            la, lb = lines[a], lines[int(b)]
            if float(la.u @ lb.u) < _COS_SAME_ANGLE:
                continue
            ua = [float(pt @ la.u) for w in la.words for pt in w.core.exterior.coords]
            ub = [float(pt @ la.u) for w in lb.words for pt in w.core.exterior.coords]
            if min(max(ua), max(ub)) - max(min(ua), min(ub)) <= 0:
                continue
            va = [
                float(np.array(pt) @ la.v)
                for w in la.words
                for pt in w.core.exterior.coords
            ]
            vb = [
                float(np.array(pt) @ la.v)
                for w in lb.words
                for pt in w.core.exterior.coords
            ]
            if max(
                min(vb) - max(va), min(va) - max(vb)
            ) <= BLOCK_EXTRA_LEADING_EM * min(la.size, lb.size):
                rows.append(a)
                cols.append(int(b))
    graph = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    return int(connected_components(graph, directed=False)[0])


def _otsu(values, bins=50, high=0.5):
    np = _np()
    hist, edges = np.histogram(np.clip(values, 0, high), bins=bins, range=(0, high))
    total = hist.sum()
    if total == 0:
        return None
    centers = (edges[:-1] + edges[1:]) / 2
    best, threshold = -1.0, None
    for cut in range(1, bins):
        w0, w1 = hist[:cut].sum(), hist[cut:].sum()
        if w0 == 0 or w1 == 0:
            continue
        m0 = (hist[:cut] * centers[:cut]).sum() / w0
        m1 = (hist[cut:] * centers[cut:]).sum() / w1
        between = w0 * w1 * (m0 - m1) ** 2
        if between > best:
            best, threshold = between, float(edges[cut])
    return threshold


def _guard(edges, page_number, log_lines):
    """Docstrum guard (O'Gorman 1993): log only, never a job warning."""
    np = _np()
    if edges is None:
        return
    i, _, cost, ahead = edges
    ok = ahead & (cost > -0.5) & (cost < 1.0)
    if ok.sum() < 30:
        return
    nearest = np.full(int(i.max()) + 1, np.inf)
    np.minimum.at(nearest, i[ok], cost[ok])
    nearest = nearest[np.isfinite(nearest)]
    threshold = _otsu(nearest)
    if threshold is not None and not (GUARD_LOW_EM <= threshold <= GUARD_HIGH_EM):
        log_lines.append(
            f"pdfcheck guard page={page_number} otsuEm={threshold:.3f} usedEm={WORD_GAP_EM}"
        )


# ---- ENDLEAF-R81-REGION ---------------------------------------------------------------


def _figure_regions(paths, reference_width):
    """Single-linkage union of path boxes within 3 mm; page-wide rules are left out."""
    np = _np()
    import shapely
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    kept = [p for p in paths if (p.bbox[2] - p.bbox[0]) < 0.98 * reference_width]
    if not kept:
        return []
    half = FIGURE_REGION_GAP_PT / 2
    boxes = shapely.box(
        np.array([p.bbox[0] - half for p in kept]),
        np.array([p.bbox[1] - half for p in kept]),
        np.array([p.bbox[2] + half for p in kept]),
        np.array([p.bbox[3] + half for p in kept]),
    )
    tree = shapely.STRtree(boxes)
    left, right = tree.query(boxes, predicate="intersects")
    graph = coo_matrix(
        (np.ones(len(left)), (left, right)), shape=(len(kept), len(kept))
    )
    count, labels = connected_components(graph, directed=False)
    regions = []
    for label in range(count):
        members = [kept[n].bbox for n in range(len(kept)) if labels[n] == label]
        regions.append(
            (
                min(b[0] for b in members),
                min(b[1] for b in members),
                max(b[2] for b in members),
                max(b[3] for b in members),
            )
        )
    return regions


# ---- ENDLEAF-R81-CHECKS ---------------------------------------------------------------


def _start(text, limit=30):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _union(boxes):
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


@dataclass
class _Page:
    number: int
    width: float
    height: float
    glyphs: list
    paths: list
    words: list
    lines: list
    body: list
    cores: object
    word_of: list
    block: tuple | None
    kind: str
    run_of: list = field(default_factory=list)
    runs: list = field(default_factory=list)


def _check_margin_escape(page):
    hits = []
    for line in page.body:
        if not line.upright:
            continue
        x0, x1 = line.box[0], line.box[2]
        excess = max(-x0, x1 - page.width)
        if page.block is not None:
            left, _, width, _ = page.block
            excess = max(excess, left - x0, x1 - (left + width))
        if excess > MARGIN_ESCAPE_MIN_PT:
            mm = excess * _MM_PER_PT
            hits.append(
                Hit(
                    "pdf_margin_escape",
                    page.number,
                    line.box,
                    f"pg{page.number}: text runs {mm:.1f} mm past the text block: '{_start(line.text)}'",
                    over_mm=round(mm, 1),
                    pitch=line.size * 1.2,
                    severity=excess,
                )
            )
    return hits


def _lines_as_shapes(paths, stroked_only=True):
    import shapely

    shapes, owners = [], []
    for n, path in enumerate(paths):
        if stroked_only and not path.stroke:
            continue
        for poly in path.polylines:
            if len(poly) >= 2:
                shapes.append(shapely.linestrings(poly))
                owners.append(n)
    return shapes, owners


def _check_caption_overlap(page):
    import shapely

    np = _np()
    captions = [ln for ln in page.body if _CAPTION.match(ln.text)]
    if not captions or not page.paths:
        return []
    shapes, owners = _lines_as_shapes(page.paths)
    hits = []
    for caption in captions:
        cx0, cy0, cx1, cy1 = caption.box
        glyph_cores = shapely.polygons(
            np.array([page.cores[n] for w in caption.words for n in w.members])
        )
        for n, path in enumerate(page.paths):
            x0, y0, x1, y1 = path.bbox
            if (
                min(x1, cx1) - max(x0, cx0) <= OVERLAP_MIN_PT
                or min(y1, cy1) - max(y0, cy0) <= OVERLAP_MIN_PT
            ):
                continue
            if (
                x0 >= cx0 - OVERLAP_MIN_PT
                and x1 <= cx1 + OVERLAP_MIN_PT
                and y0 >= cy0 - OVERLAP_MIN_PT
                and y1 <= cy1 + OVERLAP_MIN_PT
            ):
                continue  # inside the line itself (a fraction bar or an underline of the caption)
            crosses = False
            if shapes and not path.image:
                mine = [shapes[m] for m in range(len(shapes)) if owners[m] == n]
                if mine:
                    crosses = bool(
                        shapely.intersects(
                            np.array(mine, dtype=object)[:, None], glyph_cores[None, :]
                        ).any()
                    )
            if path.fill or crosses:
                hits.append(
                    Hit(
                        "pdf_caption_overlap",
                        page.number,
                        caption.box,
                        f"pg{page.number}: a drawing overlaps the caption '{_start(caption.text)}'",
                        pitch=caption.size * 1.2,
                    )
                )
                break
    return hits


def _check_label_on_stroke(page):
    import shapely

    np = _np()
    if not page.words or not page.paths:
        return []
    shapes, owners = _lines_as_shapes(page.paths)
    if not shapes:
        return []
    cores = shapely.polygons(page.cores)
    tree = shapely.STRtree(cores)
    lines = np.array(shapes, dtype=object)
    stroke_idx, core_idx = tree.query(lines, predicate="intersects")
    whites = []
    for path in page.paths:
        if path.white and not path.image:
            ring = path.polylines[0]
            polygon = (
                shapely.polygons(ring) if len(ring) >= 3 else shapely.box(*path.bbox)
            )
            whites.append(
                (
                    path.z,
                    polygon if shapely.is_valid(polygon) else shapely.box(*path.bbox),
                )
            )
    glyph_word = {n: w for w, word in enumerate(page.words) for n in word.members}
    seen = set()
    hits = []
    for s, c in zip(stroke_idx.tolist(), core_idx.tolist()):
        word_index = glyph_word.get(c)
        path = page.paths[owners[s]]
        key = (word_index, owners[s])
        if word_index is None or key in seen:
            continue
        crossing = shapely.intersection(lines[s], cores[c])
        if crossing.is_empty:
            continue
        point = crossing.representative_point()
        glyph_z = page.glyphs[c].z
        covered = any(
            path.z < z < glyph_z and poly.contains(point) for z, poly in whites
        )
        if covered:
            continue
        seen.add(key)
        word = page.words[word_index]
        hits.append(
            Hit(
                "pdf_label_on_stroke",
                page.number,
                word.box,
                f"pg{page.number}: label '{_start(word.text)}' sits on a stroked line",
                pitch=word.size * 1.2,
            )
        )
    return hits


def _check_text_escapes_node(page):
    import shapely

    np = _np()
    nodes, widths = [], []
    for path in page.paths:
        if (
            path.image
            or not (path.stroke and path.closed and path.single)
            or len(path.polylines[0]) < 4
        ):
            continue
        polygon = shapely.polygons(path.polylines[0])
        if not shapely.is_valid(polygon):
            polygon = shapely.buffer(polygon, 0)
        if polygon.is_empty:
            continue
        nodes.append(polygon)
        widths.append(path.bbox[2] - path.bbox[0])
    if not nodes or not page.words:
        return []
    tree = shapely.STRtree(np.array(nodes, dtype=object))
    cores = [w.core for w in page.words]
    word_idx, node_idx = tree.query(
        np.array(cores, dtype=object), predicate="intersects"
    )
    hits = []
    seen = set()
    for w, n in zip(word_idx.tolist(), node_idx.tolist()):
        word = page.words[w]
        if widths[n] <= NODE_MIN_WIDTH_EM * word.size or w in seen:
            continue
        area = word.core.area
        if area <= 0:
            continue
        fraction = nodes[n].intersection(word.core).area / area
        if not (NODE_INSIDE_MIN < fraction < NODE_INSIDE_MAX):
            continue
        outside = word.core.difference(nodes[n])
        bx0, by0, bx1, by1 = outside.bounds
        if max(bx1 - bx0, by1 - by0) <= NODE_ESCAPE_MIN_PT:
            continue
        seen.add(w)
        hits.append(
            Hit(
                "pdf_text_escapes_node",
                page.number,
                word.box,
                f"pg{page.number}: label '{_start(word.text)}' runs out of its node",
                pitch=word.size * 1.2,
            )
        )
    return hits


_LOGO_LETTERS = frozenset("LATEX")


def _tex_logo(page, wa, wb, ga, gb):
    """The TeX and LaTeX logos set their letters on purpose in each other's boxes."""
    if ga.text not in _LOGO_LETTERS or gb.text not in _LOGO_LETTERS:
        return False
    for line in page.lines:
        members = {id(page.words[wa]), id(page.words[wb])}
        if members <= {id(w) for w in line.words}:
            flat = line.text.upper().replace(" ", "")
            return "TEX" in flat or "TAEX" in flat
    return False


def _check_text_overlap(page):
    import shapely

    if len(page.glyphs) < 2:
        return []
    cores = shapely.polygons(page.cores)
    tree = shapely.STRtree(cores)
    left, right = tree.query(cores, predicate="intersects")
    glyph_word = {n: w for w, word in enumerate(page.words) for n in word.members}
    found = {}
    for a, b in zip(left.tolist(), right.tolist()):
        if a >= b:
            continue
        ga, gb = page.glyphs[a], page.glyphs[b]
        inter = shapely.intersection(cores[a], cores[b])
        if inter.is_empty:
            continue
        bx0, by0, bx1, by1 = inter.bounds
        if bx1 - bx0 <= OVERLAP_MIN_PT or by1 - by0 <= OVERLAP_MIN_PT:
            continue
        same_baseline = (
            abs(float(ga.origin @ ga.v) - float(gb.origin @ ga.v)) <= SAME_BASELINE_PT
        )
        if same_baseline and ga.text in _EXTENSIBLE and gb.text in _EXTENSIBLE:
            continue
        wa, wb = glyph_word[a], glyph_word[b]
        if wa == wb:
            # Inside one word kerning overlaps a little; only an overprint overlaps by more than
            # OVERPRINT_EM, measured along the baseline.
            ring = (
                inter.exterior.coords
                if inter.geom_type == "Polygon"
                else [(bx0, by0), (bx1, by1)]
            )
            along = [float(x * ga.u[0] + y * ga.u[1]) for x, y in ring]
            if max(along) - min(along) <= OVERPRINT_EM * min(ga.size, gb.size):
                continue
        elif _tex_logo(page, wa, wb, ga, gb):
            continue
        key = tuple(
            sorted((page.run_of[a], page.run_of[b]), key=lambda r: page.runs[r][1])
        )
        box = found.get(key)
        found[key] = (
            (bx0, by0, bx1, by1) if box is None else _union([box, (bx0, by0, bx1, by1)])
        )
    hits = []
    for (first, second), box in found.items():
        size = max(
            page.glyphs[n].size
            for n, r in enumerate(page.run_of)
            if r in (first, second)
        )
        hits.append(
            Hit(
                "pdf_text_overlap",
                page.number,
                box,
                f"pg{page.number}: '{_start(page.runs[first][0], 24)}' overlaps '{_start(page.runs[second][0], 24)}'",
                pitch=size * 1.2,
            )
        )
    return hits


def _figure_words(page, regions):
    out = []
    for word in page.words:
        cx, cy = word.center
        if any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in regions):
            out.append(word)
    return out


def _check_label_gutter(page, regions):
    if page.kind not in GUTTER_KINDS:
        return []
    words = [
        w for w in _figure_words(page, regions) if abs(float(w.u[0])) > _COS_SAME_ANGLE
    ]
    hits = []
    for a in range(len(words)):
        for b in range(a + 1, len(words)):
            wa, wb = words[a], words[b]
            overlap_v = min(wa.box[3], wb.box[3]) - max(wa.box[1], wb.box[1])
            if overlap_v < 0.5 * min(wa.box[3] - wa.box[1], wb.box[3] - wb.box[1]):
                continue
            different = (
                abs(wa.baseline - wb.baseline) > GUTTER_BASELINE_SHIFT_PT
                or abs(wa.size - wb.size) > GUTTER_SIZE_SHIFT_PT
            )
            if not different:
                continue
            gap = max(wa.box[0], wb.box[0]) - min(wa.box[2], wb.box[2])
            if gap >= LABEL_GUTTER_PT:
                continue
            first, second = sorted((wa, wb), key=lambda w: w.z)
            hits.append(
                Hit(
                    "pdf_label_gutter",
                    page.number,
                    _union([wa.box, wb.box]),
                    f"pg{page.number}: labels '{_start(first.text, 24)}' and '{_start(second.text, 24)}' "
                    f"are {max(gap, 0.0) * _MM_PER_PT:.1f} mm apart",
                    over_mm=round(max(gap, 0.0) * _MM_PER_PT, 1),
                    pitch=max(wa.size, wb.size) * 1.2,
                )
            )
    return hits


def _check_stray_source(page):
    if page.kind not in STRAY_SOURCE_KINDS:
        return []
    hits = []
    for line in page.body:
        if any(_MONO_FONT.search(font) for font in line.fonts):
            continue  # a listing or verbatim run; the TeX marker is PROPOSED, so the font stands in
        match = _STRAY.search(line.text)
        if match:
            hits.append(
                Hit(
                    "pdf_stray_source",
                    page.number,
                    line.box,
                    f"pg{page.number}: raw source printed as text: '{_start(match.group(0))}'",
                    pitch=line.size * 1.2,
                )
            )
    return hits


def _check_empty_page(page, last):
    words = sum(len(line.words) for line in page.body)
    limit = 0 if last else NEAR_EMPTY_MAX_WORDS
    if words <= limit and not page.paths:
        return [
            Hit(
                "pdf_empty_page",
                page.number,
                (0.0, 0.0, page.width, page.height),
                f"pg{page.number}: page has {words} words and no drawing",
                pitch=page.height,
            )
        ]
    return []


# ---- dedupe, placement, emit ----------------------------------------------------------


def dedupe(hits, tex_pages=()):
    """One finding per connected fault region (same code and page, boxes within one line pitch).

    OD-PDF-4: a pdf_margin_escape on a page TeX already names (overfull row or layout_overhang)
    is dropped.
    """
    groups = {}
    for hit in hits:
        if hit.code == "pdf_margin_escape" and hit.page in tex_pages:
            continue
        groups.setdefault((hit.code, hit.page), []).append(hit)
    merged = []
    for group in groups.values():
        parent = list(range(len(group)))

        def find(n):
            while parent[n] != n:
                parent[n] = parent[parent[n]]
                n = parent[n]
            return n

        for a in range(len(group)):
            for b in range(a + 1, len(group)):
                gap = (group[a].pitch + group[b].pitch) / 2
                ba, bb = group[a].box, group[b].box
                if (
                    min(ba[2], bb[2]) - max(ba[0], bb[0]) >= -gap
                    and min(ba[3], bb[3]) - max(ba[1], bb[1]) >= -gap
                ):
                    parent[find(a)] = find(b)
        clusters = {}
        for n, hit in enumerate(group):
            clusters.setdefault(find(n), []).append(hit)
        for members in clusters.values():
            best = max(members, key=lambda h: (h.severity, -h.box[1], -h.box[0]))
            merged.append(
                Hit(
                    best.code,
                    best.page,
                    _union([h.box for h in members]),
                    best.message,
                    best.over_mm,
                    best.pitch,
                    sum(h.count for h in members),
                    best.severity,
                )
            )
    order = {code: n for n, code in enumerate(CODES)}
    merged.sort(key=lambda h: (h.page, round(h.box[1], 1), order[h.code], h.box[0]))
    return merged


def part_for(marks, page_number, y_from_bottom):
    """The part whose start and end marks span a position, from the layout marks.

    ``marks`` rows are ``[id, tag, page, y-pt-from-bottom, orientation]``; a position is
    after a mark when it is on a later page or lower on the same page. The latest start wins.
    """
    here = (page_number, -y_from_bottom)
    open_at = {}
    best = None
    for part, tag, page, y, _ in marks:
        key = (page, -y)
        if tag == "s":
            open_at[part] = key
            if key <= here:
                best = (key, part)
        elif tag == "e" and part in open_at:
            start = open_at.pop(part)
            if start <= here <= key and (best is None or start >= best[0]):
                best = (start, part)
            elif best is not None and best[1] == part and key < here:
                best = None
    still_open = [(k, p) for p, k in open_at.items() if k <= here]
    candidates = [c for c in [best, *still_open] if c is not None]
    return max(candidates)[1] if candidates else None


def item_for(hit, page_height, marks=None, shell_pages=None):
    item = {
        "code": hit.code,
        "packages": list(PACKAGES),
        "message": hit.message,
        "page": hit.page,
        "box": [round(float(x), 1) for x in hit.box],
        "regionCount": hit.count,
    }
    if hit.over_mm is not None:
        item["overMm"] = hit.over_mm
    if marks:
        part = part_for(marks, hit.page, page_height - hit.box[1])
        if part:
            item["partId"] = part
    for number, page in (shell_pages or {}).items():
        if page == hit.page:
            item["fenceNumber"] = number
            break
    return item


def pdf_layout_line(items):
    """One stderr line, or ``None`` when there is nothing to report."""
    if not items:
        return None
    return PDF_PREFIX + json.dumps(items, separators=(",", ":"))


_ITEM_KEYS = {
    "page": int,
    "overMm": (int, float),
    "regionCount": int,
    "partId": str,
    "fenceNumber": int,
    "count": int,
}


def parse_pdf_layout(stderr):
    """Read the ``ENDLEAF_PDFLAYOUT`` line back; ``[]`` when absent or malformed."""
    if not stderr:
        return []
    text = stderr.decode("utf-8", "replace") if isinstance(stderr, bytes) else stderr
    for line in text.splitlines():
        if not line.startswith(PDF_PREFIX):
            continue
        try:
            parsed = json.loads(line[len(PDF_PREFIX) :])
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        clean = []
        for item in parsed:
            if (
                isinstance(item, dict)
                and item.get("code") in (*CODES, SKIP_CODE, MORE_CODE)
                and item.get("packages") == PACKAGES
                and isinstance(item.get("message"), str)
                and item["message"]
            ):
                kept = {
                    "code": item["code"],
                    "packages": list(PACKAGES),
                    "message": item["message"],
                }
                for key, kind in _ITEM_KEYS.items():
                    if (
                        key in item
                        and isinstance(item[key], kind)
                        and not isinstance(item[key], bool)
                    ):
                        kept[key] = item[key]
                box = item.get("box")
                if (
                    isinstance(box, list)
                    and len(box) == 4
                    and all(
                        isinstance(x, (int, float)) and not isinstance(x, bool)
                        for x in box
                    )
                ):
                    kept["box"] = list(box)
                clean.append(kept)
        return clean
    return []


# ---- the run --------------------------------------------------------------------------


def _build_page(index, width, height, glyphs, paths, block, kind, offpage, log_lines):
    np = _np()
    cores = (
        np.array([_glyph_core(g) for g in glyphs]) if glyphs else np.zeros((0, 4, 2))
    )
    words, lines, edges = [], [], None
    if glyphs:
        center = np.array([g.quad.mean(axis=0) for g in glyphs])
        labels, edges = _link(
            center,
            np.array([g.u for g in glyphs]),
            np.array([g.v for g in glyphs]),
            np.array([g.size for g in glyphs]),
            np.array([g.width for g in glyphs]),
            np.array([g.origin for g in glyphs]),
            WORD_NEIGHBOURS,
            WORD_GAP_EM,
            0.1,
            min_cost=-WORD_OVERLAP_EM,
            size_tolerance=SAME_SIZE_PT,
        )
        words = _group_words(glyphs, cores, labels)
        lines = _group_lines(words)
    guard_lines = []
    _guard(edges, index, guard_lines)
    log_lines.extend(guard_lines)
    if offpage:
        log_lines.append(f"pdfcheck offpage page={index} glyphs={offpage}")
    # The folio (a lone 1 to 4 digit number below the text block) is not body.
    floor = (block[1] + block[3]) if block else 0.88 * height
    body = [
        ln for ln in lines if not (_FOLIO.match(ln.text) and ln.box[1] >= floor - 1.0)
    ]
    word_of = [0] * len(glyphs)
    for n, word in enumerate(words):
        for m in word.members:
            word_of[m] = n
    page = _Page(
        index,
        width,
        height,
        glyphs,
        paths,
        words,
        lines,
        body,
        cores,
        word_of,
        block,
        kind,
    )
    page.run_of, page.runs = _glyph_runs(glyphs)
    return page


def _glyph_runs(glyphs):
    """Glyph runs in paint order: glyphs painted one after another on one baseline and size."""
    run_of = [0] * len(glyphs)
    runs = []
    previous = None
    for n in sorted(range(len(glyphs)), key=lambda n: glyphs[n].z):
        g = glyphs[n]
        same = (
            previous is not None
            and g.z == glyphs[previous].z + 1
            and abs(g.size - glyphs[previous].size) <= SAME_SIZE_PT
            and abs(float((g.origin - glyphs[previous].origin) @ g.v))
            <= SAME_BASELINE_PT
            and -0.01
            <= float((g.origin - glyphs[previous].origin) @ g.u)
            <= glyphs[previous].width + 0.5 * g.size
        )
        if not same:
            runs.append([])
        runs[-1].append(n)
        run_of[n] = len(runs) - 1
        previous = n
    return run_of, [
        ("".join(glyphs[n].text for n in run), glyphs[run[0]].z) for run in runs
    ]


def _preload():
    import numpy  # noqa: F401
    import pdfminer.converter  # noqa: F401
    import pdfminer.pdfpage  # noqa: F401
    import scipy.sparse.csgraph  # noqa: F401
    import scipy.spatial  # noqa: F401
    import shapely  # noqa: F401


def _run_page(raw, last, blocks, kind, budget, log_lines):
    index, width, height, glyphs, paths, offpage = raw
    block = None
    if blocks and index in blocks:
        left, top, block_width, block_height = (
            float(x) * TEX_PT_TO_BP for x in blocks[index]
        )
        block = (left, top, block_width, block_height)
    page = _build_page(
        index, width, height, glyphs, paths, block, kind, offpage, log_lines
    )
    budget.check()
    regions = _figure_regions(paths, block[2] if block else 0.75 * width)
    budget.check()
    hits = []
    for run in (
        lambda: _check_margin_escape(page),
        lambda: _check_caption_overlap(page),
        lambda: _check_label_on_stroke(page),
        lambda: _check_text_escapes_node(page),
        lambda: _check_text_overlap(page),
        lambda: _check_label_gutter(page, regions),
        lambda: _check_stray_source(page),
        lambda: _check_empty_page(page, last),
    ):
        hits.extend(run())
        budget.check()
    return hits


def _page_count(data):
    return sum(1 for _ in _pages(data))


def check_pdf(
    data,
    *,
    template_id="",
    blocks=None,
    marks=None,
    shell_pages=None,
    tex_pages=(),
    page_budget=PAGE_BUDGET_SEC,
    document_budget=DOCUMENT_BUDGET_SEC,
    clock=time.perf_counter,
):
    """Run every check over a PDF and return a ``CheckResult``; it never raises.

    ``blocks`` is ``{page: (left, top, width, height)}`` in TeX pt (ENDLEAF_PAGEBLOCK); a
    page without one skips the margin check and is counted in the log. ``tex_pages`` are the
    pages TeX already names (OD-PDF-4). A time overrun or any exception ends the checks,
    keeps the findings so far and adds one ``pdf_check_skipped`` note.
    """
    result = CheckResult()
    budget = _Budget(clock, page_budget, document_budget)
    hits, heights = [], {}
    skipped, last, no_block = None, 0, 0
    try:
        _preload()  # library import time is not per-page work
        budget.begin()
        total = _page_count(data)
        stream = extract_pages(data)
        while True:
            budget.begin_page()
            try:
                raw = next(stream)
            except StopIteration:
                break
            budget.check()
            heights[raw[0]] = raw[2]
            if not blocks or raw[0] not in blocks:
                no_block += 1
            hits.extend(
                _run_page(
                    raw, raw[0] == total, blocks, template_id, budget, result.log_lines
                )
            )
            last = raw[0]
    except CheckSkipped as exc:
        skipped = str(exc)
    except Exception as exc:  # warn-only: nothing here may fail the render
        logger.warning("pdf layout check failed: %s", exc.__class__.__name__)
        skipped = f"error {exc.__class__.__name__}"
    if no_block:
        result.log_lines.append(f"pdfcheck noblock pages={no_block}")
    merged = dedupe(hits, set(tex_pages))
    for hit in merged[:MAX_FINDINGS]:
        result.items.append(
            item_for(hit, heights.get(hit.page, 0.0), marks, shell_pages)
        )
    if len(merged) > MAX_FINDINGS:
        more = len(merged) - MAX_FINDINGS
        result.items.append(
            {
                "code": MORE_CODE,
                "packages": list(PACKAGES),
                "message": f"{more} more PDF layout findings not listed",
                "count": more,
            }
        )
    if skipped:
        note = {
            "code": SKIP_CODE,
            "packages": list(PACKAGES),
            "message": (
                f"pdf layout check stopped ({skipped}) after pg{last}; findings so far are kept"
                if last
                else f"pdf layout check stopped ({skipped}) before pg1"
            ),
        }
        if last:
            note["page"] = last
        result.items.append(note)
    return result
