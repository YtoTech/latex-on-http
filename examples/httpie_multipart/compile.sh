#!/bin/bash

# Requires https://github.com/jakubroztocil/httpie installed

# Specify a compiler, the resource spec and the file to upload.
http --download -f -v POST http://localhost:8080/builds/sync \
    file1@sample.tex \
    compiler=xelatex \
    resources='[{"main": "true", "multipart": "file1"}]'

# https://github.com/jakubroztocil/httpie#file-upload-forms
# http -f POST http://localhost:8080 /jobs name='John Smith' cv@~/Documents/cv.pdf
