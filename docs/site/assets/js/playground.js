/**
 * LaTeX-on-HTTP documentation — live playground.
 * Vanilla JS, no dependencies. Talks directly to the API (CORS-enabled).
 */
(function () {
  "use strict";

  const config = JSON.parse(
    document.getElementById("pg-config").textContent
  );

  const STORAGE_KEY = "loh-playground-state";
  const FALLBACK_BASE_URL = "https://latex.ytotech.com";

  const elements = {
    baseUrl: document.getElementById("pg-base-url"),
    endpoint: document.getElementById("pg-endpoint"),
    compiler: document.getElementById("pg-compiler"),
    mainDocument: document.getElementById("pg-main-document"),
    resources: document.getElementById("pg-resources"),
    resourcesHint: document.getElementById("pg-resources-hint"),
    addResource: document.getElementById("pg-add-resource"),
    buildFields: document.getElementById("pg-build-fields"),
    simpleFields: document.getElementById("pg-simple-fields"),
    pathParamField: document.getElementById("pg-path-param-field"),
    pathParam: document.getElementById("pg-path-param"),
    bodyField: document.getElementById("pg-body-field"),
    body: document.getElementById("pg-body"),
    run: document.getElementById("pg-run"),
    copyCurl: document.getElementById("pg-copy-curl"),
    copyPython: document.getElementById("pg-copy-python"),
    copyJavascript: document.getElementById("pg-copy-javascript"),
    requestHint: document.getElementById("pg-request-hint"),
    statusLine: document.getElementById("pg-status-line"),
    statusBadge: document.getElementById("pg-status-badge"),
    statusDetail: document.getElementById("pg-status-detail"),
    networkError: document.getElementById("pg-network-error"),
    pdfFrame: document.getElementById("pg-pdf-frame"),
    pdfEmpty: document.getElementById("pg-pdf-empty"),
    responseBody: document.getElementById("pg-response-body"),
    responseTabs: document.querySelectorAll("[data-response-tab]"),
    responsePanels: document.querySelectorAll("[data-response-panel]"),
  };

  const optionInputs = Array.prototype.slice.call(
    document.querySelectorAll("input[data-option-key]")
  );

  const state = {
    resources: [], // { path, type: url|content|file, value, file: File|null }
    pdfUrl: null,
  };

  /* ------------------------------ Helpers ------------------------------- */

  function normalizedBaseUrl() {
    return (elements.baseUrl.value || "").trim().replace(/\/+$/, "");
  }

  function buildsSyncUrl() {
    return normalizedBaseUrl() + "/builds/sync";
  }

  function selectedOptions() {
    const options = {};
    for (const input of optionInputs) {
      options[input.dataset.optionKey] = input.checked;
    }
    return options;
  }

  // Nested options object expected in the JSON payload:
  // {"compiler": {"bibliography": true, ...}, "response": {"commands": false, ...}}
  function nestedOptions() {
    const options = {};
    for (const input of optionInputs) {
      // Checkbox keys are dotted, eg. "options.compiler.bibliography":
      // assign "compiler.bibliography" inside the options object.
      const parts = input.dataset.optionKey.split(".").slice(1);
      let target = options;
      for (let index = 0; index < parts.length - 1; index += 1) {
        if (
          typeof target[parts[index]] !== "object" ||
          target[parts[index]] === null
        ) {
          target[parts[index]] = {};
        }
        target = target[parts[index]];
      }
      target[parts[parts.length - 1]] = input.checked;
    }
    return options;
  }

  function optionQueryStringEntries() {
    const entries = [];
    for (const input of optionInputs) {
      entries.push(
        encodeURIComponent(input.dataset.optionKey) +
          "=" +
          encodeURIComponent(input.checked ? "true" : "false")
      );
    }
    return entries;
  }

  async function fileToBase64(file) {
    const buffer = await file.arrayBuffer();
    let binary = "";
    const bytes = new Uint8Array(buffer);
    const chunkSize = 0x8000;
    for (let offset = 0; offset < bytes.length; offset += chunkSize) {
      binary += String.fromCharCode.apply(
        null,
        bytes.subarray(offset, offset + chunkSize)
      );
    }
    return btoa(binary);
  }

  function sanitizeMultipartName(path) {
    const safe = (path || "resource").replace(/[^a-zA-Z0-9._-]/g, "_");
    return "part-" + safe;
  }

  function escapeShellSingleQuoted(text) {
    return text.replace(/'/g, "'\\''");
  }

  function jsonPretty(value) {
    return JSON.stringify(value, null, 4);
  }

  /* --------------------------- Resource rows ----------------------------- */

  function createResourceRow(resource) {
    const row = document.createElement("div");
    row.className = "pg-resource";

    const typeSelect = document.createElement("select");
    typeSelect.className = "pg-select";
    typeSelect.title = "Resource source type";
    for (const [value, label] of [
      ["url", "url"],
      ["content", "content"],
      ["file", "file"],
    ]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      typeSelect.appendChild(option);
    }

    const pathInput = document.createElement("input");
    pathInput.className = "pg-input";
    pathInput.placeholder = "path (eg. logo.png)";
    pathInput.spellcheck = false;
    pathInput.value = resource.path || "";
    pathInput.addEventListener("input", function () {
      resource.path = pathInput.value;
      persistState();
    });

    const valueTextarea = document.createElement("textarea");
    valueTextarea.className = "pg-textarea";
    valueTextarea.style.minHeight = "64px";
    valueTextarea.spellcheck = false;
    valueTextarea.placeholder =
      "value (URL or inline content; base64 for files)";
    valueTextarea.value = resource.value || "";
    valueTextarea.addEventListener("input", function () {
      resource.value = valueTextarea.value;
      persistState();
    });

    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.className = "pg-input";
    fileInput.hidden = true;
    fileInput.addEventListener("change", function () {
      const file = fileInput.files && fileInput.files[0];
      if (file) {
        resource.file = file;
        if (!pathInput.value) {
          pathInput.value = file.name;
          resource.path = file.name;
        }
      } else {
        resource.file = null;
      }
      persistState();
    });

    typeSelect.value = resource.type || "url";
    if (typeSelect.selectedIndex < 0) {
      typeSelect.selectedIndex = 0;
    }
    function syncTypeView() {
      resource.type = typeSelect.value;
      const isFile = resource.type === "file";
      fileInput.hidden = !isFile;
      valueTextarea.hidden = isFile;
      persistState();
    }
    typeSelect.addEventListener("change", syncTypeView);

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "pg-remove";
    removeButton.title = "Remove resource";
    removeButton.textContent = "×";
    removeButton.addEventListener("click", function () {
      const index = state.resources.indexOf(resource);
      if (index >= 0) {
        state.resources.splice(index, 1);
      }
      row.remove();
      persistState();
    });

    row.appendChild(pathInput);
    row.appendChild(typeSelect);
    row.appendChild(removeButton);

    const valueWrapper = document.createElement("div");
    valueWrapper.className = "pg-resource-value";
    valueWrapper.appendChild(valueTextarea);
    valueWrapper.appendChild(fileInput);
    row.appendChild(valueWrapper);

    syncTypeView();
    return row;
  }

  function addResourceRow(resource) {
    state.resources.push(resource);
    elements.resources.appendChild(createResourceRow(resource));
    persistState();
  }

  /* -------------------------- View switching ----------------------------- */

  function currentEndpointId() {
    return elements.endpoint.value;
  }

  function syncEndpointView() {
    const endpointId = currentEndpointId();
    const isBuild = endpointId.startsWith("builds-");
    elements.buildFields.hidden = !isBuild;
    elements.simpleFields.hidden = isBuild;

    const simpleId = endpointId.replace("simple:", "");
    const simpleEndpoint = config.simpleEndpoints.find(function (endpoint) {
      return endpoint.id === simpleId;
    });
    elements.pathParamField.hidden = !(simpleEndpoint && simpleEndpoint.pathParam);
    elements.bodyField.hidden = !(simpleEndpoint && simpleEndpoint.body);
    if (simpleEndpoint && simpleEndpoint.body && !elements.body.value) {
      elements.body.value = simpleEndpoint.body;
    }

    const hints = {
      "builds-get":
        "Resources travel as resource-path[] / resource-type[] / resource-value[] query parameters. Better suited to small documents.",
      "builds-json":
        "Each resource is embedded in the JSON payload; file resources are base64-encoded by the playground.",
      "builds-multipart":
        "File resources are uploaded as binary multipart parts and referenced by name in the resources JSON.",
    };
    elements.requestHint.textContent = hints[endpointId] || "";
    persistState();
  }

  function selectResponseTab(tabName) {
    elements.responseTabs.forEach(function (tab) {
      tab.classList.toggle("is-active", tab.dataset.responseTab === tabName);
      tab.setAttribute(
        "aria-selected",
        String(tab.dataset.responseTab === tabName)
      );
    });
    elements.responsePanels.forEach(function (panel) {
      panel.hidden = panel.dataset.responsePanel !== tabName;
    });
  }

  /* ---------------------------- Persistence ------------------------------ */

  function persistState() {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          baseUrl: elements.baseUrl.value,
          endpointId: currentEndpointId(),
          compiler: elements.compiler.value,
          options: optionInputs.map(function (input) {
            return input.checked;
          }),
          mainDocument: elements.mainDocument.value,
          resources: state.resources.map(function (resource) {
            return {
              path: resource.path,
              type: resource.type,
              value: resource.value,
            };
          }),
          pathParam: elements.pathParam.value,
          body: elements.body.value,
        })
      );
    } catch (error) {
      /* Storage unavailable: keep working without persistence. */
    }
  }

  function restoreState() {
    let saved = null;
    try {
      saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "null");
    } catch (error) {
      saved = null;
    }
    if (!saved) {
      return false;
    }
    if (saved.baseUrl) {
      elements.baseUrl.value = saved.baseUrl;
    }
    if (saved.endpointId) {
      const hasOption = Array.prototype.some.call(
        elements.endpoint.options,
        function (option) {
          return option.value === saved.endpointId;
        }
      );
      if (hasOption) {
        elements.endpoint.value = saved.endpointId;
      }
    }
    if (saved.compiler && config.compilers.includes(saved.compiler)) {
      elements.compiler.value = saved.compiler;
    }
    if (Array.isArray(saved.options)) {
      optionInputs.forEach(function (input, index) {
        if (typeof saved.options[index] === "boolean") {
          input.checked = saved.options[index];
        }
      });
    }
    if (typeof saved.mainDocument === "string") {
      elements.mainDocument.value = saved.mainDocument;
    }
    if (Array.isArray(saved.resources)) {
      state.resources = saved.resources.map(function (resource) {
        return {
          path: resource.path || "",
          type: resource.type || "url",
          value: resource.value || "",
          file: null,
        };
      });
      state.resources.forEach(function (resource) {
        elements.resources.appendChild(createResourceRow(resource));
      });
    }
    if (typeof saved.pathParam === "string") {
      elements.pathParam.value = saved.pathParam;
    }
    if (typeof saved.body === "string") {
      elements.body.value = saved.body;
    }
    return true;
  }

  /* --------------------------- Request building -------------------------- */

  // Returns { url, init, summary } for the current playground state.
  async function buildRequest() {
    const endpointId = currentEndpointId();

    if (endpointId.startsWith("simple:")) {
      const simpleId = endpointId.replace("simple:", "");
      const simpleEndpoint = config.simpleEndpoints.find(function (endpoint) {
        return endpoint.id === simpleId;
      });
      let path = simpleEndpoint.path;
      if (simpleEndpoint.pathParam) {
        path += encodeURIComponent(elements.pathParam.value.trim());
      }
      const init = { method: simpleEndpoint.method };
      if (simpleEndpoint.method === "POST") {
        init.headers = { "Content-Type": "application/json" };
        init.body = elements.body.value;
      }
      return {
        url: normalizedBaseUrl() + path,
        init: init,
        summary: simpleEndpoint.method + " " + path,
      };
    }

    const compiler = elements.compiler.value;
    const mainDocument = elements.mainDocument.value;
    const options = selectedOptions();

    if (endpointId === "builds-get") {
      const params = new URLSearchParams();
      params.append("compiler", compiler);
      params.append("content", mainDocument);
      for (const resource of state.resources) {
        let value = resource.value;
        if (resource.type === "file") {
          value = resource.file ? await fileToBase64(resource.file) : "";
        }
        params.append("resource-path[]", resource.path || "");
        params.append("resource-type[]", resource.type);
        params.append("resource-value[]", value);
      }
      const query = params.toString() + (optionQueryStringEntries().length
        ? "&" + optionQueryStringEntries().join("&")
        : "");
      return {
        url: buildsSyncUrl() + "?" + query,
        init: { method: "GET" },
        summary: "GET /builds/sync (querystring)",
      };
    }

    if (endpointId === "builds-json") {
      const resources = [{ main: true, content: mainDocument }];
      for (const resource of state.resources) {
        const entry = { path: resource.path || "" };
        if (resource.type === "url") {
          entry.url = resource.value;
        } else if (resource.type === "content") {
          entry.content = resource.value;
        } else {
          entry.file = resource.file ? await fileToBase64(resource.file) : "";
        }
        resources.push(entry);
      }
      const payload = {
        compiler: compiler,
        resources: resources,
        options: nestedOptions(),
      };
      return {
        url: buildsSyncUrl(),
        init: {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
        summary: "POST /builds/sync (JSON)",
        payload: payload,
      };
    }

    // builds-multipart
    const formData = new FormData();
    formData.append("compiler", compiler);
    for (const [key, value] of Object.entries(options)) {
      formData.append(key, value ? "true" : "false");
    }
    const resources = [];
    // Main document as a multipart part.
    formData.append(
      "main",
      new File([mainDocument], "main.tex", { type: "application/x-tex" }),
      "main.tex"
    );
    resources.push({ main: true, multipart: "main" });
    let partIndex = 0;
    for (const resource of state.resources) {
      if (resource.type === "file") {
        if (!resource.file) {
          continue;
        }
        partIndex += 1;
        const partName = "res" + partIndex;
        formData.append(partName, resource.file, resource.path || resource.file.name);
        resources.push({
          path: resource.path || resource.file.name,
          multipart: partName,
        });
      } else {
        const entry = { path: resource.path || "" };
        if (resource.type === "url") {
          entry.url = resource.value;
        } else {
          entry.content = resource.value;
        }
        resources.push(entry);
      }
    }
    formData.append("resources", JSON.stringify(resources));
    return {
      url: buildsSyncUrl(),
      init: { method: "POST", body: formData },
      summary: "POST /builds/sync (multipart)",
      resources: resources,
    };
  }

  /* --------------------------- Snippet builders -------------------------- */

  function curlSnippetForState(request, payload, resources) {
    const endpointId = currentEndpointId();
    if (endpointId === "builds-get") {
      const url = new URL(request.url);
      const lines = ["curl -G '" + url.origin + url.pathname + "' \\"];
      url.searchParams.forEach(function (value, key) {
        lines.push(
          "    --data-urlencode '" +
            key +
            "=" +
            escapeShellSingleQuoted(value) +
            "' \\"
        );
      });
      lines.push("    --output document.pdf");
      return lines.join("\n");
    }
    if (endpointId === "builds-json") {
      return [
        "curl -X POST '" + request.url + "' \\",
        '    -H "Content-Type: application/json" \\',
        "    -d '" + escapeShellSingleQuoted(jsonPretty(payload)) + "' \\",
        "    --output document.pdf",
      ].join("\n");
    }
    if (endpointId === "builds-multipart") {
      const lines = ["curl -X POST '" + request.url + "' \\"];
      const formDataEntries = Array.from(
        /** @type {FormData} */ (request.init.body)
      );
      for (const [name, value] of formDataEntries) {
        if (value instanceof File) {
          lines.push(
            "    -F '" + name + "=@" + (value.name || name) + "' \\"
          );
        } else {
          lines.push(
            "    -F '" + name + "=" + escapeShellSingleQuoted(value) + "' \\"
          );
        }
      }
      lines.push("    --output document.pdf");
      return lines.join("\n");
    }
    const init = request.init || {};
    const lines = ["curl -X " + (init.method || "GET") + " '" + request.url + "' \\"];
    if (init.headers) {
      for (const [header, value] of Object.entries(init.headers)) {
        lines.push('    -H "' + header + ": " + value + '" \\');
      }
    }
    if (init.body) {
      lines.push("    -d '" + escapeShellSingleQuoted(init.body) + "'");
    } else {
      const last = lines.pop();
      lines.push(last.replace(/ \\$/, ""));
    }
    return lines.join("\n");
  }

  function pythonSnippetForState(request, payload) {
    const endpointId = currentEndpointId();
    if (endpointId.startsWith("simple:")) {
      const init = request.init || {};
      const method = (init.method || "GET").toLowerCase();
      const args = ['"' + request.url + '"'];
      if (init.body) {
        args.push(
          '    data=' + JSON.stringify(init.body),
          '    headers={"Content-Type": "application/json"}'
        );
      }
      return [
        "import requests",
        "",
        "response = requests." + method + "(",
        "    " + args.join(",\n    ") + ",",
        "    timeout=30,",
        ")",
        "print(response.status_code)",
        "print(response.text)",
      ].join("\n");
    }
    if (endpointId === "builds-get") {
      const url = new URL(request.url);
      const params = {};
      url.searchParams.forEach(function (value, key) {
        if (key in params) {
          if (!Array.isArray(params[key])) {
            params[key] = [params[key]];
          }
          params[key].push(value);
        } else {
          params[key] = value;
        }
      });
      return [
        "import requests",
        "",
        "response = requests.get(",
        '    "' + url.origin + url.pathname + '",',
        "    params=" + pythonLiteral(params, 1) + ",",
        "    timeout=120,",
        ")",
        "response.raise_for_status()",
        'with open("document.pdf", "wb") as pdf_file:',
        "    pdf_file.write(response.content)",
      ].join("\n");
    }
    if (endpointId === "builds-json") {
      return [
        "import requests",
        "",
        "payload = " + pythonLiteral(payload, 0),
        "response = requests.post(",
        '    "' + request.url + '",',
        "    json=payload,",
        "    timeout=120,",
        ")",
        "response.raise_for_status()",
        'with open("document.pdf", "wb") as pdf_file:',
        "    pdf_file.write(response.content)",
      ].join("\n");
    }
    // builds-multipart
    const formData = /** @type {FormData} */ (request.init.body);
    const fileEntries = Array.from(formData).filter(function (entry) {
      return entry[1] instanceof File;
    });
    const inlineEntries = Array.from(formData).filter(function (entry) {
      return !(entry[1] instanceof File);
    });
    const lines = ["import json", "import requests", ""];
    if (request.resources) {
      lines.push("resources = " + pythonLiteral(request.resources, 0), "");
    }
    lines.push("# Inline form entries.");
    lines.push("data = {");
    for (const [name, value] of inlineEntries) {
      lines.push(
        '    "' +
          name +
          '": ' +
          (name === "resources"
            ? "json.dumps(resources)"
            : JSON.stringify(value)) +
          ","
      );
    }
    lines.push("}", "");
    lines.push("# File parts: (part name, (file name, file object)).");
    lines.push("files = [");
    for (const [name, file] of fileEntries) {
      lines.push(
        '    ("' +
          name +
          '", ("' +
          (file.name || name) +
          '", open("' +
          (file.name || name) +
          '", "rb"))),'
      );
    }
    lines.push("]", "");
    lines.push("response = requests.post(");
    lines.push('    "' + request.url + '",');
    lines.push("    data=data,");
    lines.push("    files=files,");
    lines.push("    timeout=120,");
    lines.push(")");
    lines.push("response.raise_for_status()");
    lines.push('with open("document.pdf", "wb") as pdf_file:');
    lines.push("    pdf_file.write(response.content)");
    return lines.join("\n");
  }

  // JSON -> Python literal (True/False/None, indentation kept simple).
  function pythonLiteral(value, indent) {
    const pad = "    ".repeat(indent);
    if (value === null) {
      return "None";
    }
    if (typeof value === "boolean") {
      return value ? "True" : "False";
    }
    if (typeof value === "number") {
      return String(value);
    }
    if (typeof value === "string") {
      return JSON.stringify(value);
    }
    if (Array.isArray(value)) {
      if (value.length === 0) {
        return "[]";
      }
      const inner = value
        .map(function (item) {
          return pad + "    " + pythonLiteral(item, indent + 1);
        })
        .join(",\n");
      return "[\n" + inner + ",\n" + pad + "]";
    }
    const keys = Object.keys(value);
    if (keys.length === 0) {
      return "{}";
    }
    const inner = keys
      .map(function (key) {
        return (
          pad +
          "    " +
          JSON.stringify(key) +
          ": " +
          pythonLiteral(value[key], indent + 1)
        );
      })
      .join(",\n");
    return "{\n" + inner + ",\n" + pad + "}";
  }

  function javascriptSnippetForState(request, payload) {
    const endpointId = currentEndpointId();
    if (endpointId === "builds-json") {
      return [
        "const response = await fetch(\"" + request.url + "\", {",
        '  method: "POST",',
        '  headers: { "Content-Type": "application/json" },',
        "  body: JSON.stringify(" + jsonPretty(payload) + "),",
        "});",
        "if (!response.ok) {",
        "  const error = await response.json();",
        '  console.error(`Compilation failed: ${error.error}`, error.logs);',
        "} else {",
        "  const pdfBlob = await response.blob();",
        "}",
      ].join("\n");
    }
    if (endpointId === "builds-multipart") {
      return [
        "const formData = new FormData();",
        "// See the multipart guide for building the resources specification",
        "// and appending the File objects:",
        "const response = await fetch(\"" + request.url + "\", {",
        '  method: "POST",',
        "  body: formData,",
        "});",
      ].join("\n");
    }
    if (endpointId === "builds-get") {
      return [
        'const response = await fetch("' + request.url + '");',
        "if (!response.ok) {",
        "  const error = await response.json();",
        '  console.error(`Compilation failed: ${error.error}`, error.logs);',
        "} else {",
        "  const pdfBlob = await response.blob();",
        "}",
      ].join("\n");
    }
    const init = request.init || {};
    return [
      'const response = await fetch("' + request.url + '", ' + JSON.stringify({
        method: init.method || "GET",
        headers: init.headers || undefined,
        body: init.body || undefined,
      }, null, 2) + ");",
      "console.log(await response.text());",
    ].join("\n");
  }

  /* --------------------------- Response display -------------------------- */

  function showStatus(statusCode, duration, jobId) {
    elements.statusLine.hidden = false;
    elements.statusBadge.textContent = "HTTP " + statusCode;
    elements.statusBadge.classList.toggle(
      "pg-status-ok",
      statusCode >= 200 && statusCode < 300
    );
    elements.statusBadge.classList.toggle(
      "pg-status-error",
      !(statusCode >= 200 && statusCode < 300)
    );
    const details = [];
    details.push(duration + " ms");
    if (jobId) {
      details.push("X-Job-ID: " + jobId);
    }
    elements.statusDetail.textContent = details.join(" · ");
  }

  function showPdf(blob) {
    if (state.pdfUrl) {
      URL.revokeObjectURL(state.pdfUrl);
    }
    state.pdfUrl = URL.createObjectURL(blob);
    elements.pdfFrame.src = state.pdfUrl;
    elements.pdfFrame.hidden = false;
    elements.pdfEmpty.hidden = true;
    selectResponseTab("pdf");
  }

  function highlightJson(text) {
    const escaped = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    return escaped.replace(
      /("(?:[^"\\]|\\.)*")(\s*:)?|\b(true|false|null)\b|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g,
      function (match, string, colon, keyword, number) {
        if (string) {
          return (
            '<span class="json-string">' + string + "</span>" +
            (colon ? '<span class="json-key">' + colon + "</span>" : "")
          );
        }
        if (keyword) {
          return '<span class="json-' + keyword + '">' + keyword + "</span>";
        }
        if (number) {
          return '<span class="json-number">' + number + "</span>";
        }
        return match;
      }
    );
  }

  function showBody(text, contentType) {
    elements.pdfFrame.hidden = true;
    elements.pdfEmpty.hidden = false;
    let html;
    if ((contentType || "").includes("json")) {
      try {
        html = highlightJson(JSON.stringify(JSON.parse(text), null, 2));
      } catch (error) {
        html = highlightJson(text);
      }
    } else {
      html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    }
    elements.responseBody.innerHTML = html;
    selectResponseTab("body");
  }

  function showNetworkError(error) {
    elements.networkError.hidden = false;
    elements.networkError.textContent =
      "Request failed: " +
      (error && error.message ? error.message : String(error)) +
      ". Check the API base URL and that the service is reachable (CORS is enabled server-side).";
  }

  /* ------------------------------- Actions ------------------------------- */

  async function runRequest() {
    elements.networkError.hidden = true;
    if (currentEndpointId() === "simple:caches-reset" &&
        !window.confirm("This empties the resources cache of the target instance. Continue?")) {
      return;
    }
    elements.run.disabled = true;
    elements.run.textContent = "Running…";
    try {
      const request = await buildRequest();
      const startedAt = performance.now();
      let response;
      try {
        response = await fetch(request.url, request.init);
      } catch (networkError) {
        showNetworkError(networkError);
        return;
      }
      const duration = Math.round(performance.now() - startedAt);
      showStatus(
        response.status,
        duration,
        response.headers.get("X-Job-ID")
      );
      const contentType = response.headers.get("Content-Type") || "";
      if (response.ok && contentType.includes("application/pdf")) {
        showPdf(await response.blob());
      } else {
        showBody(await response.text(), contentType);
      }
    } finally {
      elements.run.disabled = false;
      elements.run.textContent = "Run request";
      persistState();
    }
  }

  async function copySnippet(kind) {
    const request = await buildRequest();
    let snippet;
    if (kind === "curl") {
      snippet = curlSnippetForState(
        request,
        request.payload,
        request.resources
      );
    } else if (kind === "python") {
      snippet = pythonSnippetForState(request, request.payload);
    } else {
      snippet = javascriptSnippetForState(request, request.payload);
    }
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(snippet);
    } else {
      const area = document.createElement("textarea");
      area.value = snippet;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      try {
        document.execCommand("copy");
      } finally {
        document.body.removeChild(area);
      }
    }
  }

  function flashCopied(button) {
    const original = button.textContent;
    button.textContent = "Copied!";
    window.setTimeout(function () {
      button.textContent = original;
    }, 1400);
  }

  /* -------------------------------- Init --------------------------------- */

  if (window.location.protocol === "http:" || window.location.protocol === "https:") {
    elements.baseUrl.placeholder = window.location.origin;
  } else {
    elements.baseUrl.placeholder = FALLBACK_BASE_URL;
  }

  // Server-side defaults for the build options.
  optionInputs.forEach(function (input) {
    input.checked = input.dataset.optionDefault === "true";
  });

  const restored = restoreState();
  if (!elements.baseUrl.value) {
    // Default to the same origin when served by the service itself,
    // and to the public instance when the site is browsed standalone.
    elements.baseUrl.value =
      window.location.protocol === "http:" || window.location.protocol === "https:"
        ? window.location.origin
        : FALLBACK_BASE_URL;
  }
  if (!restored) {
    // Server-side defaults: sample document and one annex resource.
    elements.mainDocument.value = config.sampleDocument;
    addResourceRow({
      path: "logo.png",
      type: "url",
      value: "https://www.ytotech.com/images/ytotech_logo.png",
      file: null,
    });
  }
  syncEndpointView();

  elements.endpoint.addEventListener("change", syncEndpointView);
  elements.compiler.addEventListener("change", persistState);
  optionInputs.forEach(function (input) {
    input.addEventListener("change", persistState);
  });
  elements.mainDocument.addEventListener("input", persistState);
  elements.baseUrl.addEventListener("change", persistState);
  elements.pathParam.addEventListener("input", persistState);
  elements.body.addEventListener("input", persistState);

  elements.addResource.addEventListener("click", function () {
    addResourceRow({ path: "", type: "url", value: "", file: null });
  });

  elements.responseTabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      selectResponseTab(tab.dataset.responseTab);
    });
  });

  elements.run.addEventListener("click", runRequest);
  document.addEventListener("keydown", function (event) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      runRequest();
    }
  });

  elements.copyCurl.addEventListener("click", function () {
    copySnippet("curl").then(function () {
      flashCopied(elements.copyCurl);
    });
  });
  elements.copyPython.addEventListener("click", function () {
    copySnippet("python").then(function () {
      flashCopied(elements.copyPython);
    });
  });
  elements.copyJavascript.addEventListener("click", function () {
    copySnippet("javascript").then(function () {
      flashCopied(elements.copyJavascript);
    });
  });
})();
