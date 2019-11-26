#!/bin/bash

# Requires https://github.com/jakubroztocil/httpie installed

http -f -v POST http://localhost:8080/builds/sync \
    file1@sample.tex \
    compiler=pdflatex \
    resources='[{"main": "true", "multipart": "file1"}]'
    # > hello_world.pdf

# https://github.com/jakubroztocil/httpie#file-upload-forms
# http -f POST http://localhost:8080 /jobs name='John Smith' cv@~/Documents/cv.pdf
