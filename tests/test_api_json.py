# -*- coding: utf-8 -*-
"""
    tests.test_api_json
    ~~~~~~~~~~~~~~~~~~~~~
    Check Latex POST/json compiling API.

    :copyright: (c) 2020 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import pytest
import json
import requests
from concurrent.futures import ThreadPoolExecutor
from requests_futures.sessions import FuturesSession
from .utils.pdf import snapshot_pdf

COMPIL_BIBLATEX_SPEC = {
    "compiler": "lualatex",
    "options": {"bibliography": {"command": "biber"}},
    "resources": [
        {
            "main": True,
            "content": r"""
\documentclass{article}
\usepackage[style=authoryear]{biblatex}
\addbibresource{learnlatex.bib} % file of reference info

\begin{document}
The mathematics showcase is from \autocite{Graham1995}.

Some more complex citations: \parencite{Graham1995} or
\textcite{Thomas2008} or possibly \citetitle{Graham1995}.

\autocite[56]{Thomas2008}

\autocite[See][45-48]{Graham1995}

Together \autocite{Thomas2008,Graham1995}

\printbibliography
\end{document}
            """,
        },
        {
            "path": "learnlatex.bib",
            "content": r"""
@article{Thomas2008,
  author  = {Thomas, Christine M. and Liu, Tianbiao and Hall, Michael B.
             and Darensbourg, Marcetta Y.},
  title   = {Series of Mixed Valent {Fe(II)Fe(I)} Complexes That Model the
             {H(OX)} State of [{FeFe}]Hydrogenase: Redox Properties,
             Density-Functional Theory Investigation, and Reactivity with
             Extrinsic {CO}},
  journal = {Inorg. Chem.},
  year    = {2008},
  volume  = {47},
  number  = {15},
  pages   = {7009-7024},
  doi     = {10.1021/ic800654a},
}
@book{Graham1995,
  author    = {Ronald L. Graham and Donald E. Knuth and Oren Patashnik},
  title     = {Concrete Mathematics},
  publisher = {Addison-Wesley},
  year      = {1995},
}
            """,
        },
    ],
}
SAMPLE_BIBLATEX = "biblatex_biber"


def test_biblatex_compilation(latex_on_http_api_url):
    """
    Compile a Latex document with a bibliography with biblatex.
    """
    r = requests.post(latex_on_http_api_url + "/builds/sync", json=COMPIL_BIBLATEX_SPEC)
    # import pprint

    # pprint.pprint(r.json())
    assert r.status_code == 201
    snapshot_pdf(r.content, SAMPLE_BIBLATEX)
