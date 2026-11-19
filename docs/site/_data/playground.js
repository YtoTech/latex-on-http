/**
 * Playground configuration, injected into the playground page and read by
 * assets/js/playground.js.
 */
export default {
  compilers: ["pdflatex", "xelatex", "lualatex", "platex", "uplatex", "context"],
  // Default main document for the playground.
  sampleDocument: [
    "\\documentclass{article}",
    "\\usepackage{graphicx}",
    "\\begin{document}",
    "Hello World from \\LaTeX{}-On-HTTP!",
    "",
    "\\includegraphics[height=2cm,width=7cm,keepaspectratio=true]{logo.png}",
    "\\end{document}",
  ].join("\n"),
  // Build options exposed as checkboxes in the playground,
  // with their default value.
  options: [
    { key: "options.compiler.bibliography", label: "compiler.bibliography", default: true },
    { key: "options.compiler.halt_on_error", label: "compiler.halt_on_error", default: false },
    { key: "options.compiler.silent", label: "compiler.silent", default: false },
    { key: "options.compiler.force", label: "compiler.force", default: true },
    { key: "options.compiler.shell_escape", label: "compiler.shell_escape", default: false },
    { key: "options.response.log_files_on_failure", label: "response.log_files_on_failure", default: true },
    { key: "options.response.commands", label: "response.commands", default: false },
  ],
  // Endpoints that can be fired as-is from the playground.
  simpleEndpoints: [
    { id: "texlive", label: "TeXLive info", method: "GET", path: "/texlive/information" },
    { id: "fonts", label: "Fonts", method: "GET", path: "/fonts" },
    { id: "packages", label: "Packages", method: "GET", path: "/packages" },
    {
      id: "package-detail",
      label: "Package details",
      method: "GET",
      path: "/packages/",
      pathParam: { name: "packageName", placeholder: "12many" },
    },
    { id: "caches", label: "Cache metadata", method: "GET", path: "/caches/resources" },
    {
      id: "caches-check",
      label: "Check cached",
      method: "POST",
      path: "/caches/resources/check_cached",
      body: '{\n  "resources": [\n    { "hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08" }\n  ]\n}',
    },
    { id: "caches-reset", label: "Reset cache", method: "DELETE", path: "/caches/resources" },
  ],
};
