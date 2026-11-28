# Copyright (C) 2026 Inkmirage (Endleaf render worker modifications)
# SPDX-License-Identifier: AGPL-3.0-or-later
"""ENDLEAF-R59-OVERHANG. A picture wider than its text line is a job warning.

endleaf-fit.tex logs ``ENDLEAF_WIDE_PICTURE width=..pt line=..pt`` for a
plain TikZ picture and ``ENDLEAF_OVERHANG package=sysml-tikz width=..pt
line=..pt`` for a fitted canvas. The sandbox turns those lines into one
``ENDLEAF_LAYOUT`` stderr line; the runner reads it back; the job record
carries it in ``warnings`` beside ``notationPdfOnly``. It is a warning: the
PDF is still returned.

ENDLEAF-R61-FIT. In fulldoc, endleaf-layout.tex also logs every picture as
``ENDLEAF_PICFIT id plain|sysml width line minsize``: its part id (the last
layout mark), the line it must fit and the smallest text size set inside
it. Then each picture past its line is its own warning and carries
``partId``, ``overMm``, ``scaleToFit`` (line / width, rounded down to two
decimals so the scaled picture fits), ``minTextPt`` (the smallest text at
that scale) and ``belowTypeFloor`` (``minTextPt`` under 7 pt, ENDLEAF-R26),
with a ``fix``: scale inside the source when the text stays at or above
7 pt, otherwise redraw or split. At most ``MAX_PICTURE_WARNINGS`` pictures
are listed; one more item counts the rest.

ENDLEAF-R80-TALL. endleaf-fit.tex also logs ``ENDLEAF_SHELLTALL n height avail``
(TeX pt) for a document-shell fence, with its caption reserve, that is still
taller than its bound at the floor scale. Each one is a ``layout_too_tall``
item (packages ``diagram``, ``overMm``, ``page``, ``landscape``), listed
beside ``layout_overhang`` and counted under ``MAX_PICTURE_WARNINGS``.
"""

import json
import math
import re

LAYOUT_PREFIX = "ENDLEAF_LAYOUT "
LAYOUT_CODE = "layout_overhang"
_PT_TO_MM = 25.4 / 72.27
# TeX wraps log lines at 79 characters, so the log is read with line
# breaks removed. The pattern is anchored on its own keywords.
_LINE = re.compile(
    r"ENDLEAF_(WIDE_PICTURE|OVERHANG)(?: package=([A-Za-z-]+))?"
    r" width=([0-9]+(?:\.[0-9]+)?)pt line=([0-9]+(?:\.[0-9]+)?)pt"
)
_FIT = re.compile(
    r"ENDLEAF_PICFIT (\S{1,80}) (plain|sysml) ([0-9]+(?:\.[0-9]+)?)pt"
    r" ([0-9]+(?:\.[0-9]+)?)pt ([0-9]+(?:\.[0-9]+)?)"
)
# ENDLEAF-R69-WHERE. endleaf-layout.tex numbers each PICFIT line (1, 2, ...)
# and logs, for a plain picture, the page it ships on and whether it turned
# its page landscape:
#   ENDLEAF_PICPAGE n page portrait|landscape   (at shipout)
#   ENDLEAF_PICTURN n inputline                 (at compile time)
_PICPAGE = re.compile(r"ENDLEAF_PICPAGE ([0-9]{1,5}) ([0-9]{1,5}) (portrait|landscape)")
_PICTURN = re.compile(r"ENDLEAF_PICTURN ([0-9]{1,5}) ([0-9]{1,7})")
# ENDLEAF-R70-SHELL. endleaf-fit.tex logs each document-shell diagram fence:
#   ENDLEAF_SHELLFIT n natural-width line type-pt scale   (compile time)
#   ENDLEAF_SHELLTURN n                                   (it turned landscape)
#   ENDLEAF_SHELLPAGE n page portrait|landscape           (at shipout)
_SHELLFIT = re.compile(
    r"ENDLEAF_SHELLFIT ([0-9]{1,5}) ([0-9]+(?:\.[0-9]+)?)pt ([0-9]+(?:\.[0-9]+)?)pt"
    r" ([0-9]+(?:\.[0-9]+)?) ([0-9]+(?:\.[0-9]+)?)"
)
_SHELLTURN = re.compile(r"ENDLEAF_SHELLTURN ([0-9]{1,5})")
_SHELLPAGE = re.compile(r"ENDLEAF_SHELLPAGE ([0-9]{1,5}) ([0-9]{1,5}) (portrait|landscape)")
# ENDLEAF-R80-TALL. endleaf-fit.tex logs a fence (with its caption reserve) that
# is still taller than its bound at the floor scale:
#   ENDLEAF_SHELLTALL n height-pt avail-pt
_SHELLTALL = re.compile(
    r"ENDLEAF_SHELLTALL ([0-9]{1,5}) ([0-9]+(?:\.[0-9]+)?)pt ([0-9]+(?:\.[0-9]+)?)pt"
)
SCALED_CODE = "picture_scaled"
TOO_TALL_CODE = "layout_too_tall"
TYPE_FLOOR_PT = 7.0
# endleaf-layout.tex logs 99 when a picture sets no text.
NO_TEXT_PT = 99.0
MAX_PICTURE_WARNINGS = 10
# Below this the picture only touches the margin; TeX's own overfull
# warning is the signal for that, not this one.
MIN_OVERHANG_PT = 1.0


