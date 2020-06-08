#!/bin/bash

# Bibtex workflow.
# --> bibtex (default)
# curl -v -X POST https://latex.ytotech.com/builds/sync \
curl -v -X POST http://localhost:8080/builds/sync \
    -F "bibtex_sample.tex=@bibtex_sample.tex" \
    -F "learnlatex.bib=@learnlatex.bib" \
    -F "compiler=pdflatex" \
    -o bibtex_sample.pdf

# Natlib workflow.
# --> Xelatex
# curl -v -X POST https://latex.ytotech.com/builds/sync \
curl -v -X POST http://localhost:8080/builds/sync \
    -F "natlib_sample.tex=@natlib_sample.tex" \
    -F "learnlatex.bib=@learnlatex.bib" \
    -F "compiler=xelatex" \
    -o natlib_sample.pdf

# Biblatex workflow.
# --> biber
# curl -v -X POST https://latex.ytotech.com/builds/sync \
curl -v -X POST http://localhost:8080/builds/sync \
    -F "biblatex_sample.tex=@biblatex_sample.tex" \
    -F "learnlatex.bib=@learnlatex.bib" \
    -F "compiler=pdflatex" \
    -F "options.bibliography.command=biber" \
    -o biblatex_sample.pdf
