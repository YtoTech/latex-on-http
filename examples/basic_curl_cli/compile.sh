#!/bin/bash

# TODO Create example with multiple files (eg. image file).

curl -v -X POST https://latex.ytotech.com/builds/sync \
    -F "sample.tex=@sample.tex" \
    -F "compiler=xelatex" \
    -o sample.pdf
