# Copyright (C) 2026 Inkmirage (Endleaf render worker modifications)
# SPDX-License-Identifier: AGPL-3.0-or-later
"""ENDLEAF-R81. The warn-only PDF layout checker and its geometry logs.

Most cases build a tiny PDF by hand (base-14 Helvetica, plain content streams), so they
need neither TeX Live nor podman. The cases that compile with XeLaTeX skip when it is missing.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("pdfminer")
pytest.importorskip("shapely")
pytest.importorskip("scipy")

from colophon import pdf_layout_check as checker  # noqa: E402
from colophon.layout_map import layout_map, page_blocks, page_marks  # noqa: E402
from colophon.layout_warn import shell_pages  # noqa: E402
from colophon.pdf_layout_check import (
    CODES,
    check_pdf,
    parse_pdf_layout,
    pdf_layout_line,
)  # noqa: E402

_TEX = Path(__file__).resolve().parents[2] / "colophon/share/tex/latex/colophon-v1"
_NEEDS_TEX = pytest.mark.skipif(
    shutil.which("xelatex") is None, reason="xelatex is not installed"
)

# TeX text block of a US Letter page: left 72 bp, top 72 bp, 468 bp wide, 648 bp tall (TeX pt).
_BLOCK = (72.27, 72.27, 468.0 * 72.27 / 72, 648.0 * 72.27 / 72)


def pdf(pages, size=(612, 792)):
    """Bytes of a PDF whose pages are the given content streams (font /F1 is Helvetica)."""
    objects = {}
    count = len(pages)
    objects[1] = "<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{3 + 2 * n} 0 R" for n in range(count))
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {count} >>"
    for n, content in enumerate(pages):
        page_id, stream_id = 3 + 2 * n, 4 + 2 * n
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {size[0]} {size[1]}] /Contents {stream_id} 0 R "
            f"/Resources << /Font << /F1 {3 + 2 * count} 0 R >> >> >>"
        )
        objects[stream_id] = (
            f"<< /Length {len(content)} >>\nstream\n{content}\nendstream"
        )
    objects[3 + 2 * count] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    out = b"%PDF-1.4\n"
    offsets = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += f"{number} 0 obj\n{objects[number]}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for number in sorted(objects):
        out += f"{offsets[number]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def text(x, y, string, size=10):
    return f"BT /F1 {size} Tf {x} {y} Td ({string}) Tj ET\n"


def body(lines=20, start=700, left=72):
    """A page of ordinary prose lines inside the block."""
    return "".join(
        text(left, start - 14 * n, "an ordinary line of body text sits here")
        for n in range(lines)
    )


def codes_of(result):
    return [item["code"] for item in result.items]


def run(pages, template="fulldoc", blocks=None, **kwargs):
    return check_pdf(
        pdf(pages),
        template_id=template,
        blocks={1: _BLOCK} if blocks is None else blocks,
        **kwargs,
    )


# -- the eight codes, each from a constructed page -----------------------------------------------------


def test_clean_page_has_no_finding():
    result = run([body() + text(400, 40, "1")])
    assert result.items == []


def test_margin_escape_fires_past_the_block_and_skips_a_page_without_a_block():
    page = text(72, 700, "short") + text(
        400, 680, "this line runs far past the right edge of the block"
    )
    result = run([page])
    (item,) = result.items
    assert item["code"] == "pdf_margin_escape" and item["page"] == 1
    assert (
        item["message"].startswith("pg1: text runs ")
        and " mm past the text block: 'this line runs" in item["message"]
    )
    assert item["overMm"] > 0 and len(item["box"]) == 4 and item["packages"] == ["pdf"]
    # No block line for the page: the margin check is skipped and counted.
    skipped = run([page], blocks={})
    assert skipped.items == [] and any("noblock" in line for line in skipped.log_lines)


def test_caption_overlap_fires_for_a_filled_drawing_over_the_caption():
    page = (
        body(10)
        + text(72, 400, "Figure 1: the pump curve")
        + "0.5 g 60 395 200 40 re f\n"
    )
    result = run([page])
    assert "pdf_caption_overlap" in codes_of(result)
    item = next(i for i in result.items if i["code"] == "pdf_caption_overlap")
    assert (
        item["message"]
        == "pg1: a drawing overlaps the caption 'Figure 1: the pump curve'"
    )


def test_label_on_stroke_fires_and_a_white_fill_after_the_stroke_hides_it():
    stroke = "0.5 w 60 604 m 300 604 l S\n"
    label = text(100, 600, "Pressure")
    result = run([stroke + label])
    assert [i["code"] for i in result.items] == ["pdf_label_on_stroke"]
    assert result.items[0]["message"] == "pg1: label 'Pressure' sits on a stroked line"
    white = "1 g 95 595 60 16 re f 0 g\n"
    assert run([stroke + white + label]).items == []


def test_text_escapes_node_fires_when_the_word_is_half_outside_a_closed_outline():
    node = "0.5 w 100 600 80 30 re S\n"
    result = run([node + text(160, 610, "Overflow")])
    assert "pdf_text_escapes_node" in codes_of(result)
    message = next(
        i["message"] for i in result.items if i["code"] == "pdf_text_escapes_node"
    )
    assert message == "pg1: label 'Overflow' runs out of its node"
    assert "pdf_text_escapes_node" not in codes_of(
        run([node + text(105, 610, "Inside")])
    )


def test_text_overlap_fires_for_words_printed_on_each_other_and_not_for_extensible_pieces():
    result = run([text(100, 600, "Alpha") + text(112, 600, "Beta")])
    (item,) = result.items
    assert (
        item["code"] == "pdf_text_overlap"
        and item["message"] == "pg1: 'Alpha' overlaps 'Beta'"
    )
    arrows = text(100, 600, "---") + text(103, 600, "---")
    assert "pdf_text_overlap" not in codes_of(run([arrows]))


def test_label_gutter_fires_on_sysml_pages_only():
    figure = "0.5 w 80 580 200 60 re S\n"
    labels = text(100, 600, "Alpha", 10) + text(100 + 25.7 + 0.4, 600, "Beta", 8)
    result = run([figure + labels], template="sysml")
    assert "pdf_label_gutter" in codes_of(result)
    item = next(i for i in result.items if i["code"] == "pdf_label_gutter")
    assert item["message"].startswith("pg1: labels 'Alpha' and 'Beta' are ") and item[
        "message"
    ].endswith(" mm apart")
    assert "pdf_label_gutter" not in codes_of(run([figure + labels], template="plots"))


def test_stray_source_fires_for_a_fence_and_a_control_word_and_respects_scope_and_listings():
    page = (
        body(5)
        + text(72, 500, "```python")
        + text(72, 440, "\\\\begin{figure} printed")
    )
    result = run([page], template="document-shell")
    tokens = [i["message"] for i in result.items if i["code"] == "pdf_stray_source"]
    assert any("raw source printed as text: '‘‘‘python'" in m for m in tokens)
    assert any("\\\\begin{figure}" in m or "\\begin{figure}" in m for m in tokens)
    # OD-PDF-7: only document-shell and fulldoc are checked.
    assert "pdf_stray_source" not in codes_of(run([page], template="plots"))


def test_empty_page_fires_inside_a_document_but_not_on_a_drawn_or_full_page():
    pages = [text(72, 700, "two") + text(150, 700, "words"), body(), body()]
    result = run(pages, blocks={1: _BLOCK, 2: _BLOCK, 3: _BLOCK})
    (item,) = [i for i in result.items if i["code"] == "pdf_empty_page"]
    assert (
        item["page"] == 1 and item["message"] == "pg1: page has 2 words and no drawing"
    )
    drawn = ["0.5 w 100 500 m 300 500 l S\n" + text(72, 700, "two words"), body()]
    assert "pdf_empty_page" not in codes_of(run(drawn, blocks={1: _BLOCK, 2: _BLOCK}))
    # The last page is flagged only with no words at all.
    last = [body(), text(72, 700, "two words")]
    assert "pdf_empty_page" not in codes_of(run(last, blocks={1: _BLOCK, 2: _BLOCK}))
    assert codes_of(run([body(), ""], blocks={1: _BLOCK, 2: _BLOCK})) == [
        "pdf_empty_page"
    ]


def test_all_eight_codes_exist_and_none_refuses():
    assert len(CODES) == 8
    assert set(checker.REFUSE_ENABLED) == set(CODES) and not any(
        checker.REFUSE_ENABLED.values()
    )
    assert checker.MAX_FINDINGS == 10 and checker.SKIP_CODE == "pdf_check_skipped"


# -- warn-only, budget, dedupe --------------------------------------------------------------------------


def test_a_finding_is_a_warning_item_and_never_fails_the_check():
    result = run(
        [text(400, 680, "this line runs far past the right edge of the block")]
    )
    assert result.items and all(
        item["packages"] == ["pdf"] and item["code"] in CODES for item in result.items
    )
    # Garbage in is a skip note, not an exception.
    garbage = check_pdf(b"not a pdf", template_id="fulldoc")
    assert [i["code"] for i in garbage.items] == ["pdf_check_skipped"]
    assert garbage.items[0]["message"].startswith("pdf layout check stopped")


def test_job_record_carries_a_pdf_warning_and_the_render_stays_ok(
    config, switch_path, monitor, auth
):
    from colophon.killswitch import KillSwitch
    from colophon.runner import Outcome, Supervisor
    from colophon.worker import create_app
    from tests.colophon.conftest import valid_body

    item = run(
        [text(400, 680, "this line runs far past the right edge of the block")]
    ).items[0]
    line = pdf_layout_line([item])
    (parsed,) = parse_pdf_layout("noise\n" + line + "\n")
    assert parsed == item
    outcome = Outcome(
        kind="ok",
        body=b"%PDF-1.4",
        content_type="application/pdf",
        wall_sec=0.5,
        layout_warnings=(parsed,),
    )

    class _Runner:
        def __call__(self, job, name, abort_event):
            return outcome

    app = create_app(
        config, KillSwitch(switch_path), monitor, Supervisor(_Runner(), 10)
    )
    response = app.test_client().post("/v1/jobs", json=valid_body(), headers=auth)
    assert response.status_code == 200 and response.headers["X-Endleaf-Result"] == "ok"
    record = json.loads(response.headers["X-Endleaf-Job"])
    assert record["result"] == "ok"
    assert [w["code"] for w in record["warnings"]] == ["pdf_margin_escape"]
    assert record["warnings"][0]["page"] == 1


def test_stderr_line_round_trip_drops_foreign_items():
    good = {
        "code": "pdf_empty_page",
        "packages": ["pdf"],
        "message": "pg2: page has 0 words and no drawing",
        "page": 2,
    }
    bad = [
        {"code": "other", "packages": ["pdf"], "message": "x"},
        {"code": "pdf_empty_page", "packages": ["tikz"], "message": "x"},
    ]
    assert parse_pdf_layout(pdf_layout_line([good, *bad])) == [good]
    assert (
        parse_pdf_layout("ENDLEAF_PDFLAYOUT not json") == []
        and parse_pdf_layout(None) == []
    )


def test_budget_overrun_keeps_findings_and_adds_one_skip_note(monkeypatch):
    faulty = text(400, 680, "this line runs far past the right edge of the block")
    state = {"t": 0.0}
    real = checker._check_text_overlap

    def slow(page):
        if page.number == 2:
            state["t"] = 10.0  # page 2 overruns its cap
        return real(page)

    monkeypatch.setattr(checker, "_check_text_overlap", slow)
    result = check_pdf(
        pdf([faulty, body()]),
        template_id="fulldoc",
        blocks={1: _BLOCK, 2: _BLOCK},
        clock=lambda: state["t"],
    )
    assert [i["code"] for i in result.items] == [
        "pdf_margin_escape",
        "pdf_check_skipped",
    ]
    note = result.items[1]
    assert (
        note["page"] == 1
        and "time budget" in note["message"]
        and "after pg1" in note["message"]
    )
    assert note["message"].endswith("findings so far are kept")
    # A clock that is already late checks nothing: the note says before pg1.
    late = check_pdf(
        pdf([body()]), template_id="fulldoc", clock=iter([0.0] + [99.0] * 50).__next__
    )
    assert [i["code"] for i in late.items] == ["pdf_check_skipped"]
    assert "before pg1" in late.items[0]["message"]


def test_findings_are_capped_at_ten_and_the_rest_counted():
    page = "".join(
        text(400, 770 - 30 * n, "this line runs far past the right edge of the block")
        for n in range(14)
    )
    result = run([page])
    listed = [i for i in result.items if i["code"] == "pdf_margin_escape"]
    # Lines 30 pt apart are farther than one line pitch, so they stay separate findings.
    assert len(listed) == 10
    more = [i for i in result.items if i["code"] == "pdf_more_findings"]
    assert more and more[0]["count"] == 4 and more[0]["packages"] == ["pdf"]


def test_dedupe_merges_nearby_hits_and_drops_margin_escape_on_a_page_tex_names():
    page = "".join(
        text(400, 700 - 12 * n, "this line runs far past the right edge of the block")
        for n in range(3)
    )
    (item,) = run([page]).items
    assert item["regionCount"] == 3
    # OD-PDF-4: TeX already names page 1 (an overfull row), so the margin escape is dropped.
    assert run([page], tex_pages={1}).items == []


def test_placement_uses_marks_and_fence_pages():
    marks = [
        ["p1", "s", 1, 700.0, "p"],
        ["p1", "e", 1, 600.0, "p"],
        ["p2", "s", 1, 590.0, "p"],
        ["p2", "e", 2, 300.0, "p"],
    ]
    assert checker.part_for(marks, 1, 650.0) == "p1"
    assert checker.part_for(marks, 1, 100.0) == "p2"
    assert checker.part_for(marks, 2, 500.0) == "p2"
    assert checker.part_for(marks, 3, 500.0) is None
    result = run(
        [text(400, 680, "this line runs far past the right edge of the block")],
        marks=[["p1", "s", 1, 700.0, "p"], ["p1", "e", 1, 100.0, "p"]],
        shell_pages={3: 1},
    )
    assert result.items[0]["partId"] == "p1" and result.items[0]["fenceNumber"] == 3


def test_off_page_glyphs_are_dropped_and_counted_not_reported():
    page = body(5) + text(900, 400, "hidden") + text(-300, 400, "gone")
    result = run([page])
    assert result.items == []
    assert any("offpage page=1 glyphs=10" in line for line in result.log_lines)


def test_docstrum_guard_logs_and_adds_no_warning():
    # Words set 3 em apart: the Otsu word threshold falls outside 0.03 to 0.17 em.
    page = "".join(
        text(72, 700 - 14 * n, "aaaa bbbb cccc dddd eeee ffff gggg") for n in range(8)
    )
    result = run([page])
    assert result.items == []


# -- no PyMuPDF -----------------------------------------------------------------------------------------


def test_module_never_loads_pymupdf():
    source = (Path(checker.__file__)).read_text(encoding="utf-8")
    assert "fitz" not in source and "pymupdf" not in source.lower()
    assert checker.IMPORTS_AGPL_PDF_LIBRARY is False
    code = (
        "import sys\n"
        "from colophon.pdf_layout_check import check_pdf\n"
        "r = check_pdf(%r, template_id='fulldoc')\n"
        "assert 'fitz' not in sys.modules and 'pymupdf' not in sys.modules\n"
        "assert not any(m.startswith(('fitz', 'pymupdf')) for m in sys.modules)\n"
    ) % pdf([body()])
    root = Path(__file__).resolve().parents[2]
    done = subprocess.run(
        [sys.executable, "-c", code], cwd=root, capture_output=True, text=True
    )
    assert done.returncode == 0, done.stderr[-1500:]


def test_libraries_are_the_permissive_set_in_pyproject():
    text_ = (
        (Path(__file__).resolve().parents[2] / "pyproject.toml")
        .read_text(encoding="utf-8")
        .lower()
    )
    for name in ("pdfminer", "shapely", "scipy"):
        assert name in text_
    assert "pymupdf" not in text_ and "fitz" not in text_


# -- geometry logs: GEOM, page blocks and the TeX side ---------------------------------------------------


def test_geom_with_the_left_margin_and_the_old_four_field_line_both_parse():
    new = layout_map(
        "ENDLEAF_GEOM 845.04684pt 718.77686pt 598.0pt 345.0pt 133.26999pt\nENDLEAF_MARK p1 s 1 449570 portrait\n"
    )
    assert new["geom"] == {
        "paper": 845.0,
        "top": 718.8,
        "textHeight": 598.0,
        "line": 345.0,
        "left": 133.3,
    }
    old = layout_map(
        "ENDLEAF_GEOM 845.04684pt 718.77686pt 598.0pt 345.0pt\nENDLEAF_MARK p1 s 1 449570 portrait\n"
    )
    assert old["geom"] == {
        "paper": 845.0,
        "top": 718.8,
        "textHeight": 598.0,
        "line": 345.0,
    }
    assert page_marks("ENDLEAF_MARK p1 s 1 4195\n304 portrait\n")[0][:3] == [
        "p1",
        "s",
        1,
    ]


def test_page_block_lines_are_read_even_when_tex_wraps_them():
    log = (
        "ENDLEAF_PAGEBLOCK 1 134.26999pt 125.26999pt 345.0pt 550.0pt\n"
        "ENDLEAF_PAGEBLOCK 2 56.9055pt 56.9055pt 728.0pt 478.0pt\n"
        "ENDLEAF_PAGEBLOCK 3 134.26999pt 125.2\n6999pt 345.0pt 550.0pt\n"
    )
    assert page_blocks(log) == {
        1: (134.26999, 125.26999, 345.0, 550.0),
        2: (56.9055, 56.9055, 728.0, 478.0),
        3: (134.26999, 125.26999, 345.0, 550.0),
    }
    assert page_blocks("") == {} and page_blocks(None) == {}
    assert shell_pages(
        "ENDLEAF_SHELLPAGE 2 5 landscape\nENDLEAF_SHELLPAGE 2 6 landscape\n"
    ) == {2: 5}


def test_every_template_inputs_the_page_block_file():
    from colophon.templates import ALLOWED_INPUTS, TEMPLATES

    assert "endleaf-pageblock.tex" in ALLOWED_INPUTS
    shared = (_TEX / "colophon-v1-preamble.tex").read_text(encoding="utf-8")
    assert "\\input{endleaf-pageblock.tex}" in shared
    owned = _TEX.parents[2] / "templates/owned"
    for template_id in TEMPLATES:
        preamble = (owned / template_id / "preamble.tex").read_text(encoding="utf-8")
        direct = "\\input{endleaf-pageblock.tex}" in preamble
        shared_input = "\\input{colophon-v1-preamble.tex}" in preamble
        assert direct or shared_input, template_id
    for lane in ("InstruMeasure", "Weft", "Investor"):
        template = _TEX.parents[2] / "templates" / lane / "pandoc.latex"
        if template.exists():
            assert "\\input{colophon-v1-preamble.tex}" in template.read_text(
                encoding="utf-8"
            )
    geom = (_TEX / "endleaf-layout.tex").read_text(encoding="utf-8")
    assert "\\the\\dimexpr1in+\\hoffset+\\oddsidemargin\\relax}%" in geom


@_NEEDS_TEX
def test_xelatex_logs_one_page_block_per_shipped_page_and_the_checker_reads_the_pdf(
    tmp_path, monkeypatch
):
    (tmp_path / "a.tex").write_text(
        "\\documentclass{article}\n\\usepackage{tikz}\n\\input{endleaf-pageblock.tex}\n\\begin{document}\n"
        "Hello world, a line of text.\n\n\\begin{tikzpicture}\\draw (0,0) rectangle (3,1);"
        "\\node at (1.5,0.5) {Label};\\draw (0,0.5) -- (3,0.5);\\end{tikzpicture}\n\\newpage\nSecond page.\n\\end{document}\n",
        encoding="utf-8",
    )
    env = {
        "TEXINPUTS": f"{_TEX}//:",
        "PATH": "/usr/bin:/bin:" + str(Path(shutil.which("xelatex")).parent),
    }
    done = subprocess.run(
        ["xelatex", "-interaction=nonstopmode", "a.tex"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        timeout=120,
    )
    log = (tmp_path / "a.log").read_text(encoding="utf-8", errors="replace")
    assert (tmp_path / "a.pdf").exists(), done.stdout[-1500:]
    blocks = page_blocks(log)
    assert sorted(blocks) == [1, 2] and blocks[1][2] == pytest.approx(345.0)
    result = check_pdf(
        (tmp_path / "a.pdf").read_bytes(), template_id="fulldoc", blocks=blocks
    )
    assert "pdf_label_on_stroke" in codes_of(result)
    assert not [i for i in result.items if i["code"] == "pdf_check_skipped"]


def test_sandbox_glue_sends_one_stderr_line_and_never_raises(monkeypatch, capsys):
    from types import SimpleNamespace

    from colophon import sandbox_render

    job = SimpleNamespace(template_id="fulldoc")
    faulty = pdf(
        [text(400, 680, "this line runs far past the right edge of the block")]
    )
    blocks = "ENDLEAF_PAGEBLOCK 1 72.27pt 72.27pt 468.0pt 648.0pt\n"
    sandbox_render._pdf_layout_check(job, faulty, blocks, None, 0)
    err = capsys.readouterr().err
    items = parse_pdf_layout(err)
    assert [i["code"] for i in items] == ["pdf_margin_escape"]
    # OD-PDF-4: TeX names page 1 with an overfull row, so the margin escape is dropped.
    named = (
        blocks
        + "Overfull \\hbox (30.0pt too wide) in paragraph at lines 3--4\n []\n\n[1]\n"
    )
    sandbox_render._pdf_layout_check(job, faulty, named, 1, 10)
    assert parse_pdf_layout(capsys.readouterr().err) == []

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(checker, "check_pdf", boom)
    sandbox_render._pdf_layout_check(
        job, faulty, blocks, None, 0
    )  # warn-only: no exception
    assert "ENDLEAF_PDFLOG" in capsys.readouterr().err


def test_preload_exercises_shapely_polygons(monkeypatch):
    import shapely

    from colophon import pdf_layout_check as plc

    calls = []
    real = shapely.polygons
    monkeypatch.setattr(
        shapely, "polygons", lambda *a, **k: calls.append(a) or real(*a, **k)
    )
    plc._preload()
    assert calls


def test_preload_raises_without_shapely_polygons(monkeypatch):
    import shapely

    from colophon import pdf_layout_check as plc

    monkeypatch.delattr(shapely, "polygons")
    with pytest.raises(AttributeError):
        plc._preload()
    with pytest.raises(AttributeError):
        plc.check_pdf(b"%PDF-1.4")


def test_sandbox_main_preloads(monkeypatch):
    from colophon import pdf_layout_check as plc
    from colophon import sandbox_render as sr

    order = []
    monkeypatch.setattr(plc, "_preload", lambda: order.append("preload"))
    monkeypatch.setattr(sr, "render_to_stdout", lambda raw: order.append("render") or 0)
    monkeypatch.setattr(
        sys, "stdin", type("S", (), {"buffer": __import__("io").BytesIO(b"{}")})()
    )
    with pytest.raises(SystemExit):
        sr.main()
    assert order == ["preload", "render"]
