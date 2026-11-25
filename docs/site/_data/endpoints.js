/**
 * Single source of truth for the LaTeX-on-HTTP API documentation.
 *
 * Consumed by:
 * - the API reference templates (parameter tables, code samples);
 * - the playground page (emitted as playground/endpoints.json at build time).
 */

const BASE_URL = "https://latex.ytotech.com";

const COMPILERS = [
  ["pdflatex", "Default. Classic pdfTeX, ASCII-oriented, widely compatible."],
  ["xelatex", "Unicode-native engine, uses system fonts (fontspec)."],
  ["lualatex", "Unicode-native engine with embedded Lua scripting."],
  ["platex", "Japanese pTeX engine (DVI output, converted with dvipdfmx)."],
  ["uplatex", "Unicode Japanese upTeX engine (DVI output, converted with dvipdfmx)."],
  ["context", "ConTeXt standalone typesetting system."],
];

// options.* properties accepted in the builds/sync payload.
const BUILD_OPTIONS = [
  {
    name: "options.compiler.bibliography",
    type: "boolean",
    default: "true",
    description:
      "Run bibtex/biber as needed to regenerate <code>.bbl</code> files "
      + "(LaTeXmk <code>-bibtex</code> option).",
  },
  {
    name: "options.compiler.halt_on_error",
    type: "boolean",
    default: "false",
    description:
      "Stop on the first error, even if non-fatal "
      + "(<code>-halt-on-error</code> option).",
  },
  {
    name: "options.compiler.silent",
    type: "boolean",
    default: "false",
    description:
      "Non-verbose mode: <code>-interaction=batchmode</code> and LaTeXmk "
      + "<code>-silent</code>. By default <code>-interaction=nonstopmode</code> is used.",
  },
  {
    name: "options.compiler.force",
    type: "boolean",
    default: "true",
    description:
      "Force LaTeXmk to process the document even if errors occur "
      + "(<code>-f</code> flag).",
  },
  {
    name: "options.compiler.shell_escape",
    type: "boolean",
    default: "false",
    description:
      "Enable TeX <code>-shell-escape</code> inside the isolated compilation "
      + "sandbox, for packages such as <code>minted</code> that run "
      + "<code>pygmentize</code>. The engine otherwise receives an explicit "
      + "<code>-no-shell-escape</code> option. "
      + "<a href='https://github.com/YtoTech/latex-on-http/blob/master/docs/sandboxing.md'>See the sandboxing model</a>.",
  },
  {
    name: "options.response.log_files_on_failure",
    type: "boolean",
    default: "true",
    description:
      "Return the full LaTeX log files (<code>log_files</code> property) "
      + "in the JSON payload on compilation error.",
  },
  {
    name: "options.response.commands",
    type: "boolean",
    default: "false",
    description:
      "Return the details of the commands run during the compilation "
      + "(<code>commands</code> property) in the JSON payload on compilation error.",
  },
];

// Resource entry fields for the JSON/multipart APIs.
const RESOURCE_FIELDS = [
  {
    name: "main",
    type: "boolean",
    description:
      "Mark the entry as the <a href='https://en.wikibooks.org/wiki/LaTeX/Modular_Documents'>"
      + "main LaTeX document</a>. With several entries exactly one must be flagged; "
      + "with a single entry it is the main document automatically.",
  },
  {
    name: "path",
    type: "string",
    description:
      "File path, relative to the main document, under which the resource is "
      + "written server-side before the compilation. Mandatory for non-main "
      + "entries so they can be referred to from the LaTeX sources.",
  },
  {
    name: "content",
    type: "string",
    description:
      "Resource source: plain text content, as a valid JSON string "
      + "(UTF-8). Use this mode for LaTeX sources.",
  },
  {
    name: "file",
    type: "string (base64)",
    description:
      "Resource source: file content, "
      + "<a href='https://en.wikipedia.org/wiki/Base64'>base64</a>-encoded.",
  },
  {
    name: "url",
    type: "string (URL)",
    description:
      "Resource source: the file is downloaded by the server from this URL "
      + "before the compilation.",
  },
  {
    name: "cache",
    type: "string (hash)",
    description:
      "Resource source: retrieve the content from the server input cache, "
      + "identified by its <code>sha256:…</code> hash. Only useful to smart "
      + "clients that precomputed resource hashes "
      + "(<a href='../caches/'>caches API</a>).",
  },
  {
    name: "multipart",
    type: "string",
    description:
      "Multipart API only: name of the <code>multipart/form-data</code> part "
      + "holding the resource content. The part is read as binary data "
      + "(base64-encoded server-side).",
  },
];

// Error codes returned as JSON payloads (400s and friends).
const BUILD_ERRORS = [
  {
    code: "INVALID_PAYLOAD_SHAPE",
    http: "400",
    description:
      "The payload does not match the input specification "
      + "(<code>shape_errors</code> details the schema violations).",
  },
  {
    code: "MISSING_COMPILATION_SPECIFICATION",
    http: "400",
    description: "No compilation specification could be parsed from the request.",
  },
  {
    code: "MISSING_RESOURCES",
    http: "400",
    description: "The <code>resources</code> list is missing.",
  },
  {
    code: "RESOURCES_SPEC_MUST_BE_A_LIST",
    http: "400",
    description: "<code>resources</code> is not a list.",
  },
  {
    code: "MULTIPLE_RESOURCE_SOURCES",
    http: "400",
    description:
      "A resource entry specifies several source fields at once "
      + "(<code>url</code>, <code>file</code>, <code>git</code>, <code>tar</code>, "
      + "<code>cache</code>, <code>content</code>): use exactly one.",
  },
  {
    code: "MUST_SPECIFY_MAIN_DOCUMENT",
    http: "400",
    description:
      "No resource is flagged as the main document "
      + "(<code>main: true</code>), while the compilation has several entries.",
  },
  {
    code: "MORE_THAN_ONE_MAIN_DOCUMENT",
    http: "400",
    description: "Several resources are flagged as the main document.",
  },
  {
    code: "MISSING_PATH_ON_RESOURCE",
    http: "400",
    description: "A non-main resource entry is missing its <code>path</code>.",
  },
  {
    code: "INVALID_COMPILER",
    http: "400",
    description:
      "Unknown <code>compiler</code> value. "
      + "<code>available_compilers</code> lists the supported engines.",
  },
  {
    code: "INVALID_RESOURCE_TYPE",
    http: "400",
    description:
      "Querystring mode: <code>resource-type[]</code> is not one of "
      + "<code>url</code>, <code>file</code> (or <code>base64</code>), "
      + "<code>content</code> (or <code>string</code>).",
  },
  {
    code: "RESOURCES_SPEC_MUST_BE_OF_SAME_LENGTH",
    http: "400",
    description:
      "Querystring mode: <code>resource-path[]</code>, <code>resource-type[]</code> "
      + "and <code>resource-value[]</code> have different lengths.",
  },
  {
    code: "INVALID_STRING_CONTENT",
    http: "400",
    description: "A <code>content</code> resource is not a JSON string.",
  },
  {
    code: "INVALID_BASE64_CONTENT",
    http: "400",
    description: "A <code>file</code> resource is not valid base64 content. "
      + "<code>path</code> is the resource's path in the build filesystem.",
  },
  {
    code: "RESOURCE_FETCH_FAILURE",
    http: "400",
    description:
      "A resource could not be fetched. "
      + "<code>fetch_error</code> carries a machine-readable <code>type</code>: "
      + "<code>http_error</code> (a non-2xx status), <code>connection_error</code>, "
      + "<code>request_timeout</code>, <code>invalid_url</code> (missing or "
      + "unsupported scheme, no host, or an invalid port — "
      + "<code>allowed_schemes</code> lists the accepted schemes), "
      + "<code>ssrf_blocked</code> (the URL would reach a private, loopback or "
      + "link-local address), <code>resource_too_large</code> (the resource "
      + "exceeds the instance <code>MAX_RESOURCE_SIZE</code> limit — "
      + "<code>size</code> and <code>max_size</code> are in bytes) or "
      + "<code>total_too_large</code> (the combined size of the build's "
      + "fetched resources exceeds the instance "
      + "<code>MAX_TOTAL_RESOURCE_SIZE</code> limit — <code>total_size</code> "
      + "and <code>max_total_size</code> are in bytes). The size limits apply "
      + "to every resource type, including inline content and cache hits.",
  },
  {
    code: "FETCH_METHOD_NOT_SUPPORTED",
    http: "400",
    description:
      "The resource source is not implemented server-side "
      + "(eg. <code>git</code>/<code>tar</code> are accepted by the schema "
      + "but not yet supported).",
  },
  {
    code: "COMPILATION_ERROR",
    http: "400",
    description:
      "The LaTeX compilation failed. <code>logs</code> (and, by default, "
      + "<code>log_files</code>) detail the LaTeX errors.",
  },
  {
    code: "COMPILATION_TIMEOUT",
    http: "400",
    description:
      "The compilation exceeded the server timeout "
      + "(<code>DEFAULT_COMPILE_TIMEOUT</code>, 100 s by default).",
  },
  {
    code: "SANDBOX_UNAVAILABLE",
    http: "503",
    description:
      "The compilation sandbox could not be set up; the server refuses to "
      + "compile without isolation. "
      + "<a href='https://github.com/YtoTech/latex-on-http/blob/master/docs/sandboxing.md'>See the sandboxing documentation</a>.",
  },
  {
    code: "QUOTA_EXCEEDED",
    http: "429",
    description:
      "Fair-use quota exceeded for your client IP. Honor "
      + "<code>Retry-After</code> and back off: continuing to retry escalates "
      + "into a temporary ban. "
      + "<a href='../rate-limiting/'>See the rate limiting documentation</a>.",
  },
  {
    code: "QUOTA_STORE_UNAVAILABLE",
    http: "503",
    description:
      "The quota store (Valkey) is unreachable on an instance configured "
      + "with <code>QUOTA_FAIL_MODE=closed</code>; most instances fail open "
      + "and keep serving instead.",
  },
  {
    code: "REQUEST_TOO_LARGE",
    http: "413",
    description:
      "The request body exceeds the instance limit "
      + "(<code>MAX_REQUEST_BODY_BYTES</code>, 40 MiB by default). Reduce the "
      + "size of the uploaded resources; the body is rejected before it is "
      + "read.",
  },
  {
    code: "SERVER_ERROR",
    http: "500",
    description: "An unexpected error occurred server-side.",
  },
];

