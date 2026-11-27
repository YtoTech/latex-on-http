"""ENDLEAF-R80: landscape fence margins and caption-aware height fit.

Unit cases (no TeX): c1 page.tex margin names, c2 fit.tex landscape derivation,
c3 the caption reserve in \\elfit@bounded, c4 the layout_too_tall warning.
TeX cases: (a) runs the worker's own Markdown PDF command (Pandoc, the diagram
filters, the lane template) and skips without Pandoc 3, xelatex or poppler;
(b) compiles the document-shell TeX wrapper and skips without xelatex/pdfinfo.
TeX wraps log lines at max_print_line (79 on Debian), so logs are read unwrapped.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from colophon import layout_warn
from colophon.enums import JobSpec
from colophon.limits import SHARE_ROOT
from colophon.render_plan import build_render_plan
from colophon.templates import compose_with_body_line
from tests.colophon.test_fulldoc import _unwrap

_ROOT = Path(__file__).resolve().parents[2]
_SHARE = _ROOT / "colophon/share"
_OWNED = _SHARE / "templates/owned"
_TEX = _SHARE / "tex/latex/colophon-v1"
_PAGE = _TEX / "endleaf-page.tex"
_FIT = _TEX / "endleaf-fit.tex"
_DIAGRAM = _ROOT / "vendor/diagram/diagram.lua"
_VALUES = {"L": "20mm", "R": "20mm", "T": "20mm", "B": "22mm"}


def _code(path):
    return "\n".join(line.split("%", 1)[0] for line in path.read_text(encoding="utf-8").splitlines())


def _braced(text, start):
    """Text from ``start`` to the end of the first balanced brace group after it."""
    depth = 0
    for i in range(text.index("{", start), len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise AssertionError("unbalanced braces")


def _flat(text):
    text = re.sub(r"\\setlength\{(\\[A-Za-z@]+)\}\{([^{}]*)\}", r"\1=\2", text)
    return re.sub(r"\s+", " ", text)


def _cond(text, start):
    """(then, else) parts of the balanced conditional whose \\if token starts at ``start``."""
    depth = 0
    else_at = None
    first_end = None
    for m in re.finditer(r"\\(if[A-Za-z@]*|else|fi)(?![A-Za-z@])", text[start:]):
        tok, pos = m.group(1), start + m.start()
        if tok == "fi":
            depth -= 1
            if depth == 0:
                end = pos
                head = re.match(r"\\if[A-Za-z@]*", text[start:]).end() + start
                if else_at is None:
                    return text[head:end], ""
                return text[head:else_at], text[else_at + len(r"\else") : end]
        elif tok == "else":
            if depth == 1 and else_at is None:
                else_at = pos
        else:
            depth += 1
    raise AssertionError("unbalanced conditional")


_DEF = (
    r"\\(?:def|gdef|edef|xdef|newcommand\*?|renewcommand\*?|providecommand\*?|newdimen|newskip)"
    r"\s*\{?\\EndleafLand%s\b"
    r"|\\newlength\s*\{?\\EndleafLand%s\b"
)


# --- c1: endleaf-page.tex ----------------------------------------------------

@pytest.mark.parametrize("side", sorted(_VALUES))
def test_c1_page_defines_each_landscape_margin_once(side):
    code = _code(_PAGE)
    assert len(re.findall(_DEF % (side, side), code)) == 1, side
    value = _VALUES[side]
    assert re.search(rf"\\EndleafLand{side}\}}?\s*(?:=\s*|\{{){value}", code), (side, value)


# --- c2: endleaf-fit.tex landscape derivation --------------------------------

def _fit_landscape_parts():
    code = _code(_FIT)
    begin = _braced(code, code.index(r"\AtBeginDocument"))
    setland = _braced(code, code.index(r"\def\elfit@setlandscape"))
    return code, begin, setland


def test_c2_fit_landscape_uses_the_four_names():
    _, begin, setland = _fit_landscape_parts()
    for name in ("EndleafLandL", "EndleafLandR", "EndleafLandT", "EndleafLandB"):
        assert rf"\{name}" in begin, name
    for name in ("EndleafLandL", "EndleafLandT"):
        assert rf"\{name}" in setland, name


def test_c2_fit_has_one_ifdefined_fallback_with_equal_values():
    code = _code(_FIT)
    assert len(re.findall(r"\\ifdefined\s*\\EndleafLandL\b", code)) == 1
    start = re.search(r"\\ifdefined\s*\\EndleafLandL\b", code).start()
    then, other = _cond(code, start)
    block = then + " " + other
    for side, value in _VALUES.items():
        assert re.search(rf"\\EndleafLand{side}\}}?\s*(?:=\s*|\{{){value}", block), side


def test_c2_landscape_no_longer_derives_from_the_portrait_snapshot():
    _, begin, setland = _fit_landscape_parts()
    for macro in (r"\elfit@left", r"\elfit@right", r"\elfit@top", r"\elfit@bot"):
        assert not re.search(re.escape(macro) + r"(?![A-Za-z@])", begin), macro
    assert r"\elfit@portoddm" not in setland and r"\elfit@porttopm" not in setland
    assert r"\elfit@portevenm" not in setland


# --- c3: caption reserve in \elfit@bounded -----------------------------------

def _bounded():
    code = _code(_FIT)
    return _flat(_braced(code, code.index(r"\def\elfit@bounded")))


def test_c3_bounded_keeps_the_floor_and_names_the_reserve_parts():
    body = _bounded()
    assert r"\def\elfit@fencefloor{7}" in _flat(_code(_FIT))
    assert r"\elfit@minscale" in body and r"\elfit@fencefloor" in body
    for token in (r"\abovecaptionskip", r"\ElfitCaptionHeight", r"\elfit@capreserve", "ENDLEAF_SHELLTALL"):
        assert token in body, token
    assert r"3\baselineskip" in body.replace(" ", "") or r"\baselineskip" in body


def test_c3_reserve_applies_inside_a_wrapped_figure_or_table_float_only():
    body = _bounded()
    assert r"\abovecaptionskip" in body, "no caption reserve in \\elfit@bounded"
    at = body.index(r"\abovecaptionskip")
    starts = [m.start() for m in re.finditer(r"\\ifelfit@insidefloat(?![A-Za-z@])", body[:at])]
    assert starts, "the reserve must be chosen under \\ifelfit@insidefloat"
    # the governing block is the nearest one that still contains the reserve
    for start in reversed(starts):
        inside, outside = _cond(body, start)
        if r"\abovecaptionskip" in inside or r"\abovecaptionskip" in outside:
            break
    else:
        raise AssertionError("no \\ifelfit@insidefloat block contains \\abovecaptionskip")
    assert r"\abovecaptionskip" in inside and r"\elfit@capreserve" in inside
    assert r"\abovecaptionskip" not in outside
    assert re.search(r"\\elfit@capreserve\s*=\s*(?:0pt|\\z@)", outside), "outside a float the reserve is 0"


def _bound_register(body):
    """Register assigned \\elfit@landth under \\ifelfit@thisland and \\textheight in its else."""
    for m in re.finditer(r"\\ifelfit@thisland(?![A-Za-z@])", body):
        then, other = _cond(body, m.start())
        t = re.search(r"(\\[A-Za-z@]+)\s*=[^\\]*\\(?:dimexpr\s*)?\\?[^\\]*", then)
        o = re.search(r"(\\[A-Za-z@]+)\s*=", other)
        if t and o and t.group(1) == o.group(1) and r"\elfit@landth" in then and r"\textheight" in other:
            return t.group(1)
    return None


def test_c3_height_bound_is_landth_when_thisland_else_textheight():
    body = _bounded()
    assert _bound_register(body), "bound selection is not tied to \\ifelfit@thisland"
    # the height scale is computed against that bound, not the bare \textheight
    assert not re.search(r"\\Gscale@div\\elfit@h\{\\textheight\}", body.replace(" ", ""))


def test_c3_shelltall_avail_is_the_bound_itself():
    body = _bounded()
    bound = _bound_register(body)
    assert bound, "no bound register"
    assert "ENDLEAF_SHELLTALL" in body, "no SHELLTALL marker in \\elfit@bounded"
    at = body.index("ENDLEAF_SHELLTALL")
    depth, end = 0, len(body)
    for i in range(at, len(body)):  # end of the brace group that holds the marker
        if body[i] == "{":
            depth += 1
        elif body[i] == "}":
            if depth == 0:
                end = i
                break
            depth -= 1
    group = body[at:end]
    thes = list(re.finditer(r"\\the(\\[A-Za-z@]+)", group))
    assert len(thes) >= 2, group
    assert thes[-1].group(1) == bound, group
    assert r"\elfit@capreserve" not in group[thes[-2].start() :], "avail must not subtract the reserve"


# --- c4: layout_warn ---------------------------------------------------------

_FIT_LINE = "ENDLEAF_SHELLFIT 1 250.0pt 300.0pt 10.0 1"
_PAGE_LINE = "ENDLEAF_SHELLPAGE 1 2 landscape"


def _tall(height, avail, extra=""):
    return "\n".join([_FIT_LINE, _PAGE_LINE, f"ENDLEAF_SHELLTALL 1 {height}pt {avail}pt", extra, ""])


def _too_tall(log):
    return [w for w in layout_warn.layout_warnings(log) if w.get("code") == "layout_too_tall"]


def test_c4_tall_fence_gives_one_layout_too_tall_item():
    items = _too_tall(_tall("512.3", "478.0"))
    assert len(items) == 1
    item = items[0]
    assert item["packages"] == ["diagram"]
    assert item["overMm"] == round((512.3 - 478.0) * layout_warn._PT_TO_MM, 1)
    assert item["page"] == 2 and item["landscape"] is True
    assert "pg2" in item["message"] and "mm" in item["message"]


def test_c4_margin_below_the_minimum_gives_no_item():
    assert len(_too_tall(_tall("512.3", "478.0"))) == 1
    assert not _too_tall(_tall("478.5", "478.0"))
    assert layout_warn.MIN_OVERHANG_PT > 0.5


def test_c4_duplicate_fence_number_gives_one_item():
    log = _tall("512.3", "478.0", "ENDLEAF_SHELLTALL 1 512.3pt 478.0pt")
    assert len(_too_tall(log)) == 1


def test_c4_survives_the_line_round_trip():
    items = _too_tall(_tall("512.3", "478.0"))
    assert items
    back = layout_warn.parse_layout(layout_warn.layout_line(items))
    assert [w["code"] for w in back] == ["layout_too_tall"]
    assert back[0]["overMm"] == items[0]["overMm"] and back[0]["packages"] == ["diagram"]


def test_c4_reads_the_fence_lines_through_a_log_wrap():
    log = _tall("512.3", "478.0", "ENDLEAF_SHELLTURN 1")
    # TeX breaks a log line after max_print_line columns; a 9-column break splits each keyword.
    wrapped = "\n".join(line[i : i + 9] for line in log.splitlines() for i in range(0, max(len(line), 1), 9))
    assert "ENDLEAF_SHELLTALL" not in wrapped
    assert layout_warn.layout_warnings(wrapped) == layout_warn.layout_warnings(log)
    assert _too_tall(wrapped)


# --- TeX-level (skipped without the tools) -----------------------------------

_tex = pytest.mark.skipif(
    shutil.which("xelatex") is None or shutil.which("pdfinfo") is None, reason="xelatex/pdfinfo not installed"
)
_A4_L = "841.89 x 595.28"
_A4_P = "595.28 x 841.89"
_NONESCAPE = Path("/usr/local/bin/xelatex-nonescape")


def _pandoc3():
    if shutil.which("pandoc") is None:
        return False
    out = subprocess.run(["pandoc", "--version"], capture_output=True, text=True).stdout
    m = re.match(r"pandoc (\d+)", out)
    return bool(m and int(m.group(1)) >= 3)


_shell = pytest.mark.skipif(
    not (_pandoc3() and all(shutil.which(t) for t in ("xelatex", "pdfinfo", "pdftotext"))),
    reason="Markdown PDF path needs pandoc 3, xelatex and poppler (pdfinfo, pdftotext)",
)


def _pages(pdf):
    info = subprocess.run(["pdfinfo", "-f", "1", "-l", "99", str(pdf)], capture_output=True, text=True).stdout
    return [l.split(":", 1)[1].split("pts")[0].strip() for l in info.splitlines() if re.match(r"Page\s+\d+ size", l)]


_PROBE = (
    r"\typeout{R80TB \the\textwidth\space\the\textheight\space\the\paperwidth\space\the\paperheight"
    r"\space\the\EndleafPageL\space\the\EndleafPageR\space\the\EndleafPageT\space\the\EndleafPageB}"
)


def _compile(tmp_path, name, body, orientation=None):
    tex, _ = compose_with_body_line("document-shell", "InstruMeasure", body, root=_OWNED, orientation=orientation)
    tex = tex.replace(r"\end{document}", _PROBE + r"\end{document}")
    d = tmp_path / name
    d.mkdir()
    (d / "job.tex").write_text(tex, encoding="utf-8")
    env = dict(os.environ, TEXINPUTS=f".:{_SHARE / 'tex'}//:")
    subprocess.run(["xelatex", "-interaction=nonstopmode", "job.tex"], cwd=d, env=env, capture_output=True, timeout=240)
    log = _unwrap((d / "job.log").read_text(encoding="utf-8", errors="replace"))
    assert not re.search(r"^! ", log, re.MULTILINE), log[-3000:]
    return d, _pages(d / "job.pdf"), log


def _markdown_pdf(tmp_path, source, orientation):
    """The worker's Markdown PDF command (build_render_plan), on this checkout's files.

    Returns (pdf, pages, the final LaTeX pass of Pandoc's --verbose output),
    which is the text the sandbox reads the fence lines from.
    """
    job = JobSpec(source=source, input_kind="markdown", output_format="pdf", lane="InstruMeasure", orientation=orientation)
    plan = build_render_plan(job)
    (command,) = plan.commands
    (source_path,) = plan.files
    (tmp_path / "input.md").write_text(source, encoding="utf-8")
    lock = _SHARE / "lock-diagram.lua"
    if not _NONESCAPE.exists():
        # A dev box has no non-escape wrapper: lock TikZ to plain xelatex.
        lock = tmp_path / "lock.lua"
        lock.write_text((_SHARE / "lock-diagram.lua").read_text(encoding="utf-8").replace(str(_NONESCAPE), "xelatex"))
    local = {
        source_path: str(tmp_path / "input.md"),
        plan.output_path: str(tmp_path / "out.pdf"),
        f"{SHARE_ROOT}/diagram.lua": str(_DIAGRAM),
        f"{SHARE_ROOT}/lock-diagram.lua": str(lock),
    }
    argv = []
    for arg in command:
        if arg in local:
            arg = local[arg]
        elif arg.startswith(SHARE_ROOT + "/"):
            arg = str(_SHARE) + arg[len(SHARE_ROOT) :]
        elif "-cnf-line=open" in arg and not _NONESCAPE.exists():
            # Pandoc passes an absolute input.tex; only the wrapper makes it relative.
            continue
        argv.append(arg)
    env = dict(os.environ, TEXINPUTS=f".:{_SHARE / 'tex'}//:")
    done = subprocess.run(argv, cwd=tmp_path, capture_output=True, env=env, timeout=300)
    out = done.stdout + done.stderr
    assert done.returncode == 0, out[-3000:]
    return tmp_path / "out.pdf", _pages(tmp_path / "out.pdf"), _unwrap(layout_warn.final_pass(out))


@_shell
def test_a_landscape_fence_with_caption_fits_one_page_at_scale_one(tmp_path):
    """One A4 landscape page, every fence at scale 1, no SHELLTALL or
    layout_too_tall, and the caption ends above the bottom margin (footskip)."""
    source = (
        '```{.tikz caption="Two line caption that is long enough to wrap onto a second line of the caption '
        'on this landscape page, with a few more words to be sure."}\n'
        "\\begin{tikzpicture}\n\\draw (0,0) rectangle (20cm,11.5cm);\n\\end{tikzpicture}\n```\n"
    )
    pdf, pages, log = _markdown_pdf(tmp_path, source, "landscape")
    assert pages == [_A4_L]
    fit = re.findall(r"ENDLEAF_SHELLFIT \d+ [0-9.]+pt [0-9.]+pt [0-9.]+ ([0-9.]+)", log)
    assert fit and all(float(s) == 1.0 for s in fit), log[-3000:]
    assert "ENDLEAF_SHELLTALL" not in log
    assert "layout_too_tall" not in str(layout_warn.layout_warnings(log))
    out = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], capture_output=True, text=True).stdout
    ys = [float(y) for y, w in re.findall(r'yMax="([0-9.]+)">([^<]*)<', out) if w in ("Two", "caption", "wrap", "sure.")]
    # text block bottom = paper height - 22 mm (bp); the footskip sits below it
    assert ys and max(ys) <= 595.28 - 22 / 25.4 * 72 + 1, ys


# Case A2 numbers (TeX pt, 72.27 per inch), from endleaf-fit.tex and the lane template:
#   landth   = 210 mm - 20 mm (T) - 22 mm (B) = 168 mm = 478.0 pt (text width 257 mm)
#   reserve  = 3 * \baselineskip (12 pt at 10 pt) + \abovecaptionskip (10 pt) = 46 pt
#              (\ElfitCaptionHeight is not defined by any template)
#   bound    = landth - reserve = 432.0 pt for the fence image
#   natural  = 17 cm + 0.4 pt line = 484.0 pt, so scale = 432.0 / 484.0 = 0.8926
#   without the reserve the scale would be 478.0 / 484.0 = 0.9876 and the
#   two-line caption (34 pt with its skip) would end 478 + 34 pt down, past the text block.
_LAND_TH = 168 / 25.4 * 72.27
_RESERVE = 3 * 12 + 10
_NATURAL_H = 17 * 28.4528 + 0.4
_A2_CAPTION = (
    "A tall reference figure on a landscape page. The caption names the box, says why it is as tall as it "
    "is, and what a reader should check against it, and it is long enough to run onto a second line of the "
    "257 mm text width of the page."
)


@_shell
def test_a2_tall_fence_with_long_caption_fits_one_page(tmp_path):
    """A 17 cm tall fence is taller than the landscape text block minus the caption
    reserve, so SHELLFIT must scale it below 1 (type stays above 7 pt) and the
    wrapped caption still ends above the bottom margin."""
    source = (
        "```{.tikz caption=\"" + _A2_CAPTION + "\"}\n"
        "\\begin{tikzpicture}\n\\draw (0,0) rectangle (20cm,17cm);\n\\end{tikzpicture}\n```\n"
    )
    pdf, pages, log = _markdown_pdf(tmp_path, source, "landscape")
    assert pages == [_A4_L]
    fit = re.findall(r"ENDLEAF_SHELLFIT \d+ [0-9.]+pt [0-9.]+pt [0-9.]+ ([0-9.]+)", log)
    assert len(fit) == 1, log[-3000:]
    scale = float(fit[0])
    assert "ENDLEAF_SHELLTALL" not in log
    assert "layout_too_tall" not in str(layout_warn.layout_warnings(log))
    # designed outcome: height-bound scale = (landth - reserve) / natural, not 1, above the 7 pt floor
    want = (_LAND_TH - _RESERVE) / _NATURAL_H
    assert abs(scale - want) < 0.01, (scale, want)
    assert scale < 1 and scale * 10 > 7
    out = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], capture_output=True, text=True).stdout
    words = set(_A2_CAPTION.split())
    ys = [float(y) for y, w in re.findall(r'yMax="([0-9.]+)">([^<]*)<', out) if w in words]
    lines = sorted({round(y, 1) for y in ys})
    limit = 595.28 - 22 / 25.4 * 72 + 1
    msg = f"caption lines={len(lines)} yMax={max(ys, default=None)} limit={limit:.2f} slack={limit - max(ys, default=0):.2f} scale={scale}"
    assert ys and len(lines) >= 2, msg
    assert max(ys) <= limit, msg
    # negative control from the measured output: at the reserve-free scale the fence is taller by
    # (no_reserve - scale) * natural height (TeX pt -> bp), so the caption would end that much lower
    no_reserve = _LAND_TH / _NATURAL_H
    assert scale < no_reserve - 0.05, (scale, no_reserve)
    projected = max(ys) + (no_reserve - scale) * _NATURAL_H * 72 / 72.27
    assert projected > limit, f"projected caption yMax {projected:.2f} must exceed limit {limit:.2f}; {msg}"


@_tex
def test_b_portrait_fence_is_unchanged(tmp_path):
    """A portrait TeX body keeps the class-derived text block. (A TeX body has no
    fences: Pandoc's \\pandocbounded, which logs SHELLFIT, is Markdown-only.)"""
    body = "\\begin{tikzpicture}\\draw (0,0) rectangle (12cm,6cm);\\end{tikzpicture}\n"
    _, pages, log = _compile(tmp_path, "port", body)
    assert pages == [_A4_P]
    probe = re.findall(r"R80TB " + " ".join([r"([0-9.]+)pt"] * 8), log)
    assert probe, "text-block probe line missing from the log"
    tw, th, pw, ph, l, r, t, b = (float(x) for x in probe[-1])
    # portrait baseline: the text block is the paper minus the class-derived page margins
    assert abs(tw - (pw - l - r)) < 0.5 and abs(th - (ph - t - b)) < 0.5, probe[-1]
    assert abs(pw - 595.28 * 72.27 / 72) < 1 and abs(ph - 841.89 * 72.27 / 72) < 1
    assert tw < pw and th < ph and tw > 0.5 * pw and th > 0.5 * ph
