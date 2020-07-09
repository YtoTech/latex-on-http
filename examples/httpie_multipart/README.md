# Compile a project with multiple files using multipart/form-data

<!-- TODO WIP -->

```bash
http POST https://latex.ytotech.com/builds/sync \
    compiler=pdflatex \
    resources:='[{"main": "true", "content": "\\\documentclass{article} \\n \\\begin{document}\\n Hello World\\n \\\end{document}"}]' \
    > hello_world.pdf
```

<!-- http --download -f -v POST https://latex.ytotech.com/builds/sync \
    file1@sample.tex \
    compiler=xelatex \
    resources='[{"main": "true", "multipart": "file1"}]' -->