def picture_fit(width_pt, line_pt, min_size_pt):
    """(scaleToFit, minTextPt, belowTypeFloor) for a picture wider than its line."""
    scale = math.floor(line_pt / width_pt * 100) / 100
    if min_size_pt >= NO_TEXT_PT:
        return scale, None, False
    min_text = math.floor(min_size_pt * scale * 10) / 10
    return scale, min_text, min_text < TYPE_FLOOR_PT


def picture_pages(text):
    """{n: (page, orientation)} from ENDLEAF_PICPAGE; the first shipout of n wins."""
    pages = {}
    for match in _PICPAGE.finditer(text):
        pages.setdefault(int(match.group(1)), (int(match.group(2)), match.group(3)))
    return pages


def turned_pictures(text):
    """{n: inputline} for each picture that turned its page or float landscape."""
    return {int(m.group(1)): int(m.group(2)) for m in _PICTURN.finditer(text)}


def _picture_warnings(text):
    out = []
    extra = 0
    pages = picture_pages(text)
    turned = turned_pictures(text)
    for number, match in enumerate(_FIT.finditer(text), start=1):
        where, kind = match.group(1), match.group(2)
        width, line, size = (float(match.group(n)) for n in (3, 4, 5))
        over = width - line
        if over < MIN_OVERHANG_PT or width <= 0:
            continue
        if len(out) >= MAX_PICTURE_WARNINGS:
            extra += 1
            continue
        scale, min_text, below = picture_fit(width, line, size)
        millimetres = round(over * _PT_TO_MM, 1)
        if below:
            fix = f"redraw or split; scaling would put text at {min_text:g} pt"
        else:
            fix = f"scale inside the source to {scale:.2f}"
        part = None if where == "-" else where
        page = pages.get(number, (None, None))[0]
        landscape = number in turned
        if landscape:
            # The page already turned: the picture is past the landscape line.
            fix = fix.replace("scale inside the source", "already landscape; scale inside the source", 1)
            if below:
                fix = "already landscape; " + fix
        where_text = " ".join(
            x for x in (part, f"pg{page}" if page is not None else None, "landscape" if landscape else None) if x
        )
        item = {
            "code": LAYOUT_CODE,
            "packages": ["sysml-tikz" if kind == "sysml" else "tikz"],
            "message": (
                (f"{where_text}: " if where_text else "")
                + f"a picture runs {millimetres:.1f} mm past the text line; "
                + f"scaleToFit {scale:.2f}, "
                + (f"minTextPt {min_text:g}" if min_text is not None else "no text")
                + (" (below 7 pt)" if below else "")
                + f". Fix: {fix}"
            ),
            "overMm": millimetres,
            "scaleToFit": scale,
            **({"minTextPt": min_text} if min_text is not None else {}),
            "belowTypeFloor": below,
            "fix": fix,
        }
        if part:
            item["partId"] = part
        if page is not None:
            item["page"] = page
        if landscape:
            item["landscape"] = True
        out.append(item)
    if extra:
        out.append(
            {
                "code": LAYOUT_CODE,
                "packages": ["tikz"],
                "message": f"{extra} more pictures run past the text line",
            }
        )
    return out