// ----------------------------------------------------------------------------
// Shared sample documents.
// ----------------------------------------------------------------------------

// A three-resource sample: main document (string), image (URL), second
// LaTeX file (base64). The base64 payload decodes to:
// "This is the second page, which was passed as a base64 encoded file".
const SAMPLE_MAIN_CONTENT = String.raw`\documentclass{article}
\usepackage{graphicx}
\begin{document}
 Hello World\\
 \includegraphics[height=2cm,width=7cm,keepaspectratio=true]{logo.png}
 \include{page2}
\end{document}`;

const SAMPLE_RESOURCES = [
  {
    main: true,
    content: SAMPLE_MAIN_CONTENT,
  },
  {
    path: "logo.png",
    url: "https://www.ytotech.com/images/ytotech_logo.png",
  },
  {
    path: "page2.tex",
    file: "VGhpcyBpcyB0aGUgc2Vjb25kIHBhZ2UsIHdoaWNoIHdhcyBwYXNzZWQgYXMgYSBiYXNlNjQgZW5jb2RlZCBmaWxl",
  },
];

const JSON_PAYLOAD_SAMPLE = JSON.stringify(
  {
    compiler: "lualatex",
    resources: SAMPLE_RESOURCES,
  },
  null,
  4
);

// Indented, single-quoted shell-safe variant for curl -d samples.
const JSON_PAYLOAD_SAMPLE_SHELL = JSON_PAYLOAD_SAMPLE.replace(/'/g, "'\\''");

const SIMPLE_HELLO = String.raw`\documentclass{article}
\begin{document}
Hello World LaTeX-On-HTTP
\end{document}`;

// ----------------------------------------------------------------------------
// Code sample builders.
// ----------------------------------------------------------------------------

function curlGetSample() {
  return [
    "# Compile a document passed inline as the main resource:",
    "curl -G " + BASE_URL + "/builds/sync \\",
    "    --data-urlencode 'content=" + SIMPLE_HELLO.replace(/\n/g, " ") + "' \\",
    "    --output hello_world.pdf",
    "",
    "# Compile a document fetched from an URL, with the XeLaTeX compiler,",
    "# plus an annex resource (an image downloaded from an URL):",
    "curl -G " + BASE_URL + "/builds/sync \\",
    "    --data-urlencode 'compiler=xelatex' \\",
    "    --data-urlencode 'url="
      + BASE_URL_REF_EXAMPLE + "' \\",
    "    --data-urlencode 'resource-type[]=url' \\",
    "    --data-urlencode 'resource-path[]=logo.png' \\",
    "    --data-urlencode 'resource-value[]=https://www.ytotech.com/images/ytotech_logo.png' \\",
    "    --output resume.pdf",
  ].join("\n");
}

// Referenced to avoid repeating the long GitHub raw URL in several builders.
const BASE_URL_REF_EXAMPLE =
  "https://raw.githubusercontent.com/YtoTech/latex-on-http/master/examples/templates/moderncv.tex";

function pythonGetSample() {
  return [
    "import requests",
    "",
    "response = requests.get(",
    '    "' + BASE_URL + '/builds/sync",',
    "    params={",
    '        "compiler": "pdflatex",',
    '        "content": (',
    '            "\\\\documentclass{article}\\n"',
    '            "\\\\begin{document}\\n"',
    '            "Hello World LaTeX-On-HTTP\\n"',
    '            "\\\\end{document}"',
    "        ),",
    '        "resource-type[]": "url",',
    '        "resource-path[]": "logo.png",',
    '        "resource-value[]": "https://www.ytotech.com/images/ytotech_logo.png",',
    "    },",
    "    timeout=120,",
    ")",
    "response.raise_for_status()",
    'with open("hello_world.pdf", "wb") as pdf_file:',
    "    pdf_file.write(response.content)",
  ].join("\n");
}

function javascriptGetSample() {
  return [
    "const params = new URLSearchParams({",
    '  compiler: "pdflatex",',
    '  content: "\\\\documentclass{article}\\n\\\\begin{document}\\n"',
    '    + "Hello World LaTeX-On-HTTP\\n\\\\end{document}",',
    '  "resource-type[]": "url",',
    '  "resource-path[]": "logo.png",',
    '  "resource-value[]": "https://www.ytotech.com/images/ytotech_logo.png",',
    "});",
    'const response = await fetch("'
      + BASE_URL + '/builds/sync?" + params.toString());',
    "if (!response.ok) {",
    "  const error = await response.json();",
    '  console.error(`Compilation failed: ${error.error}`, error.logs);',
    "} else {",
    "  // The body is the compiled PDF: pipe it to a file, a blob, etc.",
    "  const pdfBlob = await response.blob();",
    "}",
  ].join("\n");
}

function curlJsonSample() {
  return [
    "curl -X POST " + BASE_URL + "/builds/sync \\",
    '    -H "Content-Type: application/json" \\',
    "    -d '" + JSON_PAYLOAD_SAMPLE_SHELL + "' \\",
    "    --output hello_world.pdf",
  ].join("\n");
}

function pythonJsonSample() {
  return [
    "import requests",
    "",
    "payload = {",
    '    "compiler": "lualatex",',
    '    "resources": [',
    "        {",
    '            "main": True,',
    '            "content": "\\\\documentclass{article}\\n \\\\usepackage{graphicx}\\n'
      + "  \\\\begin{document}\\n Hello World\\\\\\\\\\n"
      + " \\\\includegraphics[height=2cm,width=7cm,keepaspectratio=true]{logo.png}\\n"
      + " \\\\include{page2}\\n \\\\end{document}\",",
    "        },",
    "        {",
    '            "path": "logo.png",',
    '            "url": "https://www.ytotech.com/images/ytotech_logo.png",',
    "        },",
    "        {",
    '            "path": "page2.tex",',
    '            "file": "VGhpcyBpcyB0aGUgc2Vjb25kIHBhZ2UsIHdoaWNoIHdhcyBwYXNzZWQgYXMgYSBiYXNlNjQgZW5jb2RlZCBmaWxl",',
    "        },",
    "    ],",
    "}",
    "response = requests.post(",
    '    "' + BASE_URL + '/builds/sync",',
    "    json=payload,",
    "    timeout=120,",
    ")",
    "if response.ok:",
    '    with open("hello_world.pdf", "wb") as pdf_file:',
    "        pdf_file.write(response.content)",
    "else:",
    "    error = response.json()",
    "    print(f\"Compilation failed: {error['error']}\")",
    '    print(error.get("logs", ""))',
  ].join("\n");
}

function javascriptJsonSample() {
  return [
    "const response = await fetch(\""
      + BASE_URL + "/builds/sync\", {",
    '  method: "POST",',
    '  headers: { "Content-Type": "application/json" },',
    "  body: JSON.stringify({",
    '    compiler: "lualatex",',
    "    resources: [",
    "      {",
    "        main: true,",
    '        content: "\\\\documentclass{article}\\n \\\\usepackage{graphicx}\\n'
      + "  \\\\begin{document}\\n Hello World\\\\\\\\\\n"
      + " \\\\includegraphics[height=2cm,width=7cm,keepaspectratio=true]{logo.png}\\n"
      + " \\\\include{page2}\\n \\\\end{document}\",",
    "      },",
    "      {",
    '        path: "logo.png",',
    '        url: "https://www.ytotech.com/images/ytotech_logo.png",',
    "      },",
    "      {",
    '        path: "page2.tex",',
    '        file: "VGhpcyBpcyB0aGUgc2Vjb25kIHBhZ2UsIHdoaWNoIHdhcyBwYXNzZWQgYXMgYSBiYXNlNjQgZW5jb2RlZCBmaWxl",',
    "      },",
    "    ],",
    "  }),",
    "});",
    "if (!response.ok) {",
    "  const error = await response.json();",
    '  console.error(`Compilation failed: ${error.error}`, error.logs);',
    "} else {",
    "  const pdfBlob = await response.blob();",
    "}",
  ].join("\n");
}

function curlMultipartSample() {
  return [
    "# Declare the resources with a JSON form entry, and reference the",
    "# uploaded multipart file parts by name (binary transfer, no base64):",
    "curl -X POST " + BASE_URL + "/builds/sync \\",
    "    -F 'compiler=pdflatex' \\",
    "    -F 'resources=[{\"main\": true, \"multipart\": \"main\"}, {\"path\": \"logo.png\", \"multipart\": \"logo\"}]' \\",
    "    -F 'main=@main.tex' \\",
    "    -F 'logo=@logo.png' \\",
    "    --output document.pdf",
    "",
    "# Or simply upload the files: the first .tex part is taken as the",
    "# main document, and every part is stored under its file name.",
    "curl -X POST " + BASE_URL + "/builds/sync \\",
    "    -F 'file=@main.tex' \\",
    "    --output document.pdf",
  ].join("\n");
}

function httpieMultipartSample() {
  return [
    "# Inline content with HTTPie:",
    "http --multipart --download --output hello.pdf -v POST "
      + BASE_URL + "/builds/sync \\",
    "    compiler=pdflatex \\",
    "    resources='[{\"main\": true, \"content\": \"\\\\documentclass{article}\\n \\\\begin{document}\\n Hello World\\n \\\\end{document}\"}]'",
    "",
    "# Local files, referenced in the resources specification:",
    "http --multipart --download --output document.pdf POST "
      + BASE_URL + "/builds/sync \\",
    "    file1@main.tex \\",
    "    compiler=xelatex \\",
    '    resources=\'[{"main": true, "multipart": "file1"}]\'',
  ].join("\n");
}

function pythonMultipartSample() {
  return [
    "import json",
    "import requests",
    "",
    "resources = [",
    '    {"main": True, "multipart": "main"},',
    '    {"path": "logo.png", "multipart": "logo"},',
    "]",
    'with open("main.tex", "rb") as main_file, open("logo.png", "rb") as logo_file:',
    "    response = requests.post(",
    '        "' + BASE_URL + '/builds/sync",',
    "        data={",
    '            "compiler": "pdflatex",',
    '            "resources": json.dumps(resources),',
    "        },",
    "        files=[",
    '            ("main", ("main.tex", main_file)),',
    '            ("logo", ("logo.png", logo_file)),',
    "        ],",
    "        timeout=120,",
    "    )",
    "response.raise_for_status()",
    'with open("document.pdf", "wb") as pdf_file:',
    "    pdf_file.write(response.content)",
  ].join("\n");
}

function javascriptMultipartSample() {
  return [
    "const resources = [",
    '  { main: true, multipart: "main" },',
    '  { path: "logo.png", multipart: "logo" },',
    "];",
    "const formData = new FormData();",
    'formData.append("compiler", "pdflatex");',
    'formData.append("resources", JSON.stringify(resources));',
    'formData.append("main", mainTexFile);  // File objects, eg. from <input type="file">',
    'formData.append("logo", logoPngFile);',
    "",
    "const response = await fetch(\""
      + BASE_URL + "/builds/sync\", {",
    '  method: "POST",',
    "  body: formData,  // The browser sets the multipart Content-Type itself.",
    "});",
  ].join("\n");
}

function curlGetInfoSample(path, filter) {
  const command = "curl " + BASE_URL + path;
  if (filter) {
    return command + " | python3 -m json.tool";
  }
  return command;
}

// ----------------------------------------------------------------------------
// Landing-page quickstart samples.
// ----------------------------------------------------------------------------

const QUICKSTART_SAMPLES = [
  {
    label: "curl (GET)",
    language: "bash",
    code: [
      "curl -G " + BASE_URL + "/builds/sync \\",
      "    --data-urlencode 'content="
        + SIMPLE_HELLO.replace(/\n/g, " ") + "' \\",
      "    --output hello_world.pdf",
    ].join("\n"),
  },
  {
    label: "curl (JSON)",
    language: "bash",
    code: [
      "curl -X POST " + BASE_URL + "/builds/sync \\",
      '    -H "Content-Type: application/json" \\',
      "    -d '" + JSON_PAYLOAD_SAMPLE.replace(/'/g, "'\\''") + "' \\",
      "    --output hello_world.pdf",
    ].join("\n"),
  },
];

// ----------------------------------------------------------------------------
// Builders for the additional language tabs (HTTPie, PHP, Go, Elixir, CLJS).
// ----------------------------------------------------------------------------

const MAIN_CONTENT_FULL = String.raw`\\documentclass{article}\n \\usepackage{graphicx}\n  \\begin{document}\n Hello World\\\\\n \\includegraphics[height=2cm,width=7cm,keepaspectratio=true]{logo.png}\n \\include{page2}\n \\end{document}`;

function elixirMixInstall(extraDeps) {
  return [
    "Mix.install([{:req, \"~> 0.8\"}" + (extraDeps || "") + "])",
    "",
  ].join("\n");
}

function httpieGetBuildSample() {
  return [
    "# Compile a document passed inline as the main resource:",
    "http --download --output hello_world.pdf GET "
      + BASE_URL + "/builds/sync \\",
    "    compiler==pdflatex \\",
    "    'content==" + SIMPLE_HELLO.replace(/\n/g, " ") + "'",
    "",
    "# Compile a document fetched from an URL, with the XeLaTeX compiler,",
    "# plus an annex resource (an image downloaded from an URL):",
    "http --download --output resume.pdf GET "
      + BASE_URL + "/builds/sync \\",
    "    compiler==xelatex \\",
    "    'url==" + BASE_URL_REF_EXAMPLE + "' \\",
    "    'resource-type[]==url' \\",
    "    'resource-path[]==logo.png' \\",
    "    'resource-value[]==https://www.ytotech.com/images/ytotech_logo.png'",
  ].join("\n");
}

function httpieJsonBuildSample() {
  return [
    "http --download --output hello_world.pdf POST "
      + BASE_URL + "/builds/sync \\",
    "    compiler=lualatex \\",
    "    resources:='" + JSON.stringify(SAMPLE_RESOURCES, null, 4) + "'",
  ].join("\n");
}

function phpGetBuildSample() {
  return [
    "<?php",
    "// Annex resources are passed as resource-path[]/resource-type[]/",
    "// resource-value[] entries; for several resources, build the query",
    "// manually to repeat each resource-*[] key.",
    "$params = [",
    '    "compiler" => "pdflatex",',
    '    "content" => "\\\\documentclass{article}\\n\\\\begin{document}\\n'
      + "Hello World LaTeX-On-HTTP\\n\\\\end{document}\",",
    '    "resource-type[]" => "url",',
    '    "resource-path[]" => "logo.png",',
    '    "resource-value[]" => "https://www.ytotech.com/images/ytotech_logo.png",',
    "];",
    "$pdf = file_get_contents(\""
      + BASE_URL + "/builds/sync?\" . http_build_query($params));",
    "if ($pdf !== false) {",
    '    file_put_contents("hello_world.pdf", $pdf);',
    "}",
  ].join("\n");
}

function phpJsonBuildSample() {
  return [
    "<?php",
    "$payload = json_encode([",
    '    "compiler" => "lualatex",',
    '    "resources" => [',
    "        [",
    '            "main" => true,',
    '            "content" => "' + MAIN_CONTENT_FULL + '",',
    "        ],",
    "        [",
    '            "path" => "logo.png",',
    '            "url" => "https://www.ytotech.com/images/ytotech_logo.png",',
    "        ],",
    "        [",
    '            "path" => "page2.tex",',
    '            "file" => "VGhpcyBpcyB0aGUgc2Vjb25kIHBhZ2UsIHdoaWNoIHdhcyBwYXNzZWQgYXMgYSBiYXNlNjQgZW5jb2RlZCBmaWxl",',
    "        ],",
    "    ],",
    "]);",
    "",
    "$context = stream_context_create([",
    '    "http" => [',
    '        "method" => "POST",',
    '        "header" => "Content-Type: application/json\\r\\n",',
    '        "content" => $payload,',
    '        "timeout" => 120,',
    '        // Return the body of 4xx responses as well, so compilation',
    '        // failures can be handled instead of emitting a PHP warning.',
    '        "ignore_errors" => true,',
    "    ],",
    "]);",
    "$response = file_get_contents(\"" + BASE_URL + "/builds/sync\", false, $context);",
    '$statusLine = $http_response_header[0] ?? "";',
    "",
    'if ($response !== false && str_contains($statusLine, "201")) {',
    '    file_put_contents("hello_world.pdf", $response);',
    "} else {",
    '    $error = json_decode($response, true);',
    '    echo "Compilation failed: {$error["error"]}\\n";',
    '    echo $error["logs"] . "\\n";',
    "}",
  ].join("\n");
}

function phpMultipartSample() {
  return [
    "<?php",
    "$ch = curl_init(\"" + BASE_URL + "/builds/sync\");",
    "curl_setopt_array($ch, [",
    "    CURLOPT_POST => true,",
    "    CURLOPT_POSTFIELDS => [",
    '        "compiler" => "pdflatex",',
    '        "resources" => json_encode([',
    '            ["main" => true, "multipart" => "main"],',
    '            ["path" => "logo.png", "multipart" => "logo"],',
    "        ]),",
    '        "main" => new CURLFile("main.tex"),',
    '        "logo" => new CURLFile("logo.png"),',
    "    ],",
    "    CURLOPT_RETURNTRANSFER => true,",
    "]);",
    "$response = curl_exec($ch);",
    "$status = curl_getinfo($ch, CURLINFO_HTTP_CODE);",
    "curl_close($ch);",
    "if ($status === 201) {",
    '    file_put_contents("document.pdf", $response);',
    "} else {",
    '    $error = json_decode($response, true);',
    '    echo "Compilation failed: {$error["error"]}\\n";',
    "}",
  ].join("\n");
}

function goGetBuildSample() {
  return [
    "package main",
    "",
    "import (",
    '    "io"',
    '    "log"',
    '    "net/http"',
    '    "net/url"',
    '    "os"',
    ")",
    "",
    "func main() {",
    "    params := url.Values{}",
    '    params.Set("compiler", "pdflatex")',
    '    params.Set("content", "\\\\documentclass{article}\\n\\\\begin{document}\\n'
      + "Hello World LaTeX-On-HTTP\\n\\\\end{document}\")",
    '    params.Set("resource-type[]", "url")',
    '    params.Set("resource-path[]", "logo.png")',
    '    params.Set("resource-value[]", "https://www.ytotech.com/images/ytotech_logo.png")',
    '    // For several resources, use params.Add to repeat each resource-*[] key.',
    "",
    '    response, err := http.Get("'
      + BASE_URL + "/builds/sync?\" + params.Encode())",
    "    if err != nil {",
    "        log.Fatal(err)",
    "    }",
    "    defer response.Body.Close()",
    "",
    "    pdf, err := io.ReadAll(response.Body)",
    "    if err != nil {",
    "        log.Fatal(err)",
    "    }",
    '    if response.StatusCode == http.StatusCreated {',
    '        os.WriteFile("hello_world.pdf", pdf, 0644)',
    "    } else {",
    '        log.Fatalf("Compilation failed: %s", pdf)',
    "    }",
    "}",
  ].join("\n");
}

function goJsonBuildSample() {
  return [
    "package main",
    "",
    "import (",
    '    "bytes"',
    '    "encoding/json"',
    '    "io"',
    '    "log"',
    '    "net/http"',
    '    "os"',
    ")",
    "",
    "func main() {",
    "    payload := map[string]any{",
    '        "compiler": "lualatex",',
    '        "resources": []map[string]any{',
    "            {",
    '                "main": true,',
    '                "content": "' + MAIN_CONTENT_FULL + '",',
    "            },",
    '            {"path": "logo.png", "url": "https://www.ytotech.com/images/ytotech_logo.png"},',
    "            {",
    '                "path": "page2.tex",',
    '                "file": "VGhpcyBpcyB0aGUgc2Vjb25kIHBhZ2UsIHdoaWNoIHdhcyBwYXNzZWQgYXMgYSBiYXNlNjQgZW5jb2RlZCBmaWxl",',
    "            },",
    "        },",
    "    }",
    "    body, err := json.Marshal(payload)",
    "    if err != nil {",
    "        log.Fatal(err)",
    "    }",
    "",
    "    response, err := http.Post(",
    '        "' + BASE_URL + '/builds/sync",',
    '        "application/json",',
    "        bytes.NewReader(body),",
    "    )",
    "    if err != nil {",
    "        log.Fatal(err)",
    "    }",
    "    defer response.Body.Close()",
    "",
    "    responseBody, _ := io.ReadAll(response.Body)",
    '    if response.StatusCode == http.StatusCreated {',
    '        os.WriteFile("hello_world.pdf", responseBody, 0644)',
    "    } else {",
    '        log.Fatalf("Compilation failed: %s", responseBody)',
    "    }",
    "}",
  ].join("\n");
}

function goMultipartSample() {
  return [
    "package main",
    "",
    "import (",
    '    "bytes"',
    '    "io"',
    '    "log"',
    '    "mime/multipart"',
    '    "net/http"',
    '    "os"',
    ")",
    "",
    "func main() {",
    "    var requestBody bytes.Buffer",
    "    writer := multipart.NewWriter(&requestBody)",
    '    _ = writer.WriteField("compiler", "pdflatex")',
    "    _ = writer.WriteField(",
    '        "resources",',
    '        `[{"main": true, "multipart": "main"}, {"path": "logo.png", "multipart": "logo"}]`,',
    "    )",
    '    for _, part := range []struct{ field, path string }{',
    '        {"main", "main.tex"},',
    '        {"logo", "logo.png"},',
    "    } {",
    "        file, err := os.Open(part.path)",
    "        if err != nil {",
    "            log.Fatal(err)",
    "        }",
    "        fileWriter, err := writer.CreateFormFile(part.field, part.path)",
    "        if err != nil {",
    "            log.Fatal(err)",
    "        }",
    "        if _, err := io.Copy(fileWriter, file); err != nil {",
    "            log.Fatal(err)",
    "        }",
    "        file.Close()",
    "    }",
    "    writer.Close()",
    "",
    "    request, err := http.NewRequest(",
    '        "POST",',
    '        "' + BASE_URL + '/builds/sync",',
    "        &requestBody,",
    "    )",
    "    if err != nil {",
    "        log.Fatal(err)",
    "    }",
    '    request.Header.Set("Content-Type", writer.FormDataContentType())',
    "",
    "    response, err := http.DefaultClient.Do(request)",
    "    if err != nil {",
    "        log.Fatal(err)",
    "    }",
    "    defer response.Body.Close()",
    "",
    "    responseBody, _ := io.ReadAll(response.Body)",
    '    if response.StatusCode == http.StatusCreated {',
    '        os.WriteFile("document.pdf", responseBody, 0644)',
    "    } else {",
    '        log.Fatalf("Compilation failed: %s", responseBody)',
    "    }",
    "}",
  ].join("\n");
}

function elixirGetBuildSample() {
  return [
    elixirMixInstall(),
    "response =",
    "  Req.get!(\"" + BASE_URL + "/builds/sync\",",
    "    params: [",
    '      {"compiler", "pdflatex"},',
    '      {"content", "\\\\documentclass{article}\\n\\\\begin{document}\\n'
      + "Hello World LaTeX-On-HTTP\\n\\\\end{document}\"},",
    '      {"resource-type[]", "url"},',
    '      {"resource-path[]", "logo.png"},',
    '      {"resource-value[]", "https://www.ytotech.com/images/ytotech_logo.png"}',
    "    ]",
    "  )",
    "",
    "if response.status == 201 do",
    '  File.write!("hello_world.pdf", response.body)',
    "else",
    '  IO.puts("Compilation failed: #{response.body["error"]}")',
    "end",
  ].join("\n");
}

function elixirJsonBuildSample() {
  return [
    elixirMixInstall(),
    "payload = %{",
    '  compiler: "lualatex",',
    "  resources: [",
    "    %{",
    "      main: true,",
    '      content: "' + MAIN_CONTENT_FULL + '"',
    "    },",
    '    %{path: "logo.png", url: "https://www.ytotech.com/images/ytotech_logo.png"},',
    "    %{",
    '      path: "page2.tex",',
    '      file: "VGhpcyBpcyB0aGUgc2Vjb25kIHBhZ2UsIHdoaWNoIHdhcyBwYXNzZWQgYXMgYSBiYXNlNjQgZW5jb2RlZCBmaWxl"',
    "    }",
    "  ]",
    "}",
    "",
    "response = Req.post!(\"" + BASE_URL + "/builds/sync\", json: payload)",
    "",
    "if response.status == 201 do",
    '  File.write!("hello_world.pdf", response.body)',
    "else",
    '  IO.puts("Compilation failed: #{response.body["error"]}")',
    '  IO.puts(response.body["logs"] || "")',
    "end",
  ].join("\n");
}

function elixirMultipartSample() {
  return [
    elixirMixInstall(", {:jason, \"~> 1.4\"}"),
    "resources = [",
    '  %{main: true, multipart: "main"},',
    '  %{path: "logo.png", multipart: "logo"}',
    "]",
    "",
    "response =",
    "  Req.post!(\"" + BASE_URL + "/builds/sync\",",
    "    form_multipart: [",
    '      {"compiler", "pdflatex"},',
    '      {"resources", Jason.encode!(resources)},',
    '      {"main", {File.read!("main.tex"), filename: "main.tex"}},',
    '      {"logo", {File.read!("logo.png"), filename: "logo.png"}}',
    "    ]",
    "  )",
    "",
    "if response.status == 201 do",
    '  File.write!("document.pdf", response.body)',
    "else",
    '  IO.puts("Compilation failed: #{response.body["error"]}")',
    "end",
  ].join("\n");
}

function cljsGetBuildSample() {
  return [
    "(let [params (js/URLSearchParams.)]",
    '  (.append params "compiler" "pdflatex")',
    '  (.append params "content" "\\\\documentclass{article}\\n\\\\begin{document}\\n'
      + "Hello World LaTeX-On-HTTP\\n\\\\end{document}\")",
    '  (.append params "resource-type[]" "url")',
    '  (.append params "resource-path[]" "logo.png")',
    '  (.append params "resource-value[]" "https://www.ytotech.com/images/ytotech_logo.png")',
    "  (-> (js/fetch (str \"" + BASE_URL + "/builds/sync?\" (.toString params)))",
    "      (.then (fn [response]",
    "               (if (.-ok response)",
    "                 (.then (.blob response)",
    "                        (fn [pdf-blob]",
    "                          ;; Display or save the PDF, eg.:",
    "                          (set! (.-src (.getElementById js/document \"pdf-view\"))",
    "                                (js/URL.createObjectURL pdf-blob))))",
    "                 (.then (.json response)",
    "                        (fn [error]",
    '                          (js/console.error \"Compilation failed\" error))))))))',
  ].join("\n");
}

function cljsJsonBuildSample() {
  return [
    "(-> (js/fetch \"" + BASE_URL + "/builds/sync\"",
    "              #js {:method \"POST\"",
    '                   :headers #js {"Content-Type" "application/json"}',
    "                   :body (js/JSON.stringify",
    "                          (clj->js {:compiler \"lualatex\"",
    "                                    :resources [{:main true",
    '                                                 :content "' + MAIN_CONTENT_FULL + '"}',
    '                                                {:path "logo.png"',
    '                                                 :url "https://www.ytotech.com/images/ytotech_logo.png"}',
    '                                                {:path "page2.tex"',
    '                                                 :file "VGhpcyBpcyB0aGUgc2Vjb25kIHBhZ2UsIHdoaWNoIHdhcyBwYXNzZWQgYXMgYSBiYXNlNjQgZW5jb2RlZCBmaWxl"}]}))})',
    "    (.then (fn [response]",
    "             (if (.-ok response)",
    "               (-> (.blob response)",
    "                   (.then (fn [pdf-blob]",
    "                            ;; Display the PDF in the page, eg.:",
    "                            (set! (.-src (.getElementById js/document \"pdf-view\"))",
    "                                  (js/URL.createObjectURL pdf-blob)))))",
    "               (-> (.json response)",
    "                   (.then (fn [error]",
    "                            (js/console.error (.-error error)",
    "                                              (.-logs error)))))))))",
  ].join("\n");
}

function cljsMultipartSample() {
  return [
    "(let [form-data (js/FormData.)",
    "      resources (clj->js [{:main true :multipart \"main\"}",
    '                          {:path "logo.png" :multipart "logo"}])]',
    '  (.append form-data "compiler" "pdflatex")',
    '  (.append form-data "resources" (js/JSON.stringify resources))',
    '  (.append form-data "main" main-tex-file "main.tex")  ;; File objects, eg. from <input type="file">',
    '  (.append form-data "logo" logo-png-file "logo.png")',
    "  (-> (js/fetch \"" + BASE_URL + "/builds/sync\"",
    '                #js {:method "POST" :body form-data})',
    "      (.then (fn [response]",
    "               (if (.-ok response)",
    "                 (-> (.blob response)",
    "                     (.then (fn [pdf-blob]",
    "                              ;; Display the PDF in the page, eg.:",
    "                              (set! (.-src (.getElementById js/document \"pdf-view\"))",
    "                                    (js/URL.createObjectURL pdf-blob)))))",
    "                 (-> (.json response)",
    "                     (.then (fn [error]",
    "                              (js/console.error (.-error error))))))))))",
  ].join("\n");
}

// Simple GET endpoints (texlive, fonts, packages, package detail, caches).
function httpieGetSample(path) {
  return "http --body GET " + BASE_URL + path;
}

function phpGetSample(path) {
  return [
    "<?php",
    "$response = json_decode(",
    '    file_get_contents("' + BASE_URL + path + '"),',
    "    true",
    ");",
    "print_r($response);",
  ].join("\n");
}

function goGetSample(path) {
  return [
    "package main",
    "",
    "import (",
    '    "encoding/json"',
    '    "fmt"',
    '    "log"',
    '    "net/http"',
    ")",
    "",
    "func main() {",
    "    response, err := http.Get(\"" + BASE_URL + path + "\")",
    "    if err != nil {",
    "        log.Fatal(err)",
    "    }",
    "    defer response.Body.Close()",
    "",
    "    var result map[string]any",
    '    if err := json.NewDecoder(response.Body).Decode(&result); err != nil {',
    "        log.Fatal(err)",
    "    }",
    "    fmt.Println(result)",
    "}",
  ].join("\n");
}

function elixirGetSample(path) {
  return [
    elixirMixInstall(),
    "response = Req.get!(\"" + BASE_URL + path + "\")",
    "IO.inspect(response.body)",
  ].join("\n");
}

function cljsGetSample(path) {
  return [
    "(-> (js/fetch \"" + BASE_URL + path + "\")",
    "    (.then (fn [response] (.json response)))",
    "    (.then (fn [data]",
    '             (js/console.log (js/JSON.stringify data nil 2)))))',
  ].join("\n");
}

function httpieDeleteSample(path) {
  return "http DELETE " + BASE_URL + path;
}

function phpDeleteSample(path) {
  return [
    "<?php",
    "$context = stream_context_create(",
    '    ["http" => ["method" => "DELETE"]]',
    ");",
    "file_get_contents(\"" + BASE_URL + path + "\", false, $context);",
  ].join("\n");
}

function goDeleteSample(path) {
  return [
    "package main",
    "",
    'import (',
    '    "fmt"',
    '    "net/http"',
    ')',
    "",
    "func main() {",
    '    request, _ := http.NewRequest("DELETE", "' + BASE_URL + path + '", nil)',
    "    response, err := http.DefaultClient.Do(request)",
    "    if err != nil {",
    "        panic(err)",
    "    }",
    "    defer response.Body.Close()",
    "    fmt.Println(response.StatusCode)",
    "}",
  ].join("\n");
}

function elixirDeleteSample(path) {
  return [
    elixirMixInstall(),
    "response = Req.delete!(\"" + BASE_URL + path + "\")",
    "IO.puts(response.status)",
  ].join("\n");
}

function cljsDeleteSample(path) {
  return [
    "(-> (js/fetch \"" + BASE_URL + path + "\"",
    '                #js {:method "DELETE"})',
    "    (.then (fn [response] (js/console.log (.-status response)))))",
  ].join("\n");
}

function httpieCheckCachedSample() {
  return [
    "http --body POST " + BASE_URL + "/caches/resources/check_cached \\",
    "    resources:='{\"resources\": [{\"hash\": \"sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08\"}]}'",
  ].join("\n");
}

function phpCheckCachedSample() {
  return [
    "<?php",
    "$payload = json_encode([",
    '    "resources" => [',
    "        [",
    '            "hash" => "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",',
    "        ],",
    "    ],",
    "]);",
    "$context = stream_context_create([",
    '    "http" => [',
    '        "method" => "POST",',
    '        "header" => "Content-Type: application/json\\r\\n",',
    '        "content" => $payload,',
    "    ],",
    "]);",
    "$response = file_get_contents(\""
      + BASE_URL + "/caches/resources/check_cached\", false, $context);",
    "print_r(json_decode($response, true));",
  ].join("\n");
}

function goCheckCachedSample() {
  return [
    "package main",
    "",
    "import (",
    '    "bytes"',
    '    "encoding/json"',
    '    "fmt"',
    '    "net/http"',
    ")",
    "",
    "func main() {",
    '    body, _ := json.Marshal(map[string]any{',
    '        "resources": []map[string]any{',
    '            {"hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"},',
    "        },",
    "    })",
    "    response, err := http.Post(",
    '        "' + BASE_URL + '/caches/resources/check_cached",',
    '        "application/json",',
    "        bytes.NewReader(body),",
    "    )",
    "    if err != nil {",
    "        panic(err)",
    "    }",
    "    defer response.Body.Close()",
    "",
    "    var result map[string]any",
    "    _ = json.NewDecoder(response.Body).Decode(&result)",
    "    fmt.Println(result)",
    "}",
  ].join("\n");
}

function elixirCheckCachedSample() {
  return [
    elixirMixInstall(),
    "response =",
    "  Req.post!(\"" + BASE_URL + "/caches/resources/check_cached\",",
    "    json: %{",
    '      resources: [%{hash: "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"}]',
    "    }",
    "  )",
    "IO.inspect(response.body)",
  ].join("\n");
}

function cljsCheckCachedSample() {
  return [
    "(-> (js/fetch \"" + BASE_URL + "/caches/resources/check_cached\"",
    "              #js {:method \"POST\"",
    '                   :headers #js {"Content-Type" "application/json"}',
    "                   :body (js/JSON.stringify",
    "                          (clj->js {:resources [{:hash \"sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08\"}]}))})",
    "    (.then (fn [response] (.json response)))",
    "    (.then (fn [data] (js/console.log data))))",
  ].join("\n");
}

// ----------------------------------------------------------------------------
// Endpoint definitions.
// ----------------------------------------------------------------------------

export default {
  baseUrl: BASE_URL,
  compilers: COMPILERS,
  buildOptions: BUILD_OPTIONS,
  resourceFields: RESOURCE_FIELDS,
  errors: BUILD_ERRORS,
  samplePayload: JSON_PAYLOAD_SAMPLE,
  quickstart: QUICKSTART_SAMPLES,
  endpoints: {
    buildsSync: {
      id: "builds-sync",
      path: "/builds/sync",
      title: "Compile a LaTeX document",
      summary:
        "Compile a LaTeX document and get back the generated PDF, waiting "
        + "for the end of the build (synchronous).",
      methods: ["GET", "POST"],
      modes: [
        {
          id: "querystring",
          httpMethod: "GET",
          title: "GET querystring",
          description:
            "Pass the main document and annex resources as GET parameters. "
            + "Handy for quick one-liners and <code>?compiler=…&url=…</code> "
            + "bookmarklets; better suited to small documents, as everything "
            + "travels in the URL.",
          params: [
            {
              name: "content",
              type: "string",
              required: "one of content / url / file",
              description:
                "Main document, as a (URL-encoded) LaTeX string. "
                + "Values starting with <code>http</code> given without a "
                + "<code>resource-type[]</code> are guessed as URLs.",
            },
            {
              name: "url",
              type: "string (URL)",
              required: "one of content / url / file",
              description:
                "Main document, fetched by the server from this URL.",
            },
            {
              name: "file",
              type: "string (base64)",
              required: "one of content / url / file",
              description: "Main document, base64-encoded.",
            },
            {
              name: "compiler",
              type: "string",
              default: "pdflatex",
              description:
                "One of <code>pdflatex</code>, <code>xelatex</code>, "
                + "<code>lualatex</code>, <code>platex</code>, "
                + "<code>uplatex</code>, <code>context</code>.",
            },
            {
              name: "resource-path[]",
              type: "string (repeatable)",
              description:
                "Path of an annex resource, relative to the main document "
                + "(eg. <code>logo.png</code>, <code>chapters/intro.tex</code>).",
            },
            {
              name: "resource-type[]",
              type: "string (repeatable)",
              default: "guessed",
              description:
                "Type of the matching <code>resource-value[]</code>: "
                + "<code>url</code>, <code>file</code> (base64) or "
                + "<code>content</code> (plain string). "
                + "<code>base64</code> and <code>string</code> are accepted aliases.",
            },
            {
              name: "resource-value[]",
              type: "string (repeatable)",
              description: "Content (URL, base64 data or string) of the matching resource.",
            },
            {
              name: "options.*",
              type: "string",
              description:
                "Dotted build options, eg. <code>options.compiler.shell_escape=true</code>. "
                + "<a href='#options'>See the options reference</a>.",
            },
          ],
          notes:
            "<code>resource-path[]</code>, <code>resource-type[]</code> and "
            + "<code>resource-value[]</code> are positional lists: all entries "
            + "must have the same length. Annex resources (non-main) are "
            + "written server-side under the given <code>resource-path[]</code>.",
          samples: [
            { label: "curl", language: "bash", code: curlGetSample() },
            { label: "HTTPie", language: "bash", code: httpieGetBuildSample() },
            { label: "Python", language: "python", code: pythonGetSample() },
            { label: "PHP", language: "php", code: phpGetBuildSample() },
            { label: "Go", language: "go", code: goGetBuildSample() },
            { label: "Elixir", language: "elixir", code: elixirGetBuildSample() },
            { label: "JavaScript", language: "javascript", code: javascriptGetSample() },
            { label: "ClojureScript", language: "clojure", code: cljsGetBuildSample() },
          ],
        },
        {
          id: "json",
          httpMethod: "POST",
          title: "POST JSON",
          description:
            "The richest input mode: a JSON payload describing the compiler, "
            + "the resources (inline content, base64 files, remote URLs or "
            + "cache hits) and the build options.",
          params: [
            {
              name: "compiler",
              type: "string",
              default: "pdflatex",
              description:
                "One of <code>pdflatex</code>, <code>xelatex</code>, "
                + "<code>lualatex</code>, <code>platex</code>, "
                + "<code>uplatex</code>, <code>context</code>.",
            },
            {
              name: "resources",
              type: "list of objects",
              required: "required",
              description:
                "The files uploaded and compiled. "
                + "<a href='#resources'>See the resource fields</a>: each entry "
                + "takes a <code>main</code> flag, a <code>path</code> and "
                + "exactly one source field (<code>content</code>, "
                + "<code>file</code>, <code>url</code> or <code>cache</code>).",
            },
            {
              name: "options",
              type: "object",
              description:
                "<a href='#options'>Build options</a>, nested "
                + "(<code>options.compiler.…</code>, <code>options.response.…</code>). "
                + "Top-level dotted keys (<code>\"options.compiler.silent\": true</code>) "
                + "are also accepted and merged.",
            },
          ],
          samples: [
            { label: "curl", language: "bash", code: curlJsonSample() },
            { label: "HTTPie", language: "bash", code: httpieJsonBuildSample() },
            { label: "Python", language: "python", code: pythonJsonSample() },
            { label: "PHP", language: "php", code: phpJsonBuildSample() },
            { label: "Go", language: "go", code: goJsonBuildSample() },
            { label: "Elixir", language: "elixir", code: elixirJsonBuildSample() },
            { label: "JavaScript", language: "javascript", code: javascriptJsonSample() },
            { label: "ClojureScript", language: "clojure", code: cljsJsonBuildSample() },
          ],
        },
        {
          id: "multipart",
          httpMethod: "POST",
          title: "POST multipart/form-data",
          description:
            "Send the resources as <code>multipart/form-data</code> parts: "
            + "the natural choice to upload local/binary files (images, "
            + "bibliographies, class files…), with no base64 encoding step.",
          params: [
            {
              name: "compiler",
              type: "string (form field)",
              default: "pdflatex",
              description: "LaTeX compiler to use.",
            },
            {
              name: "options.*",
              type: "string (form fields)",
              description:
                "Dotted build options as form fields, eg. "
                + "<code>options.compiler.halt_on_error=true</code>.",
            },
            {
              name: "resources",
              type: "string (form field, JSON)",
              description:
                "JSON list of resource entries. Each entry maps to an uploaded "
                + "file part with the <code>multipart</code> field (naming the "
                + "form part), plus <code>main</code> and <code>path</code>; "
                + "entries without <code>multipart</code> may still use inline "
                + "<code>content</code>/<code>file</code>/<code>url</code> sources. "
                + "The file content is transferred as binary data.",
            },
            {
              name: "(file parts)",
              type: "binary",
              description:
                "The uploaded files referenced by the <code>multipart</code> "
                + "entries. If no <code>resources</code> form field is given, "
                + "the resources are reconstructed from the uploaded parts: the "
                + "first <code>.tex</code> part is the main document, each part "
                + "is stored under its file name.",
            },
          ],
          notes:
            "Each <code>multipart</code> reference must match an uploaded part "
            + "name, else <code>MISSING_MULTIPART_FILE</code> is returned. A part "
            + "without <code>path</code> in its resource entry is stored under "
            + "its upload file name.",
          samples: [
            { label: "curl", language: "bash", code: curlMultipartSample() },
            { label: "HTTPie", language: "bash", code: httpieMultipartSample() },
            { label: "Python", language: "python", code: pythonMultipartSample() },
            { label: "PHP", language: "php", code: phpMultipartSample() },
            { label: "Go", language: "go", code: goMultipartSample() },
            { label: "Elixir", language: "elixir", code: elixirMultipartSample() },
            { label: "JavaScript", language: "javascript", code: javascriptMultipartSample() },
            { label: "ClojureScript", language: "clojure", code: cljsMultipartSample() },
          ],
        },
      ],
      response: {
        success:
          "<strong>201 Created</strong> with the generated PDF as body "
          + "(<code>Content-Type: application/pdf</code>, "
          + "<code>Content-Disposition: inline</code>, so browsers display it "
          + "instead of downloading it). The response carries an "
          + "<code>X-Job-ID</code> header identifying the compilation job.",
        failure:
          "<strong>400</strong> with a JSON payload describing the failure: "
          + "<code>error</code> (error code), <code>duration</code>, "
          + "<code>logs</code> (compiler output) and, unless disabled, "
          + "<code>log_files</code> (full LaTeX log files). "
          + "Add <code>options.response.commands</code> to get the commands run. "
          + "<strong>429</strong> when the fair-use quota is exceeded "
          + "(<a href='../rate-limiting/'>rate limiting &amp; quotas</a>). "
          + "<strong>503</strong> if the compilation sandbox is unavailable; "
          + "<strong>500</strong> on unexpected server errors.",
      },
    },
    texliveInformation: {
      id: "texlive-information",
      path: "/texlive/information",
      title: "TeXLive installation information",
      summary: "Get information on the TeXLive installation used for the compilations.",
      methods: ["GET"],
      responseDescription:
        "A JSON payload with a TeXLive installation specification "
        + "(<code>version</code>, <code>installation_path</code>, installed "
        + "<code>modules</code>, <code>tlmgr</code> revision).",
      samples: [
        {
          label: "curl",
          language: "bash",
          code: curlGetInfoSample("/texlive/information", true),
        },
        {
          label: "HTTPie",
          language: "bash",
          code: httpieGetSample("/texlive/information"),
        },
        {
          label: "Python",
          language: "python",
          code:
            "import requests\n\n"
            + "information = requests.get(\n"
            + '    "' + BASE_URL + '/texlive/information"\n'
            + ").json()\n"
            + 'print(information["texlive"]["version"])',
        },
        { label: "PHP", language: "php", code: phpGetSample("/texlive/information") },
        { label: "Go", language: "go", code: goGetSample("/texlive/information") },
        { label: "Elixir", language: "elixir", code: elixirGetSample("/texlive/information") },
        {
          label: "JavaScript",
          language: "javascript",
          code:
            "const information = await (\n"
            + '  await fetch("' + BASE_URL + '/texlive/information")\n'
            + ").json();\n"
            + 'console.log(information.texlive.version);',
        },
        { label: "ClojureScript", language: "clojure", code: cljsGetSample("/texlive/information") },
      ],
      sampleResponse: [
        "{",
        '  "texlive": {',
        '    "installation_path": "/usr/local/texlive",',
        '    "modules": [',
        "      {",
        '        "name": "TLConfig",',
        '        "value": "52745"',
        "      },",
        '      ["..."]',
        "    ],",
        '    "version": "2026"',
        "  },",
        '  "tlmgr": {',
        '    "revision": "52931",',
        '    "revision_date": "2019-11-27 00:04:18 +0100"',
        "  }",
        "}",
      ].join("\n"),
    },
    fonts: {
      id: "fonts",
      path: "/fonts",
      title: "List available fonts",
      summary:
        "Explore the fonts that can be used directly in LaTeX compilations "
        + "(system-installed fonts).",
      methods: ["GET"],
      responseDescription: "A JSON payload with a list of fonts.",
      samples: [
        {
          label: "curl",
          language: "bash",
          code: curlGetInfoSample("/fonts", true),
        },
        {
          label: "HTTPie",
          language: "bash",
          code: httpieGetSample("/fonts"),
        },
        {
          label: "Python",
          language: "python",
          code:
            "import requests\n\n"
            + "fonts = requests.get(\n"
            + '    "' + BASE_URL + '/fonts"\n'
            + ").json()\n"
            + "for font in fonts[\"fonts\"]:\n"
            + "    print(font[\"family\"])",
        },
        { label: "PHP", language: "php", code: phpGetSample("/fonts") },
        { label: "Go", language: "go", code: goGetSample("/fonts") },
        { label: "Elixir", language: "elixir", code: elixirGetSample("/fonts") },
        {
          label: "JavaScript",
          language: "javascript",
          code:
            "const fonts = await (\n"
            + '  await fetch("' + BASE_URL + '/fonts")\n'
            + ").json();\n"
            + "for (const font of fonts.fonts) {\n"
            + "  console.log(font.family);\n"
            + "}",
        },
        { label: "ClojureScript", language: "clojure", code: cljsGetSample("/fonts") },
      ],
      sampleResponse: [
        "{",
        '  "fonts": [',
        "    {",
        '      "family": "Amiri",',
        '      "name": "Amiri",',
        '      "styles": [',
        '        "Regular"',
        "      ]",
        "    },",
        '    ["..."]',
        "  ]",
        "}",
      ].join("\n"),
    },
    packages: {
      id: "packages",
      path: "/packages",
      title: "List installed LaTeX packages",
      summary:
        "Explore the LaTeX packages installed on the compilation environment, "
        + "with CTAN links.",
      methods: ["GET"],
      responseDescription:
        "A JSON payload with a list of packages (<code>name</code>, "
        + "<code>shortdesc</code>, <code>installed</code>, "
        + "<code>url_ctan</code>, <code>url_info</code>).",
      samples: [
        {
          label: "curl",
          language: "bash",
          code: curlGetInfoSample("/packages", true),
        },
        {
          label: "HTTPie",
          language: "bash",
          code: httpieGetSample("/packages"),
        },
        {
          label: "Python",
          language: "python",
          code:
            "import requests\n\n"
            + "packages = requests.get(\n"
            + '    "' + BASE_URL + '/packages"\n'
            + ").json()\n"
            + "for package in packages[\"packages\"]:\n"
            + "    if package[\"installed\"]:\n"
            + "        print(package[\"name\"])",
        },
        { label: "PHP", language: "php", code: phpGetSample("/packages") },
        { label: "Go", language: "go", code: goGetSample("/packages") },
        { label: "Elixir", language: "elixir", code: elixirGetSample("/packages") },
        {
          label: "JavaScript",
          language: "javascript",
          code:
            "const packages = await (\n"
            + '  await fetch("' + BASE_URL + '/packages")\n'
            + ").json();\n"
            + "for (const pkg of packages.packages) {\n"
            + "  console.log(pkg.name, pkg.installed);\n"
            + "}",
        },
        { label: "ClojureScript", language: "clojure", code: cljsGetSample("/packages") },
      ],
      sampleResponse: [
        "{",
        '  "packages": [',
        "    {",
        '      "installed": true,',
        '      "name": "12many",',
        '      "shortdesc": "Generalising mathematical index sets",',
        '      "url_ctan": "https://ctan.org/pkg/12many",',
        '      "url_info": "/packages/12many"',
        "    },",
        '    ["..."]',
        "  ]",
        "}",
      ].join("\n"),
    },
    packageDetail: {
      id: "package-detail",
      path: "/packages/<packageName>",
      title: "Get LaTeX package information",
      summary:
        "Get information on a LaTeX package, including whether it is "
        + "installed on the compilation environment.",
      methods: ["GET"],
      responseDescription:
        "A JSON payload with the package information "
        + "(description, category, license, version, sizes, CTAN link).",
      pathParams: [
        {
          name: "packageName",
          type: "string",
          description: "CTAN package name, eg. <code>12many</code>.",
        },
      ],
      samples: [
        {
          label: "curl",
          language: "bash",
          code: curlGetInfoSample("/packages/12many", true),
        },
        {
          label: "HTTPie",
          language: "bash",
          code: httpieGetSample("/packages/12many"),
        },
        {
          label: "Python",
          language: "python",
          code:
            "import requests\n\n"
            + "package = requests.get(\n"
            + '    "' + BASE_URL + '/packages/12many"\n'
            + ").json()\n"
            + "print(package[\"package\"][\"installed\"])",
        },
        { label: "PHP", language: "php", code: phpGetSample("/packages/12many") },
        { label: "Go", language: "go", code: goGetSample("/packages/12many") },
        { label: "Elixir", language: "elixir", code: elixirGetSample("/packages/12many") },
        {
          label: "JavaScript",
          language: "javascript",
          code:
            "const pkg = await (\n"
            + '  await fetch("' + BASE_URL + '/packages/12many")\n'
            + ").json();\n"
            + "console.log(pkg.package.installed);",
        },
        { label: "ClojureScript", language: "clojure", code: cljsGetSample("/packages/12many") },
      ],
      sampleResponse: [
        "{",
        '  "package": {',
        '    "cat-date": [',
        '      "2016-06-24T19:18:15+02:00"',
        "    ],",
        '    "cat-license": "lppl",',
        '    "cat-topics": [',
        '      "maths"',
        "    ],",
        '    "cat-version": "0.3",',
        '    "category": "Package",',
        '    "collection": "collection-mathscience",',
        '    "installed": true,',
        '    "longdesc": "In the discrete branches of mathematics and the computer sciences, it will only take some seconds before you\'re faced with a set like {1,...,m}. [...]",',
        '    "package": "12many",',
        '    "relocatable": false,',
        '    "revision": "15878",',
        '    "shortdesc": "Generalising mathematical index sets",',
        '    "sizes": {',
        '      "run": "5k"',
        "    },",
        '    "url_ctan": "https://ctan.org/pkg/12many"',
        "  }",
        "}",
      ].join("\n"),
      errors: [
        {
          code: "Package not found",
          http: "404",
          description: "No CTAN package with this name.",
        },
      ],
    },
    cachesList: {
      id: "caches-resources",
      path: "/caches/resources",
      title: "Get cache metadata",
      summary:
        "Get a view on the resources cache: size and number of cached "
        + "resources (used to speed up compilations by skipping downloads).",
      methods: ["GET"],
      responseDescription:
        "A JSON payload with cache metadata. Cache entries are filtered "
        + "(only size is returned): their content is not exposed.",
      samples: [
        {
          label: "curl",
          language: "bash",
          code: curlGetInfoSample("/caches/resources", true),
        },
        {
          label: "HTTPie",
          language: "bash",
          code: httpieGetSample("/caches/resources"),
        },
        {
          label: "Python",
          language: "python",
          code:
            "import requests\n\n"
            + "cache = requests.get(\n"
            + '    "' + BASE_URL + '/caches/resources"\n'
            + ").json()\n"
            + "print(cache)",
        },
        { label: "PHP", language: "php", code: phpGetSample("/caches/resources") },
        { label: "Go", language: "go", code: goGetSample("/caches/resources") },
        { label: "Elixir", language: "elixir", code: elixirGetSample("/caches/resources") },
        {
          label: "JavaScript",
          language: "javascript",
          code:
            "const cache = await (\n"
            + '  await fetch("' + BASE_URL + '/caches/resources")\n'
            + ").json();\n"
            + "console.log(cache);",
        },
        { label: "ClojureScript", language: "clojure", code: cljsGetSample("/caches/resources") },
      ],
    },
    cachesReset: {
      id: "caches-reset",
      path: "/caches/resources",
      title: "Reset the cache",
      summary: "Empty the resources cache (eg. to force fresh downloads).",
      methods: ["DELETE"],
      responseDescription: "<strong>204 No Content</strong> on success.",
      samples: [
        {
          label: "curl",
          language: "bash",
          code: "curl -X DELETE " + BASE_URL + "/caches/resources -v",
        },
        {
          label: "HTTPie",
          language: "bash",
          code: httpieDeleteSample("/caches/resources"),
        },
        {
          label: "Python",
          language: "python",
          code:
            "import requests\n\n"
            + "response = requests.delete(\n"
            + '    "' + BASE_URL + '/caches/resources"\n'
            + ")\n"
            + "response.raise_for_status()",
        },
        { label: "PHP", language: "php", code: phpDeleteSample("/caches/resources") },
        { label: "Go", language: "go", code: goDeleteSample("/caches/resources") },
        { label: "Elixir", language: "elixir", code: elixirDeleteSample("/caches/resources") },
        {
          label: "JavaScript",
          language: "javascript",
          code:
            'await fetch("' + BASE_URL + '/caches/resources", {\n'
            + '  method: "DELETE",\n'
            + "});",
        },
        { label: "ClojureScript", language: "clojure", code: cljsDeleteSample("/caches/resources") },
      ],
    },
    cachesCheck: {
      id: "caches-check",
      path: "/caches/resources/check_cached",
      title: "Check cached resources",
      summary:
        "Check, for smart clients, whether resources (identified by their "
        + "content hash) are already in the server cache.",
      methods: ["POST"],
      params: [
        {
          name: "resources",
          type: "list of objects",
          required: "required",
          description:
            "Each entry must have a <code>hash</code> property, formatted as "
            + "<code>sha256:&lt;hexdigest&gt;</code> of the resource content.",
        },
      ],
      responseDescription:
        "A JSON payload mapping each hash to <code>{\"hit\": true|false}</code>.",
      samples: [
        {
          label: "curl",
          language: "bash",
          code: [
            "curl -X POST " + BASE_URL + "/caches/resources/check_cached \\",
            '    -H "Content-Type: application/json" \\',
            "    -d '{",
            '        "resources": [',
            "            {",
            '                "hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"',
            "            }",
            "        ]",
            "    }'",
          ].join("\n"),
        },
        {
          label: "HTTPie",
          language: "bash",
          code: httpieCheckCachedSample(),
        },
        {
          label: "Python",
          language: "python",
          code:
            "import hashlib\n"
            + "import requests\n\n"
            + "content = open(\"logo.png\", \"rb\").read()\n"
            + "resource_hash = \"sha256:{}\".format(hashlib.sha256(content).hexdigest())\n"
            + "response = requests.post(\n"
            + '    "' + BASE_URL + '/caches/resources/check_cached",\n'
            + '    json={"resources": [{"hash": resource_hash}]},\n'
            + ")\n"
            + 'print(response.json()["resources"][resource_hash]["hit"])',
        },
        { label: "PHP", language: "php", code: phpCheckCachedSample() },
        { label: "Go", language: "go", code: goCheckCachedSample() },
        { label: "Elixir", language: "elixir", code: elixirCheckCachedSample() },
        {
          label: "JavaScript",
          language: "javascript",
          code: [
            "// Compute the SHA-256 of the resource bytes,",
            "// eg. with the Web Crypto API:",
            "const data = await file.arrayBuffer();",
            'const digest = await crypto.subtle.digest("SHA-256", data);',
            "const hash = [...new Uint8Array(digest)]",
            '  .map((byte) => byte.toString(16).padStart(2, "0"))',
            '  .join("");',
            "const response = await fetch(",
            '  "' + BASE_URL + '/caches/resources/check_cached",',
            "  {",
            '    method: "POST",',
            '    headers: { "Content-Type": "application/json" },',
            '    body: JSON.stringify({ resources: [{ hash: "sha256:" + hash }] }),',
            "  },",
            ");",
            "const { resources } = await response.json();",
            'console.log(resources["sha256:" + hash].hit);',
          ].join("\n"),
        },
        { label: "ClojureScript", language: "clojure", code: cljsCheckCachedSample() },
      ],
      errors: [
        {
          code: "MISSING_PAYLOAD",
          http: "400",
          description: "No JSON payload in the request.",
        },
        {
          code: "MISSING_RESOURCES",
          http: "400",
          description: "No <code>resources</code> list in the payload.",
        },
        {
          code: "MISSING_RESOURCE_HASH",
          http: "400",
          description: "A resource entry has no <code>hash</code>.",
        },
      ],
    },
  },
};
