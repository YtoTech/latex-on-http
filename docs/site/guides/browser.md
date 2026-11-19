---
title: Calling from a browser (JSON API)
layout: base.njk
active: "/guides/browser/"
---

{% import "macros.njk" as macros %}

<div class="prose">

Browsers can call the API directly: the service allows cross-origin requests
(CORS), so your web application can compile documents without relaying them
through your own backend. This guide uses the JSON API with `fetch`, and shows
how to display the returned PDF **in the page**.

## Complete example: compile and display the PDF

The response of a successful build is the raw PDF (`Content-Type:
application/pdf`). Read it as a `Blob`, create an object URL, and assign it to
an `<iframe>` (or `<embed>`/`<object>`): the browser renders the PDF with its
native viewer.

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Compile and display a LaTeX doc</title>
</head>
<body>
  <textarea id="latexdoc" rows="10" cols="60">\documentclass{article}
\usepackage{graphicx}
\begin{document}
Hello LaTeX. \\
\includegraphics[width=4cm]{logo.png}
\end{document}</textarea>

  <button id="compileBtn">Compile</button>

  <div id="error" hidden>
    <h2>Compilation error</h2>
    <pre id="error-logs"></pre>
  </div>

  <!-- The PDF is displayed here. -->
  <iframe id="pdf-view" title="Compiled PDF" hidden></iframe>
  <a id="pdf-download" download="document.pdf" hidden>Download the PDF</a>

  <script>
    const API_URL = "https://latex.ytotech.com/builds/sync";

    // Reusable helper: create an object URL, display and offer the PDF.
    function displayPdfBlob(pdfBlob, fileName) {
      const pdfUrl = URL.createObjectURL(pdfBlob);
      const viewer = document.getElementById("pdf-view");
      const download = document.getElementById("pdf-download");
      viewer.src = pdfUrl;
      viewer.hidden = false;
      download.href = pdfUrl;
      download.hidden = false;
      // Revoke the previous object URL to free memory.
      viewer.addEventListener("load", () => URL.revokeObjectURL(pdfUrl), {
        once: true,
      });
    }

    async function compileLaTeX(latexDoc) {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          compiler: "pdflatex",
          resources: [
            {
              main: true,
              content: latexDoc,
            },
            {
              path: "logo.png",
              url: "https://www.ytotech.com/images/ytotech_logo.png",
            },
          ],
        }),
      });

      if (!response.ok) {
        // Compilation error: the payload is JSON with the error and logs.
        const error = await response.json();
        document.getElementById("error").hidden = false;
        document.getElementById("error-logs").textContent =
          error.error + "\n\n" + (error.logs || "");
        return;
      }

      document.getElementById("error").hidden = true;
      const pdfBlob = await response.blob();
      displayPdfBlob(pdfBlob, "document.pdf");
    }

    document.getElementById("compileBtn").addEventListener("click", () => {
      compileLaTeX(document.getElementById("latexdoc").value);
    });
  </script>
</body>
</html>
```

## Alternatives for showing the PDF

- **`<iframe src>` / `<embed src>` / `<object data>`** with the object URL:
  the simplest approach, rendered by the browser's native PDF viewer (as
  above).
- **[PDF.js](https://mozilla.github.io/pdf.js/)** if you need a consistent
  viewer across browsers, page-level rendering to `<canvas>`, or to overlay
  interactive elements.
- **Save as file** with an `<a download>` link pointing to the object URL
  (shown above), or the
  [`file-saver`](https://www.npmjs.com/package/file-saver) library.

## Notes and gotchas

- **CORS.** The service sends `Access-Control-Allow-Origin: *`, so requests
  from any origin are allowed — including from `localhost` during development.
- **Response is binary, not JSON.** A successful response body is the PDF
  itself: read it with `response.blob()`. Only error responses are JSON —
  check `response.ok` *before* calling `response.json()`.
- **Object URL lifecycle.** Object URLs are not garbage-collected while
  referenced; revoke them (as above) when replacing a displayed document.
- **Send big files with the [multipart API]( {{ rootPrefix }}guides/browser-multipart/index.html )** —
  it transfers raw binary instead of base64-in-JSON, and integrates directly
  with `<input type="file">` and drag & drop.

</div>
