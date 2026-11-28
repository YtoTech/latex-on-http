# Copyright (C) 2017-2019 Yoan Tournade (upstream LaTeX-on-HTTP)
# Copyright (C) 2026 Inkmirage (Endleaf render worker modifications)
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Server-owned templates. ENDLEAF-R27.

A caller sends ``templateId`` and a body. The worker builds the document
as that template's preamble plus the body. The class and the packages in
the preamble come from the allowlist. A caller-supplied preamble is refused
before this module runs.
"""

from dataclasses import dataclass
from pathlib import Path

from colophon.limits import SHARE_ROOT

# Gate playbook order. document-shell is Markdown. The others are TeX.
# fulldoc is PDF only (ENDLEAF-R39). It is not a sold kind.
TEMPLATE_IDS = (
    "document-shell",
    "pidcircuit",
    "circuits",
    "plots",
    "chemistry",
    "gantt",
    "floorplan",
    "sysml",
    "fulldoc",
    # ENDLEAF-R59-TEMPLATES. The six named playbook kinds. Same preamble
    # as circuits; before this the gate wrapped them as a document-shell
    # tikz fence on PDF too.
    "tikzcd",
    "forest",
    "automata",
    "mindmap",
    "tikztiming",
    "bytefield",
    # ENDLEAF-R66. Stock labels: the gate writes the body from fields.
    "stocklabel",
)

# article, the base fonts, and the names in colophon-v1-preamble.tex.
# Nothing outside this set may appear in a template preamble.
ALLOWED_CLASSES = frozenset({"article"})
ALLOWED_PACKAGES = frozenset(
    {
        "fontspec",
        "xeCJK",
        "graphicx",
        "booktabs",
        "longtable",
        "hyperref",
        "tikz",
        "circuitikz",
        "siunitx",
        "pgfplots",
        "chemfig",
        "mhchem",
        "tikz-3dplot",
        "tikz-feynman",
        "tikz-cd",
        "forest",
        "tikz-timing",
        "bytefield",
        "pgfgantt",
        "tikz-dimline",
        "tikzscale",
        "endleaf-floorplan",
        "sysml-tikz",
    }
)
ALLOWED_LIBRARIES = frozenset(
    {
        "shapes",
        "arrows.meta",
        "positioning",
        "calc",
        "automata",
        "mindmap",
        "circuits.pid.ISO14617",
    }
)
ALLOWED_INPUTS = frozenset(
    {
        "colophon-v1-preamble.tex",
        "endleaf-fit.tex",
        "endleaf-credit.tex",
        "endleaf-type.tex",
        "endleaf-kinds.tex",
        "endleaf-layout.tex",
        "endleaf-pageblock.tex",
        "endleaf-label.tex",
    }
)


@dataclass(frozen=True)
class TemplateAsset:
    template_id: str
    kind: str
    example_name: str


TEMPLATES = {
    "document-shell": TemplateAsset("document-shell", "markdown", "example.md"),
    "pidcircuit": TemplateAsset("pidcircuit", "tex", "example.tex"),
    "circuits": TemplateAsset("circuits", "tex", "example.tex"),
    "plots": TemplateAsset("plots", "tex", "example.tex"),
    "chemistry": TemplateAsset("chemistry", "tex", "example.tex"),
    "gantt": TemplateAsset("gantt", "tex", "example.tex"),
    "floorplan": TemplateAsset("floorplan", "tex", "example.tex"),
    "sysml": TemplateAsset("sysml", "tex", "example.tex"),
    "fulldoc": TemplateAsset("fulldoc", "tex", "example.tex"),
    "tikzcd": TemplateAsset("tikzcd", "tex", "example.tex"),
    "forest": TemplateAsset("forest", "tex", "example.tex"),
    "automata": TemplateAsset("automata", "tex", "example.tex"),
    "mindmap": TemplateAsset("mindmap", "tex", "example.tex"),
    "tikztiming": TemplateAsset("tikztiming", "tex", "example.tex"),
    "bytefield": TemplateAsset("bytefield", "tex", "example.tex"),
    "stocklabel": TemplateAsset("stocklabel", "tex", "example.tex"),
}


def owned_root(root=None):
    if root is None:
        return Path(SHARE_ROOT) / "templates" / "owned"
    return Path(root)


# article has no a3paper option. A3 starts from a4paper; endleaf-page.tex
# resizes it.
_PAPER = {"a4": "a4paper", "letter": "letterpaper", "a3": "a4paper"}
PAPER_NAME = {"a4": "A4", "letter": "Letter", "a3": "A3"}


PAGE_HOOK = "\\AddToHook{class/article/after}{\\input{endleaf-page.tex}}"


def paper_option(page_size="a4", orientation=None):
    """ENDLEAF-R56-SIZES. Class paper option. ``ValueError`` if unknown.

    Orientation is not a class option: article's ``landscape`` keeps the
    345 pt prose line. endleaf-page.tex turns the page and widens the line.
    """
    paper = _PAPER.get(page_size)
    if paper is None:
        raise ValueError("pageSize")
    if orientation not in (None, "portrait", "landscape"):
        raise ValueError("orientation")
    return paper


def page_macros(page_size="a4", orientation=None):
    """Lines before \\documentclass. endleaf-page.tex and endleaf-fit read them.

    ``\\EndleafPaper`` names the page. ``\\EndleafOrientation`` is defined
    only when the job named one; endleaf-fit then keeps that orientation
    instead of choosing (ENDLEAF-R56-FIT).
    """
    paper_option(page_size, orientation)
    lines = [f"\\def\\EndleafPaper{{{PAPER_NAME[page_size]}}}"]
    if orientation is not None:
        lines.append(f"\\def\\EndleafOrientation{{{orientation}}}")
    lines.append(PAGE_HOOK)
    return "\n".join(lines) + "\n"


# DK-11201 page and printable margins. parse_job always sets labelSize;
# this default is for the reference example only.
DEFAULT_LABEL_SIZE = (89.8, 29.0, 2.95, 1.55)


def label_macros(label_size):
    """ENDLEAF-R66-SIZE. Lines before \\documentclass; endleaf-label.tex reads them."""
    width, height, mx, my = label_size
    names = (("W", width), ("H", height), ("MX", mx), ("MY", my))
    return "".join(f"\\def\\EndleafLabel{name}{{{value:.2f}}}\n" for name, value in names)


def compose(template_id, lane, body, root=None, page_size="a4", orientation=None, label_size=None):
    """Preamble plus body. ``root`` defaults to the image share directory."""
    return compose_with_body_line(
        template_id, lane, body, root, page_size=page_size, orientation=orientation, label_size=label_size
    )[0]


def compose_with_body_line(
    template_id, lane, body, root=None, page_size="a4", orientation=None, label_size=None
):
    """ENDLEAF-R58-BODYLINE. ``(job.tex text, body start line)``.

    The start line is the 1-based line of job.tex that holds the body's first
    line, so a TeX error at job.tex line N inside the body is body line
    ``N - start + 1``.
    """
    path = owned_root(root) / template_id / "preamble.tex"
    text = path.read_text(encoding="utf-8")
    # fulldoc's locked preamble has no lane stamp. Other templates have one.
    if (
        text.count("__LANE__") > 1
        or text.count("__BODY__") != 1
        or text.count("__PAPER__") != 1
    ):
        raise ValueError("preamble")
    paper = paper_option(page_size, orientation)
    if template_id == "stocklabel":
        # ENDLEAF-R66-SIZE. The label page, not endleaf-page.tex.
        if label_size is None:
            label_size = DEFAULT_LABEL_SIZE
        text = label_macros(label_size) + text.replace("__PAPER__", paper, 1)
    else:
        text = page_macros(page_size, orientation) + text.replace("__PAPER__", paper, 1)
    if "__LANE__" in text:
        text = text.replace("__LANE__", lane, 1)
    start = text.count("\n", 0, text.index("__BODY__")) + 1
    return text.replace("__BODY__", body, 1), start


def example_body(template_id, root=None):
    asset = TEMPLATES[template_id]
    path = owned_root(root) / template_id / asset.example_name
    return path.read_text(encoding="utf-8")
