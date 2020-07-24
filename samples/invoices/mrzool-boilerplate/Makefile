output-local-pandoc-pdf:
	pandoc details.yml --template=template-pandoc.tex -o output-pandoc.pdf --pdf-engine=xelatex

output-local-pandoc-tex:
	pandoc details.yml --template=template-pandoc.tex -o output-pandoc.tex

# xelatex template-raw.tex -jobname=output-xelatex -interaction=nonstopmode
output-local-pdflatex-pdf:
	latexmk -c
	latexmk -pdf -interaction=nonstopmode --xelatex -jobname=output-xelatex template-raw.tex

output-cloud-latexonhttp-pdf:
	curl -v -X POST https://latex.ytotech.com/builds/sync \
		-F "template-raw.tex=@template-raw.tex" \
		-F "compiler=xelatex" \
		-o output-xelatex.pdf
