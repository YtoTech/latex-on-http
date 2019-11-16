#!/bin/bash

main_document_name="Dossier_Eleve.tex"
# -w is important to get a single line result.
main_document_base64="$(cat $main_document_name | base64 -w 0)"

json_payload='{
        "compiler": "pdflatex",
        "resources": [
            {
                "main": true,
                "file": "'"$main_document_base64"'"
            }
        ]
    }'
echo $json_payload > payload.json

curl -v -X POST https://latex.ytotech.com/builds/sync \
    -H "Content-Type:application/json" \
    -d "$json_payload" \
> Dossier_Eleve.pdf
