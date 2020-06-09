#!/bin/bash

# curl -v -X POST http://localhost:8080/builds/sync \

# Bibtex workflow.
# --> pdflatex with bibtex (default)
curl -v -X POST https://latex.ytotech.com/builds/sync \
    -F "bibtex_sample.tex=@bibtex_sample.tex" \
    -F "learnlatex.bib=@learnlatex.bib" \
    -F "compiler=pdflatex" \
    -F "options.bibliography.command=bibtex" \
    -o bibtex_sample.pdf

# Natlib workflow.
# --> pdflatex
curl -v -X POST https://latex.ytotech.com/builds/sync \
    -F "natlib_sample.tex=@natlib_sample.tex" \
    -F "learnlatex.bib=@learnlatex.bib" \
    -F "compiler=pdflatex" \
    -o natlib_sample.pdf

# Biblatex workflow.
# --> biber
curl -v -X POST https://latex.ytotech.com/builds/sync \
    -F "biblatex_sample.tex=@biblatex_sample.tex" \
    -F "learnlatex.bib=@learnlatex.bib" \
    -F "compiler=pdflatex" \
    -F "options.bibliography.command=biber" \
    -o biblatex_sample.pdf
