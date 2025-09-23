#!/bin/bash

# TODO Create example with multiple files (eg. image file).

# Or https://latex.ytotech.com/builds/sync
curl -v -X POST http://localhost:8080/builds/sync \
    -F "sample.tex=@sample.tex" \
    -F "compiler=xelatex" \
    -F "options.compiler.halt_on_error=false" \
    -F "options.compiler.silent=true" \
    -F "options.response.log_files_on_failure=false" \
    -o sample.pdf
