#!/bin/bash

# Requires https://github.com/jakubroztocil/httpie installed

# Specify a compiler, the resource spec and the file to upload.
http --download --multipart --output sample.pdf -f -v POST https://latex.ytotech.com/builds/sync \
    file1@sample.tex \
    compiler=xelatex \
    resources='[{"main": true, "multipart": "file1"}]'