def shell_pages(log):
    """``{fence n: page}`` from ENDLEAF_SHELLPAGE (the first shipout of a fence wins)."""
    text = (log or "").replace("\n", "")
    pages = {}
    for match in _SHELLPAGE.finditer(text):
        pages.setdefault(int(match.group(1)), int(match.group(2)))
    return pages


def _shell_warnings(text):
    """ENDLEAF-R70-SHELL. One item per fence that overhangs or was shrunk."""
    pages = {}
    for match in _SHELLPAGE.finditer(text):
        pages.setdefault(int(match.group(1)), (int(match.group(2)), match.group(3)))
    turned = {int(m.group(1)) for m in _SHELLTURN.finditer(text)}
    out = []
    seen = set()
    extra = 0
    for match in _SHELLFIT.finditer(text):
        number = int(match.group(1))
        if number in seen:
            continue
        seen.add(number)
        natural, line, type_pt, applied = (float(match.group(n)) for n in (2, 3, 4, 5))
        if natural <= 0:
            continue
        shown = natural * applied
        page, orientation = pages.get(number, (None, None))
        landscape = number in turned or orientation == "landscape"
        where = " ".join(
            x for x in (f"pg{page}" if page is not None else None, "landscape" if landscape else None) if x
        )
        prefix = f"{where}: " if where else ""
        if shown - line >= MIN_OVERHANG_PT:
            if len(out) >= MAX_PICTURE_WARNINGS:
                extra += 1
                continue
            # Against the fence as drawn: the scale its source needs.
            scale = math.floor(line / natural * 100) / 100
            min_text = math.floor(type_pt * scale * 10) / 10
            below = min_text < TYPE_FLOOR_PT
            millimetres = round((shown - line) * _PT_TO_MM, 1)
            fix = (
                f"redraw or split; scaling would put text at {min_text:g} pt"
                if below
                else f"scale inside the source to {scale:.2f}"
            )
            if landscape:
                fix = "already landscape; " + fix
            item = {
                "code": LAYOUT_CODE,
                "packages": ["diagram"],
                "message": (
                    f"{prefix}a diagram runs {millimetres:.1f} mm past the text line"
                    f" at {applied:.2f} scale; scaleToFit {scale:.2f}, minTextPt {min_text:g}"
                    + (" (below 7 pt)" if below else "")
                    + f". Fix: {fix}"
                ),
                "overMm": millimetres,
                "scaleToFit": scale,
                "minTextPt": min_text,
                "belowTypeFloor": below,
                "fix": fix,
            }
        elif applied < 1:
            text_pt = math.floor(type_pt * applied * 10) / 10
            applied = math.floor(applied * 100) / 100
            item = {
                "code": SCALED_CODE,
                "packages": ["diagram"],
                "message": f"{prefix}a diagram was shrunk to {applied:.2f}; its text is {text_pt:g} pt",
                "scale": applied,
                "minTextPt": text_pt,
            }
        else:
            continue
        if page is not None:
            item["page"] = page
        if landscape:
            item["landscape"] = True
        out.append(item)
    # ENDLEAF-R80-TALL: its own dedupe set, so a fence that also overhangs
    # yields both items. It is read whatever natural width says.
    tall_seen = set()
    for match in _SHELLTALL.finditer(text):
        number = int(match.group(1))
        if number in tall_seen:
            continue
        tall_seen.add(number)
        height, avail = float(match.group(2)), float(match.group(3))
        over = height - avail
        if over < MIN_OVERHANG_PT:
            continue
        if len(out) >= MAX_PICTURE_WARNINGS:
            extra += 1
            continue
        page, orientation = pages.get(number, (None, None))
        landscape = number in turned or orientation == "landscape"
        where = " ".join(
            x for x in (f"pg{page}" if page is not None else None, "landscape" if landscape else None) if x
        )
        prefix = f"{where}: " if where else ""
        millimetres = round(over * _PT_TO_MM, 1)
        item = {
            "code": TOO_TALL_CODE,
            "packages": ["diagram"],
            "message": (
                f"{prefix}a diagram and its caption run {millimetres:.1f} mm past the text height;"
                " redraw or split. Fix: shorten the diagram or split it across pages"
            ),
            "overMm": millimetres,
        }
        if page is not None:
            item["page"] = page
        if landscape:
            item["landscape"] = True
        out.append(item)
    if extra:
        out.append(
            {
                "code": LAYOUT_CODE,
                "packages": ["diagram"],
                "message": f"{extra} more diagrams run past the text line",
            }
        )
    return out


