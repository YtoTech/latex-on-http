---
title: Calling from a browser (multipart API)
layout: base.njk
active: "/guides/browser-multipart/"
---

{% import "macros.njk" as macros %}

<div class="prose">

When the documents to compile come from the user — selected with a file input
or dropped on the page — the multipart API is the natural fit: files are
transferred as raw binary parts, with no base64 encoding step, and integrate
directly with the browser's `FormData`.

## Two styles for the multipart API

1. **Explicit** — describe the resources in a `resources` JSON form field, and
   reference the uploaded file parts by name with the `multipart` key. Gives
   you full control over paths and which file is the main document.
2. **Implicit** — just upload the files: the server takes the first `.tex`
   part as the main document and stores each part under its file name.

## Complete example: explicit resources with a file input

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Compile local files (multipart)</title>
</head>
<body>
  <form id="compile-form">
    <p>
      <label>Main document (.tex):
        <input type="file" name="main" accept=".tex" required>
      </label>
    </p>
    <p>
      <label>Annex files (images, bibliographies…):
        <input type="file" name="annexes" multiple>
      </label>
    </p>
    <button type="submit">Compile</button>
  </form>

  <div id="error" hidden>
    <h2>Compilation error</h2>
    <pre id="error-logs"></pre>
  </div>

  <!-- The PDF is displayed here. -->
  <iframe id="pdf-view" title="Compiled PDF" hidden></iframe>
  <a id="pdf-download" download="document.pdf" hidden>Download the PDF</a>

  <script>
    const API_URL = "https://latex.ytotech.com/builds/sync";

    function displayPdfBlob(pdfBlob) {
      const pdfUrl = URL.createObjectURL(pdfBlob);
      const viewer = document.getElementById("pdf-view");
      const download = document.getElementById("pdf-download");
      viewer.src = pdfUrl;
      viewer.hidden = false;
      download.href = pdfUrl;
      download.hidden = false;
    }

    async function compileFormData(entries) {
      // Build the resources specification: one entry per uploaded file,
      // bound to its multipart part name.
      const resources = entries.map((entry, index) => {
        const resource = { multipart: entry.fieldName, path: entry.file.name };
        if (index === 0) {
          resource.main = true;  // The first file is the main document.
        }
        return resource;
      });

      const formData = new FormData();
      formData.append("compiler", "pdflatex");
      formData.append("resources", JSON.stringify(resources));
      for (const entry of entries) {
        formData.append(entry.fieldName, entry.file, entry.file.name);
      }

      // Do NOT set Content-Type manually: the browser adds the multipart
      // boundary itself.
      const response = await fetch(API_URL, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        document.getElementById("error").hidden = false;
        document.getElementById("error-logs").textContent =
          error.error + "\n\n" + (error.logs || "");
        return;
      }
      document.getElementById("error").hidden = true;
      displayPdfBlob(await response.blob());
    }

    document.getElementById("compile-form").addEventListener("submit", (event) => {
      event.preventDefault();
      const mainInput = event.target.elements.main;
      const annexesInput = event.target.elements.annexes;
      // Keep each file together with the multipart part name it will be sent under.
      const entries = [
        ...[...mainInput.files].map((file) => ({ file, fieldName: "main" })),
        ...[...annexesInput.files].map(
          (file, index) => ({ file, fieldName: "annex" + index })
        ),
      ];
      compileFormData(entries);
    });
  </script>
</body>
</html>
```

## Implicit style: just upload the files

Without a `resources` field, the server reconstructs the specification from
the uploaded parts: the first `.tex` part becomes the main document, and each
part is stored under its upload file name:

```javascript
const formData = new FormData();
formData.append("main.tex", mainTexFile);
formData.append("logo.png", logoPngFile);

const response = await fetch("https://latex.ytotech.com/builds/sync", {
  method: "POST",
  body: formData,
});
```

## Upload progress with XMLHttpRequest

`fetch` does not expose upload progress; use `XMLHttpRequest` when you want a
progress bar for large file uploads (the request/response handling is
otherwise identical):

```javascript
function compileWithProgress(formData, onProgress) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", "https://latex.ytotech.com/builds/sync");
    request.responseType = "blob";
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        onProgress(event.loaded / event.total);
      }
    });
    request.addEventListener("load", () => {
      if (request.status === 201) {
        resolve(request.response);  // The PDF blob.
      } else {
        // Error payloads are JSON: read them from the blob.
        request.response.text().then((text) => reject(JSON.parse(text)));
      }
    });
    request.addEventListener("error", () => reject(new Error("Network error")));
    request.send(formData);
  });
}
```

## Notes

- **Do not set `Content-Type` yourself** on multipart requests: the browser
  generates it with the boundary that delimits the parts.
- **Mixed sources are allowed**: entries of the `resources` specification
  without a `multipart` key can still use inline `content`, base64 `file` or
  `url` sources — handy to mix user-uploaded files with server-known assets.
- **Non-`.tex` main document?** In implicit mode the first `.tex` part wins;
  with unusual layouts, use the explicit style and flag `main: true` on the
  right entry.
- See also the [JSON browser guide]( {{ rootPrefix }}guides/browser/index.html ) for displaying the PDF
  in the page and the error-handling patterns — they are the same here.

</div>
