# Compile a LaTeX doc from a browser using `fetch`

```js
async function compileLaTeXSimpleDoc (latexDoc) {
    const response = await fetch('https://latex.ytotech.com/builds/sync', {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json'
        },
        responseType: 'blob',
        body: JSON.stringify({
            compiler: 'pdflatex',
			resources: [
				{
					main: true,
					content: latexDoc
				}
			]
        }),
    });
    console.log(response);
      if (!response.ok) {
        const errorText = await response.text();
        // To something with the compilation error.
        console.error(errorText);
        return;
      }
    try {
        const pdfBlob = await response.blob();
        console.log('The PDF blob', pdfBlob);
        // Do something with the PDF blob:
        //  - make the browser download it;
        //  - display it in DOM, natively or with a lib (like pdf.js).
        // https://cdnjs.com/libraries/pdf.js

        // Eg. save file with https://www.npmjs.com/package/file-saver lib.
        // saveAs(blob, 'hello.pdf');
    } catch(e) {
        console.error(`Error LaTeX-on-HTTP response handling: ${e}`);
    }
}

compileLaTeXSimpleDoc(`\documentclass{article}
\usepackage{graphicx}
\begin{document}
Hello LaTeX. \\
\end{document}`);
```

See `save-as-file.html` for a minimalist HTML page integrating the service to compile some LaTeX and download the PDF.