def final_pass(output):
    """Pandoc ``--verbose`` output: only the last LaTeX run's text."""
    text = output.decode("utf-8", "replace") if isinstance(output, bytes) else (output or "")
    marker = "[makePDF] LaTeX run number"
    at = text.rfind(marker)
    return text if at < 0 else text[at:]


def layout_warnings(log):
    """Structured warnings from a final-pass log; ``[]`` when nothing overhangs."""
    text = (log or "").replace("\n", "")
    if "ENDLEAF_SHELLFIT" in text or "ENDLEAF_SHELLTALL" in text:
        return _shell_warnings(text) + [
            item for item in _plain_warnings(text) if item["packages"] != ["diagram"]
        ]
    return _plain_warnings(text)


def _plain_warnings(text):
    if "ENDLEAF_PICFIT" in text:
        return _picture_warnings(text)
    worst = {}
    counts = {}
    for match in _LINE.finditer(text):
        package = match.group(2) or "tikz"
        over = float(match.group(3)) - float(match.group(4))
        if over < MIN_OVERHANG_PT:
            continue
        counts[package] = counts.get(package, 0) + 1
        worst[package] = max(worst.get(package, 0.0), over)
    out = []
    for package in sorted(worst):
        millimetres = worst[package] * _PT_TO_MM
        count = counts[package]
        noun = "picture runs" if count == 1 else f"{count} pictures run up to"
        out.append(
            {
                "code": LAYOUT_CODE,
                "packages": [package],
                "message": (
                    f"a {noun} {millimetres:.1f} mm past the text line; "
                    "narrow or split the picture"
                ),
            }
        )
    return out


def layout_line(warnings):
    """One stderr line, or ``None`` when there is nothing to report."""
    if not warnings:
        return None
    return LAYOUT_PREFIX + json.dumps(warnings, separators=(",", ":"))


_FIT_KEYS = {
    "partId": str,
    "overMm": (int, float),
    "scaleToFit": (int, float),
    "minTextPt": (int, float),
    "belowTypeFloor": bool,
    "fix": str,
    "page": int,
    "landscape": bool,
    "scale": (int, float),
}


def parse_layout(stderr):
    """Read the ``ENDLEAF_LAYOUT`` line back; ``[]`` when absent or malformed."""
    if not stderr:
        return []
    text = stderr.decode("utf-8", "replace") if isinstance(stderr, bytes) else stderr
    for line in text.splitlines():
        if not line.startswith(LAYOUT_PREFIX):
            continue
        try:
            parsed = json.loads(line[len(LAYOUT_PREFIX) :])
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        clean = []
        for item in parsed:
            if (
                isinstance(item, dict)
                and item.get("code") in (LAYOUT_CODE, SCALED_CODE, TOO_TALL_CODE)
                and isinstance(item.get("packages"), list)
                and item["packages"]
                and all(isinstance(name, str) and name for name in item["packages"])
                and isinstance(item.get("message"), str)
                and item["message"]
            ):
                kept = {
                    "code": item["code"],
                    "packages": list(item["packages"]),
                    "message": item["message"],
                }
                for key in _FIT_KEYS:
                    if key in item and isinstance(item[key], _FIT_KEYS[key]):
                        kept[key] = item[key]
                clean.append(kept)
        return clean
    return []
