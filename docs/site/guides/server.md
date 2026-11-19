---
title: Calling from server code
layout: base.njk
active: "/guides/server/"
---

{% import "macros.njk" as macros %}

<div class="prose">

Calling the API from your backend is the most common integration: generate
invoices, reports, diplomas or user-uploaded documents on demand, without
installing or operating a TeXLive distribution. The HTTP API is plain REST —
any language or framework that speaks HTTP can use it.

The synchronous `POST /builds/sync` endpoint waits for the compilation to
finish and returns the PDF as the response body. Compilation typically takes
a few hundred milliseconds to a few seconds; budget a generous HTTP timeout.

## Python (requests)

Send the document inline as a `content` resource, and annex files through
`url`, `file` (base64) or additional `content` entries. Handle compilation
errors by reading the JSON failure payload:

```python
import requests

API_URL = "https://latex.ytotech.com/builds/sync"  # Or your self-hosted instance.

payload = {
    "compiler": "lualatex",
    "resources": [
        {
            "main": True,
            "content": "\\documentclass{article}\n"
                       "\\begin{document}\n"
                       "Hello from the server code.\n"
                       "\\end{document}",
        },
        {
            # Dependencies are stored under `path`, relative to the main
            # document, and can be referenced from the LaTeX sources.
            "path": "logo.png",
            "url": "https://www.ytotech.com/images/ytotech_logo.png",
        },
    ],
}

response = requests.post(API_URL, json=payload, timeout=120)

if response.ok:
    with open("document.pdf", "wb") as pdf_file:
        pdf_file.write(response.content)
else:
    error = response.json()
    # `error["error"]` is a machine-readable error code, eg. COMPILATION_ERROR;
    # `error["logs"]` contains the compiler output and `error["log_files"]`
    # the full LaTeX logs (unless log_files_on_failure is disabled).
    print(f"Compilation failed: {error['error']}")
    print(error.get("logs", ""))
```

For large or regularly generated documents, stream the body to a file instead
of buffering it in memory:

```python
with requests.post(API_URL, json=payload, stream=True, timeout=120) as response:
    response.raise_for_status()
    with open("document.pdf", "wb") as pdf_file:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            pdf_file.write(chunk)
```

## Node.js (fetch)

```javascript
import { writeFile } from "node:fs/promises";

const payload = {
  compiler: "pdflatex",
  resources: [
    {
      main: true,
      content: `\\documentclass{article}
\\begin{document}
Hello from the server code.
\\end{document}`,
    },
  ],
};

const response = await fetch("https://latex.ytotech.com/builds/sync", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload),
});

if (response.ok) {
  const pdf = Buffer.from(await response.arrayBuffer());
  await writeFile("document.pdf", pdf);
} else {
  const error = await response.json();
  console.error(`Compilation failed: ${error.error}`);
  console.error(error.logs);
}
```

## PHP

`file_get_contents` with a stream context — available in every PHP
installation, no curl extension required:

```php
<?php

$apiUrl = "https://latex.ytotech.com/builds/sync";  // Or your self-hosted instance.

$payload = json_encode([
    "compiler" => "lualatex",
    "resources" => [
        [
            "main" => true,
            "content" => "\\documentclass{article}\n"
                . "\\begin{document}\n"
                . "Hello from the server code.\n"
                . "\\end{document}",
        ],
        [
            // Dependencies are stored under `path`, relative to the main
            // document, and can be referenced from the LaTeX sources.
            "path" => "logo.png",
            "url" => "https://www.ytotech.com/images/ytotech_logo.png",
        ],
    ],
]);

$context = stream_context_create([
    "http" => [
        "method" => "POST",
        "header" => "Content-Type: application/json\r\n",
        "content" => $payload,
        "timeout" => 120,
        // Return the body of 4xx responses as well, so compilation failures
        // can be handled instead of emitting a PHP warning.
        "ignore_errors" => true,
    ],
]);

$response = file_get_contents($apiUrl, false, $context);
// First header line, eg. "HTTP/1.1 201 Created":
$statusLine = $http_response_header[0] ?? "";

if ($response !== false && str_contains($statusLine, "201")) {
    file_put_contents("document.pdf", $response);
} elseif ($response !== false) {
    $error = json_decode($response, true);
    // `error["error"]` is a machine-readable error code, eg. COMPILATION_ERROR;
    // `error["logs"]` contains the compiler output and `error["log_files"]`
    // the full LaTeX logs (unless log_files_on_failure is disabled).
    echo "Compilation failed: " . ($error["error"] ?? "SERVER_ERROR") . "\n";
    echo ($error["logs"] ?? "") . "\n";
} else {
    echo "Request failed: no response from the compilation service.\n";
}
```

## Practical notes

- **Timeouts.** The server kills compilations after a timeout
  (`DEFAULT_COMPILE_TIMEOUT`, 100 s by default) and answers
  `COMPILATION_TIMEOUT`. Set your HTTP client timeout above it (2 minutes is a
  reasonable default), and account for the time spent fetching remote
  resources.
- **Job tracking.** Every builds response carries an `X-Job-ID` header
  identifying the compilation job server-side — useful to correlate your
  application logs with the compilation service logs.
- **Error payloads.** Failures are JSON with an `error` code, the compiler
  `logs`, and by default the full `log_files` — surface those to your users or
  your logging system rather than the HTTP status alone. See the
  [error code table]( {{ rootPrefix }}api/builds-sync/index.html#errors ).
- **Idempotence and caching.** The same input specification (compiler,
  options, resource contents) always produces the same PDF: safe to retry on
  transient network errors.
- **Do not block your request thread longer than needed**: if you generate
  many documents, parallelize with a bounded worker pool — each compilation
  runs in an isolated sandbox server-side.

{{ macros.callout("tip", "<p>Writing your LaTeX with a template engine (Jinja2, Mustache…)? Escape
nothing special — just be careful that your template output is valid LaTeX, and
send it as a <code>content</code> resource. Keep static assets (logos, class
files) as <code>url</code> or <code>file</code> resources to avoid embedding
them in every request.</p>") }}

</div>
