# Compile a project with multiple files using multipart/form-data

```bash
http POST https://latex.ytotech.com/builds/sync \
    compiler=pdflatex \
    resources:='[{"main": "true", "content": "\\\documentclass{article} \\n \\\begin{document}\\n Hello World\\n \\\end{document}"}]' \
    > hello_world.pdf
```
