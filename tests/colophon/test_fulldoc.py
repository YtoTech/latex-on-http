# Copyright (C) 2026 Inkmirage (Endleaf render worker modifications)
# SPDX-License-Identifier: AGPL-3.0-or-later
"""ENDLEAF-R39 and ENDLEAF-R49. fulldoc is PDF only; wide sysml is landscape A4."""

import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from colophon.enums import JobRejected, parse_job
from colophon.limits import FULLDOC_MAX_PAGES
from colophon.pdf_pages import (
    fulldoc_page_count,
    fulldoc_page_failure,
    pages_from_log,
    pages_from_pdf,
)
from colophon.revision import package_set, package_set_hash
from colophon.sandbox_render import render_to_stdout
from colophon.templates import compose
from tests.colophon.conftest import valid_body

_ROOT = Path(__file__).resolve().parents[2]


def _kind_fixtures():
    path = _ROOT / "container/run_kind_fixtures.py"
    spec = importlib.util.spec_from_file_location("endleaf_kind_fixtures_fulldoc", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_KIND_FIXTURES = _kind_fixtures()
_CJK_TOKENS_PRESENT = _KIND_FIXTURES._cjk_tokens_present
_BODY_TYPE_ERROR = _KIND_FIXTURES._body_type_error
_OWNED = _ROOT / "colophon/share/templates/owned"
_KINDS = _ROOT / "tests/colophon/fixtures/kinds"
_REVIEW = _ROOT / "tests/colophon/fixtures/review"
_TEXINPUTS = os.pathsep.join(
    (
        str(_ROOT / "colophon/share/tex/latex/colophon-v1"),
        str(_ROOT / "colophon/share/tex/latex/endleaf-floorplan"),
        str(_ROOT / "colophon/share/tex/latex/sysml-tikz"),
        str(_ROOT / "vendor/pidcircuittikz"),
        "",
    )
)
_PACKAGE_SET_HASH = "73d55216488d240edccd26168576fcb402ce10794e04a3ef5ee8aec2bb166b98"
_FIT = re.compile(
    r"ENDLEAF_FIT shipped=([0-9.]+)pt line=([0-9.]+)pt "
    r"high=([0-9.]+)pt avail=([0-9.]+)pt "
    r"uniform=([0-9.]+) unit=([0-9.]+) type=([0-9.]+) "
    r"page=(portrait|landscape)"
)
_ENDLEAF_FIT_BLOB = "c4eb9d472d1c6d86fbab44967a731ed338dcf837"  # Endleaf landscape margins and caption-aware fit (ENDLEAF-R80)
# Sysml preamble is the R49 vendor plus __PAPER__ for job pageSize.
_ENDLEAF_SYSML_PREAMBLE_BLOB = "3b38c57495eb15afc7233c7758c5865d84616716"
_BOX = re.compile(
    r"SYSMLBOX\s+(\S+)\s+([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)"
)
_WORD = re.compile(
    r'<word xMin="([0-9.]+)" yMin="([0-9.]+)" xMax="([0-9.]+)" yMax="([0-9.]+)">(.*?)</word>'
)
_PAGE = re.compile(r'<page width="([0-9.]+)" height="([0-9.]+)">')
_FIT_TEX = _ROOT / "colophon/share/tex/latex/colophon-v1/endleaf-fit.tex"


def _type_ready():
    if shutil.which("kpsewhich") is None:
        return False
    found = subprocess.run(
        ["kpsewhich", "texgyrepagella-regular.otf"],
        check=False,
        capture_output=True,
        text=True,
    )
    return found.returncode == 0 and bool(found.stdout.strip())


def test_package_set_hash_is_unchanged():
    assert package_set_hash(package_set()) == _PACKAGE_SET_HASH


def test_cjk_tokens_tolerate_pdftotext_breaks():
    extracted = "配\n置見圖 1"
    assert _CJK_TOKENS_PRESENT(extracted, "配置")
    assert _CJK_TOKENS_PRESENT("配 置見圖 1", "配置")
    assert _CJK_TOKENS_PRESENT("配置見圖 1", "配置")
    assert _CJK_TOKENS_PRESENT("幫\n浦監測", "幫浦")
    assert _CJK_TOKENS_PRESENT("參 數", "參數")
    assert not _CJK_TOKENS_PRESENT("配見圖 1", "配置")
    assert not _CJK_TOKENS_PRESENT("置見圖 1", "配置")
    assert not _CJK_TOKENS_PRESENT("配設見圖 1", "配置")
    assert not _CJK_TOKENS_PRESENT("置\n配見圖 1", "配置")
    assert not _CJK_TOKENS_PRESENT("幫監測", "幫浦")
    assert not _CJK_TOKENS_PRESENT("參見", "參數")


_PDFONTS_HEADER = (
    "name                                 type              encoding         "
    "emb sub uni object ID",
    "------------------------------------ ----------------- ---------------- "
    "--- --- --- ---------",
)
_PDFONTS_PAGELLA = (
    "SQMVLL+TeXGyrePagella-Regular-Identity-H CID Type 0C       Identity-H"
    "       yes yes yes      5  0"
)
_PDFONTS_CMMI = (
    "QXLMBR+CMMI10                        Type 1C           Builtin"
    "          yes yes yes     19  0"
)
_PDFONTS_CMR7 = (
    "NWVKSU+CMR7                          Type 1C           Builtin"
    "          yes yes yes     20  0"
)
_PDFONTS_CMR10 = (
    "AAAAAA+CMR10                         Type 1            Builtin"
    "          yes yes yes      1  0"
)
_PDFONTS_LMROMAN = (
    "BAAAAA+LMRoman10-Regular             CID Type 0C       Identity-H"
    "       yes yes yes      3  0"
)


_PDFONTS_TAGGED_CURSOR = (
    "NCMRNR+TeXGyreCursor-Regular         CID Type 0C       Identity-H"
    "        yes yes yes     14  0"
)


def test_body_type_ignores_the_subset_tag():
    """The random six-letter subset tag is not the font name (NCMRNR+ once failed a bake)."""
    for tag in ("NCMRNR", "CMRAAA", "AACMR7", "LMROMA"):
        row = _PDFONTS_TAGGED_CURSOR.replace("NCMRNR", tag)
        assert _BODY_TYPE_ERROR(list(_PDFONTS_HEADER) + [_PDFONTS_PAGELLA, row]) is None, tag
    assert _KIND_FIXTURES.font_name(_PDFONTS_TAGGED_CURSOR) == "TeXGyreCursor-Regular"
    assert _KIND_FIXTURES.font_name(_PDFONTS_CMR10) == "CMR10"
    # A real CMR10 behind a tag still fails.
    body_cmr = _BODY_TYPE_ERROR(list(_PDFONTS_HEADER) + [_PDFONTS_PAGELLA, _PDFONTS_CMR10.replace("AAAAAA", "NCMRNR")])
    assert body_cmr and "Computer Modern" in body_cmr


def test_body_type_allows_cmr7_math_not_cmr10_or_latin_modern():
    math_ok = _BODY_TYPE_ERROR(
        list(_PDFONTS_HEADER) + [_PDFONTS_PAGELLA, _PDFONTS_CMMI, _PDFONTS_CMR7]
    )
    assert math_ok is None
    body_cmr = _BODY_TYPE_ERROR(
        list(_PDFONTS_HEADER) + [_PDFONTS_PAGELLA, _PDFONTS_CMR10]
    )
    assert body_cmr and "Computer Modern" in body_cmr
    no_pagella = _BODY_TYPE_ERROR(list(_PDFONTS_HEADER) + [_PDFONTS_CMR7])
    assert no_pagella and "Pagella" in no_pagella
    latin = _BODY_TYPE_ERROR(
        list(_PDFONTS_HEADER) + [_PDFONTS_PAGELLA, _PDFONTS_LMROMAN]
    )
    assert latin and "Latin Modern" in latin


def test_fulldoc_html_and_docx_are_refused():
    for output_format in ("html", "docx"):
        with pytest.raises(JobRejected) as caught:
            parse_job(
                valid_body(
                    templateId="fulldoc",
                    outputFormat=output_format,
                    body="Hello.",
                )
            )
        assert caught.value.reason == "outputFormat"
    job = parse_job(valid_body(templateId="fulldoc", outputFormat="pdf", body="Hello."))
    assert job.template_id == "fulldoc"
    assert job.output_format == "pdf"
    assert job.input_kind == "tex"


def test_page_cap_message():
    assert FULLDOC_MAX_PAGES == 16
    assert fulldoc_page_failure(None) == "fulldoc page count is unreadable"
    assert fulldoc_page_failure(16) is None
    assert fulldoc_page_failure(1) is None
    assert fulldoc_page_failure(17) == "fulldoc exceeds maxPages 16 (got 17 pages)"
    assert pages_from_log("Output written on job.pdf (16 pages, 100 bytes).") == 16
    assert pages_from_log("no pages here") is None
    assert pages_from_pdf(b"%PDF-1.5\n/Type /Pages\n/Type /Page\n") == 1
    assert pages_from_pdf(b"not a pdf") is None
    assert fulldoc_page_count(b"not a pdf", "Output written on job.pdf (2 pages).") == 2


def test_vendored_fit_matches_endleaf_r49():
    fit_blob = subprocess.check_output(
        ["git", "hash-object", str(_FIT_TEX)],
        text=True,
    ).strip()
    preamble = _OWNED / "sysml" / "preamble.tex"
    preamble_blob = subprocess.check_output(
        ["git", "hash-object", str(preamble)],
        text=True,
    ).strip()
    assert fit_blob == _ENDLEAF_FIT_BLOB
    assert preamble_blob == _ENDLEAF_SYSML_PREAMBLE_BLOB


def test_endleaf_fit_landscapes_at_declared_type_and_refuses_crush():
    text = _FIT_TEX.read_text(encoding="utf-8")
    assert "ENDLEAF-R49" in text
    assert r"\AtBeginDocument" in text
    assert r"\elfit@portline" in text
    assert r"\elfit@landpw=\paperheight" in text
    assert r"\elfit@landph=\paperwidth" in text
    assert r"\elfit@setlandscape" in text
    assert r"\pdfpagewidth" in text
    assert r"page=\elfit@page" in text
    assert r"\elfit@uniform{1}" in text
    assert r"\xdef\elfit@shown{\elfit@bodyreq}" in text
    assert "7pt is a floor, not a fit target" in text
    assert r"\PackageError{endleaf}" in text
    assert "Text was not shrunk" in text
    assert r"\elfit@sfloor" not in text
    assert "coordshrink" not in text
    assert r"\resizebox" not in text
    assert "ENDLEAF_WIDE_PICTURE" in text
    assert r"\RenewDocumentEnvironment{figure}" not in text
    assert r"\RenewDocumentEnvironment{table}" not in text
    assert r"\def\figure" in text
    # ENDLEAF-R59-FLOAT. No forced break: a landscape figure is a
    # page-only float shipped alone on a landscape float page.
    code = "\n".join(line.split("%", 1)[0] for line in text.splitlines())
    assert r"\newpage" not in code
    assert r"\clearpage" not in code
    assert r"\elfit@markland" in text
    assert r"\def\@tryfcolumn" in text
    assert r"\def\@testwrongwidth" in text
    assert r"\def\@outputpage" in text
    assert "ENDLEAF_OVERHANG" in text
    assert r"renewcommand{\sysml@typeset}" in text
    assert r"\begin{minipage}{\linewidth}" in text


def test_sysml_preamble_does_not_freeze_portrait_minipage():
    text = (_OWNED / "sysml" / "preamble.tex").read_text(encoding="utf-8")
    assert r"\documentclass[__PAPER__]{article}" in text
    assert r"\input{endleaf-fit.tex}" in text
    assert "__BODY__" in text
    after_begin = text.split(r"\begin{document}", 1)[1]
    assert "__BODY__" in after_begin
    assert r"\begin{minipage}" not in after_begin
    assert r"\pdfpagewidth=" not in after_begin
    assert r"\end{document}" in after_begin


def _xelatex(tmp_path, name, tex):
    if not _type_ready():
        tex = tex.replace("\\input{endleaf-type.tex}\n", "")
    (tmp_path / name).write_text(tex, encoding="utf-8")
    env = os.environ.copy()
    env["TEXINPUTS"] = _TEXINPUTS + env.get("TEXINPUTS", "")
    completed = subprocess.run(
        [
            "xelatex",
            "-no-shell-escape",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            name,
        ],
        cwd=tmp_path,
        check=False,
        timeout=180,
        capture_output=True,
        env=env,
    )
    log_path = tmp_path / (Path(name).stem + ".log")
    log = (
        log_path.read_text(encoding="utf-8", errors="replace")
        if log_path.is_file()
        else completed.stdout.decode("utf-8", "replace")
    )
    assert completed.returncode == 0, log[-2000:]
    pdf = tmp_path / (Path(name).stem + ".pdf")
    assert pdf.is_file()
    return pdf, log


def _text(pdf):
    extracted = subprocess.run(
        ["pdftotext", "-raw", str(pdf), "-"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert extracted.returncode == 0
    return extracted.stdout


def _pages(pdf):
    info = subprocess.run(
        ["pdfinfo", str(pdf)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert info.returncode == 0, info.stderr
    for line in info.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    raise AssertionError(info.stdout)


def _unwrap(log):
    """Join TeX log lines. A line of 79 columns or more is a hard wrap."""
    pieces = []
    pending = ""
    for line in log.splitlines():
        pending = pending + line if pending else line
        if len(line) < 79:
            pieces.append(pending)
            pending = ""
    if pending:
        pieces.append(pending)
    return "\n".join(pieces)


def _fit(log):
    found = _FIT.search(_unwrap(log))
    assert found, _unwrap(log)[-2000:]
    shipped, line, high, avail, uniform, unit, type_size = (
        float(item) for item in found.groups()[:7]
    )
    return {
        "shipped": shipped,
        "line": line,
        "high": high,
        "avail": avail,
        "uniform": uniform,
        "unit": unit,
        "type": type_size,
        "type_text": found.group(7),
        "page": found.group(8),
    }


# pdfinfo without -f/-l prints "Page size:". With -f N -l N, poppler
# 24+ prints "Page    N size:" (same numbers). Accept both.
_PAGE_SIZE_LINE = re.compile(
    r"^Page(?:\s+\d+)?\s+size:\s+([0-9.]+)\s+x\s+([0-9.]+)"
)


def test_pdfinfo_page_size_line_accepts_numbered_and_plain():
    plain = _PAGE_SIZE_LINE.match("Page size:  595.28 x 841.89 pts (A4)")
    numbered = _PAGE_SIZE_LINE.match("Page    1 size:  841.89 x 595.28 pts (A4)")
    assert plain.groups() == ("595.28", "841.89")
    assert numbered.groups() == ("841.89", "595.28")


def _page_size(pdf, page=1):
    info = subprocess.run(
        ["pdfinfo", "-f", str(page), "-l", str(page), str(pdf)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert info.returncode == 0, info.stderr
    for line in info.stdout.splitlines():
        match = _PAGE_SIZE_LINE.match(line)
        if match:
            return float(match.group(1)), float(match.group(2))
    raise AssertionError(info.stdout)


def _shipped_boxes(log):
    text = _unwrap(log)
    start = text.rfind("ENDLEAF_FIT_SHIP")
    assert start >= 0, text[-1500:]
    end = text.find("\nENDLEAF_FIT ", start)
    assert end > start, text[start : start + 1500]
    boxes = []
    for kind, x0, y0, x1, y1 in _BOX.findall(text[start:end]):
        xa, xb = sorted((float(x0), float(x1)))
        ya, yb = sorted((float(y0), float(y1)))
        boxes.append((kind, xa, ya, xb, yb))
    return boxes


def _overlap(a0, a1, b0, b1):
    return min(a1, b1) - max(a0, b0)


def _crosses_outline(label, outline, tol=0.4):
    """A hit on both axes that is not strictly inside the outline."""
    ox = _overlap(label[1], label[3], outline[1], outline[3])
    oy = _overlap(label[2], label[4], outline[2], outline[4])
    if ox <= tol or oy <= tol:
        return False
    inside = (
        label[1] >= outline[1] - 0.05
        and label[3] <= outline[3] + 0.05
        and label[2] >= outline[2] - 0.05
        and label[4] <= outline[4] + 0.05
    )
    return not inside


def _bbox_words(pdf, page):
    extracted = subprocess.run(
        ["pdftotext", "-bbox", "-f", str(page), "-l", str(page), str(pdf), "-"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert extracted.returncode == 0, extracted.stderr
    page_box = _PAGE.search(extracted.stdout)
    assert page_box, extracted.stdout[:500]
    words = [
        {
            "xMin": float(x0),
            "yMin": float(y0),
            "xMax": float(x1),
            "yMax": float(y1),
            "text": word,
        }
        for x0, y0, x1, y1, word in _WORD.findall(extracted.stdout)
    ]
    return float(page_box.group(1)), float(page_box.group(2)), words


@pytest.mark.skipif(shutil.which("xelatex") is None, reason="xelatex is not installed")
def test_fulldoc_fixture_compiles(tmp_path):
    body = (_KINDS / "fulldoc.tex").read_text(encoding="utf-8")
    tex = compose("fulldoc", "lane-a", body, _OWNED)
    typed = _type_ready()
    pdf, log = _xelatex(tmp_path, "fulldoc.tex", tex)
    assert "Overfull \\hbox" not in log
    pages = _pages(pdf)
    assert 1 <= pages <= 16
    text = _text(pdf)
    for needle in ("幫浦", "參數", "配置"):
        assert _CJK_TOKENS_PRESENT(text, needle), text
    fit = _fit(log)
    assert fit["uniform"] == pytest.approx(1, abs=0.01)
    assert fit["unit"] == pytest.approx(1, abs=0.001)
    assert fit["type"] == pytest.approx(10, abs=0.05)
    assert fit["type_text"] == "10"
    assert fit["page"] == "landscape"
    assert fit["shipped"] <= fit["line"] + 0.2
    assert fit["high"] <= fit["avail"] + 0.2
    assert not re.search(r"type\s+\d+\s*pt", text)
    assert "type 7 pt" not in text
    assert "View" not in text
    assert "overrides" not in text
    assert pages >= 2
    _assert_float_page_stacks_at_the_top(pdf)
    fonts = subprocess.run(
        ["pdffonts", str(pdf)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert fonts.returncode == 0, fonts.stderr
    rows = fonts.stdout.splitlines()
    if typed:
        problem = _BODY_TYPE_ERROR(rows)
        assert problem is None, fonts.stdout
    else:
        assert rows[2:]
        for row in rows[2:]:
            # name and type vary in width. emb sub uni sit before the object id.
            assert row.split()[-5] == "yes", row


def _assert_float_page_stacks_at_the_top(pdf):
    """Figure 2 and Figure 3 share the top of a portrait float page."""
    pages = _pages(pdf)
    found = None
    for page in range(1, pages + 1):
        _width, height, words = _bbox_words(pdf, page)
        captions = []
        for index, word in enumerate(words):
            if word["text"] != "Figure" or index + 1 >= len(words):
                continue
            number = words[index + 1]["text"].rstrip(":")
            if number in {"2", "3"}:
                captions.append(word["yMin"])
        if len(captions) >= 2:
            found = (height, captions, [word["text"] for word in words])
            break
    assert found is not None
    height, captions, labels = found
    assert captions == sorted(captions)
    assert len(captions) >= 2, labels
    assert captions[0] < 220
    assert max(captions) < height * 0.45
    assert captions[-1] - captions[0] < 180


def _assert_labels_clear_outlines(boxes):
    labels = [box for box in boxes if box[0] in {"text", "plab"}]
    outlines = [box for box in boxes if box[0] == "part"]
    lines = [box for box in boxes if box[0] == "line"]
    assert labels and outlines, boxes
    for label in labels:
        for outline in outlines:
            assert not _crosses_outline(label, outline), (label, outline)
        for line in lines:
            assert (
                _overlap(label[1], label[3], line[1], line[3]) <= 0.4
                or _overlap(label[2], label[4], line[2], line[4]) <= 0.4
            ), (label, line)


@pytest.mark.skipif(shutil.which("xelatex") is None, reason="xelatex is not installed")
def test_wide_sysml_canvas_is_landscape_at_declared_type(tmp_path):
    body = "\\makeatletter\\sysml@marktracetrue\\makeatother\n" + (
        _REVIEW / "wide-175.tex"
    ).read_text(encoding="utf-8")
    tex = compose("sysml", "lane-a", body, _OWNED)
    pdf, log = _xelatex(tmp_path, "wide.tex", tex)
    assert "Overfull \\hbox" not in log
    assert "Overfull \\vbox" not in log
    fit = _fit(log)
    assert fit["shipped"] <= fit["line"] + 0.2
    assert fit["high"] <= fit["avail"] + 0.2
    assert fit["uniform"] == pytest.approx(1, abs=0.01)
    assert fit["unit"] == pytest.approx(1, abs=0.001)
    assert fit["type"] == pytest.approx(10, abs=0.05)
    assert fit["type_text"] == "10"
    assert fit["page"] == "landscape"
    assert _pages(pdf) == 1
    width, height = _page_size(pdf)
    assert width > height
    assert width == pytest.approx(841.89, abs=1)
    assert height == pytest.approx(595.28, abs=1)
    text = _text(pdf)
    assert "參數" in text
    assert not re.search(r"type\s+10\s*pt", text)
    assert "type 7 pt" not in text
    assert "View" not in text
    assert "overrides" not in text
    _assert_labels_clear_outlines(_shipped_boxes(log))


@pytest.mark.skipif(shutil.which("xelatex") is None, reason="xelatex is not installed")
def test_narrow_sysml_canvas_stays_portrait_at_declared_type(tmp_path):
    body = (
        "\\begin{sysmlfigure}[view={narrow}, revision={keep}, "
        "overrides={none}, depth={1}, body size={10}]\n"
        "\\begin{sysmlcanvas}\n"
        "\\sysmlpart{N.box}{8}{8}{18}{18}\n"
        "\\sysmllabel[name]{17}{14}{幫浦}\n"
        "\\end{sysmlcanvas}\n"
        "\\end{sysmlfigure}\n"
    )
    tex = compose("sysml", "lane-a", body, _OWNED)
    pdf, log = _xelatex(tmp_path, "narrow.tex", tex)
    assert "Overfull \\hbox" not in log
    assert "Overfull \\vbox" not in log
    assert _pages(pdf) == 1
    fit = _fit(log)
    assert fit["page"] == "portrait"
    assert fit["uniform"] == pytest.approx(1, abs=0.01)
    assert fit["unit"] == pytest.approx(1, abs=0.001)
    assert fit["type"] == pytest.approx(10, abs=0.05)
    assert fit["type_text"] == "10"
    width, height = _page_size(pdf)
    assert height > width
    assert width == pytest.approx(595.28, abs=1)
    assert height == pytest.approx(841.89, abs=1)
    text = _text(pdf)
    assert "View" not in text
    assert "overrides" not in text
    assert "keep" in text
    assert "幫浦" in text
    assert not re.search(r"type\s+10\s*pt", text)


@pytest.mark.skipif(shutil.which("xelatex") is None, reason="xelatex is not installed")
def test_tall_sysml_canvas_refuses_instead_of_crush(tmp_path):
    body = (_REVIEW / "tall-split.tex").read_text(encoding="utf-8")
    tex = compose("sysml", "lane-a", body, _OWNED)
    if not _type_ready():
        tex = tex.replace("\\input{endleaf-type.tex}\n", "")
    (tmp_path / "tall.tex").write_text(tex, encoding="utf-8")
    env = os.environ.copy()
    env["TEXINPUTS"] = _TEXINPUTS + env.get("TEXINPUTS", "")
    completed = subprocess.run(
        [
            "xelatex",
            "-no-shell-escape",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            "tall.tex",
        ],
        cwd=tmp_path,
        check=False,
        timeout=180,
        capture_output=True,
        env=env,
    )
    log_path = tmp_path / "tall.log"
    log = (
        log_path.read_text(encoding="utf-8", errors="replace")
        if log_path.is_file()
        else completed.stdout.decode("utf-8", "replace")
    )
    assert completed.returncode != 0, log[-2000:]
    unwrapped = _unwrap(log)
    assert "Text was not shrunk" in unwrapped
    assert "does not fit portrait A4 at the declared type size" in unwrapped


@pytest.mark.skipif(shutil.which("xelatex") is None, reason="xelatex is not installed")
def test_hash_in_a_float_body_compiles(tmp_path):
    body = (_REVIEW / "hash-float.tex").read_text(encoding="utf-8")
    tex = compose("fulldoc", "lane-a", body, _OWNED)
    pdf, _log = _xelatex(tmp_path, "hash.tex", tex)
    assert _pages(pdf) == 1
    text = _text(pdf)
    assert "#" in text
    assert "0" in text and "2" in text


@pytest.mark.skipif(shutil.which("xelatex") is None, reason="xelatex is not installed")
def test_plain_pictures_are_not_fitted(tmp_path):
    body = (
        "\\begin{tikzpicture}\n"
        "\\draw (0,0) -- (15,0);\n"
        "\\end{tikzpicture}\n"
        "\\begin{circuitikz}\n"
        "\\draw (0,0) to[R] (15,0);\n"
        "\\end{circuitikz}\n"
    )
    tex = compose("fulldoc", "lane-a", body, _OWNED)
    _pdf, log = _xelatex(tmp_path, "widepic.tex", tex)
    unwrapped = _unwrap(log)
    warnings = re.findall(
        r"ENDLEAF_WIDE_PICTURE width=([0-9.]+)pt line=([0-9.]+)pt", unwrapped
    )
    assert len(warnings) == 2, unwrapped[-2000:]
    for width, line in warnings:
        assert float(width) > float(line)
    assert "ENDLEAF_FIT " not in unwrapped


def test_float_bodies_are_not_collected():
    fit = _FIT_TEX.read_text(encoding="utf-8")
    assert "\\def\\figure" in fit
    assert "\\def\\table" in fit
    assert "\\elfit@figopt" in fit
    assert "\\RenewDocumentEnvironment{figure}" not in fit
    assert "\\RenewDocumentEnvironment{table}" not in fit
    assert "\\resizebox" not in fit
    assert "ENDLEAF_WIDE_PICTURE" in fit


def _bind_tex(monkeypatch, tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    wrapper = bindir / "xelatex-nonescape"
    shutil.copy(_ROOT / "container/xelatex-nonescape", wrapper)
    wrapper.chmod(0o755)
    monkeypatch.setattr("colophon.render_plan.XELATEX_BIN", str(wrapper))
    monkeypatch.setattr("colophon.templates.SHARE_ROOT", str(_ROOT / "colophon/share"))
    monkeypatch.setenv("TEXINPUTS", _TEXINPUTS + os.environ.get("TEXINPUTS", ""))
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")


class _Capture:
    def __init__(self):
        self.buffer = io.BytesIO()
        self._text = []

    def write(self, data):
        if isinstance(data, bytes):
            self.buffer.write(data)
            return len(data)
        self._text.append(data)
        return len(data)

    def flush(self):
        return None

    @property
    def text(self):
        return "".join(self._text)


def _render(payload, monkeypatch):
    stdout = _Capture()
    stderr = _Capture()
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)
    code = render_to_stdout(json.dumps(payload).encode("utf-8"))
    return code, stdout.buffer.getvalue(), stderr.text


@pytest.mark.skipif(shutil.which("xelatex") is None, reason="xelatex is not installed")
def test_fulldoc_page_cap_after_compile(tmp_path, monkeypatch):
    _bind_tex(monkeypatch, tmp_path)
    sixteen = "Page.\\newpage\n" * 15 + "Page.\n"
    code, pdf, err = _render(
        valid_body(templateId="fulldoc", outputFormat="pdf", body=sixteen),
        monkeypatch,
    )
    assert code == 0, err[-2000:]
    assert pdf.startswith(b"%PDF")
    assert "ENDLEAF_STATUS ok" in err
    seventeen = "Page.\\newpage\n" * 16 + "Page.\n"
    code, _pdf, err = _render(
        valid_body(templateId="fulldoc", outputFormat="pdf", body=seventeen),
        monkeypatch,
    )
    assert code == 11, err[-2000:]
    assert "ENDLEAF_STATUS cap" in err
    assert "fulldoc exceeds maxPages 16 (got 17 pages)" in err
    diag = json.loads(err.split("ENDLEAF_DIAG ", 1)[1].splitlines()[0])
    assert diag["message"] == "fulldoc exceeds maxPages 16 (got 17 pages)"


def _assert_refs_resolved(text):
    """Captions number on the first pass. ``??`` is an unresolved \\ref."""
    assert "??" not in text
    assert re.search(r"Figure\s+1", text)
    assert re.search(r"Figure\s+2", text)
    assert re.search(r"Figure\s+3", text)
    assert re.search(r"Table\s+1", text)
    assert re.search(r"圖\s*1", text), text
    assert re.search(r"表\s*1", text), text
    assert re.search(r"Section\s+1", text), text


@pytest.mark.skipif(
    shutil.which("xelatex") is None
    or shutil.which("pdftotext") is None
    or shutil.which("pdfinfo") is None,
    reason="xelatex, pdftotext, or pdfinfo is not installed",
)
def test_fulldoc_cross_references_resolve(tmp_path, monkeypatch):
    _bind_tex(monkeypatch, tmp_path)
    body = (_KINDS / "fulldoc.tex").read_text(encoding="utf-8")
    code, pdf, err = _render(
        valid_body(templateId="fulldoc", outputFormat="pdf", lane="lane-a", body=body),
        monkeypatch,
    )
    assert code == 0, err[-2000:]
    assert pdf.startswith(b"%PDF")
    assert "ENDLEAF_STATUS ok" in err
    assert "ENDLEAF_OVERFULL 0" in err
    path = tmp_path / "fulldoc-refs.pdf"
    path.write_bytes(pdf)
    assert 1 <= _pages(path) <= 16
    _assert_refs_resolved(_text(path))
