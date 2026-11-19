# CHANGELOG

## 2026-11-19-3

* Distribute a documentation site from the service: API reference (endpoints, parameters, code samples for curl/Python/JavaScript/HTTPie), usage guides for server code, CI pipelines and browser integrations (JSON and multipart), and a live in-browser playground to try the endpoints. Built with Node/Eleventy at Docker image build and served from the `/docs/` route; the API index response now points `documentation` to it.

## 2026-11-19-2

* Fix pLaTeX/upLaTeX PDF generation by switching from `dvips` + Ghostscript to `dvipdfmx`. Ghostscript 10's default `SAFER` policy rejected writing the output PDF in the sandbox, causing Japanese documents to fail with `COMPILATION_ERROR`.
* Add `collection-langjapanese` to the base Docker image so the `jsarticle` class, upLaTeX engine, and Japanese fonts are available.

## 2026-11-19-1

* Track synchronous compilation jobs in PostgreSQL with sanitized request metadata, lifecycle status and timestamps, resource/cache metrics, PDF metadata, and `X-Job-ID` responses.
* Add deterministic SHA-256 `compilation_hash` values based on the compiler, effective options, fetched resource paths, and actual contents, independent of transport format or resource order.
* Isolate each compilation process tree with Bubblewrap, one writable workspace, allowed executables, no network, and a scrubbed environment.
* Add opt-in `options.compiler.shell_escape` for `minted`/Pygments; shell escape remains explicitly disabled by default (https://github.com/YtoTech/latex-on-http/issues/25).
* Kill the complete process group on timeout and reject unsafe generated PDF/log symlinks.
* Harden workspace path containment against prefix traversal and symlinked directories.
* Fix ConTeXt compilation under sandboxing by binding the luametatex launcher stubs (`context.lua`, `mtxrun.lua`) and invoking launchers through their real TeX Live bin-directory aliases so the TeX tree configuration is preserved.
* Make resource fetch HTTP timeouts (connect/read) configurable through the `FETCHER_HTTP_REQ_CONNECT_TIMEOUT` and `FETCHER_HTTP_REQ_READ_TIMEOUT` environment variables, and enable the resource fetch timeout test in the test configuration.
* Add an LLM/agent-friendly test setup: `make test-env` / `make test-unit` unit tier in a dedicated `.venv-cline` virtualenv, automatic skip of integration tests when `LATEX_ON_HTTP_API_URL` is unset, and a graceful skip of the real-sandbox test when user namespaces are unavailable (documented in `.cline/skills/testing/SKILL.md` and `DEV.md`).

## 2026-11-18-2

* Add Amiri as a system font for XeLaTeX and the `/fonts` API [#59](https://github.com/YtoTech/latex-on-http/issues/59)

## 2026-11-18-1

* Handle invalid UTF8 bytes / encoding issues in compiler issue
* Return HTTP 400 for invalid Base64 resources instead of HTTP 500
* Return HTTP 400 for non-string `content` resources instead of HTTP 500
* Return HTTP 400 for malformed resource URLs instead of HTTP 500
* Fix cache eviction after Hy update by importing `first` from Toolz
* Reject resources with multiple source fields

## 2026-10-25-3

* Log to Sentry in case of ZMQ socket failure

## 2026-10-25-2

* Add log for Sentry SDK init

## 2026-10-25-1

* Fix function `drop` not defined anymore in Hy ; now import from toolz

## 2026-04-10-3

* Add CHANGELOG link

## 2026-04-10-2

* Option `options.compiler.force` as default to match old behavior

## 2026-04-10-1

* Add `options.compiler.force` to try to fore compilation (Latexmk `-f` option)
and always return the generated PDF
* Remove `options.bibliography.command`, as Latexmk select automatically either `bibtex` or `biber`
* Add `options.compiler.bibliography` to enable or disable automatic Latexmk bibliography compilation step (default to true)
* Add `commands` property on error output when `options.response.commands` is enabled, which detail of each command runned and its outputs

## 2026-03-17-1

* TeXLive 2026 base image

## 2025-09-23-3

* Bump Python dependencies

## 2025-09-23-2

* Kill all children processes on timeout
* Do not return partial PDF on timeout
* Add option `options.compiler.halt_on_error`
* Add option `options.compiler.silent`

## 2025-09-23-1

* Fix timeout for compilation, with proper error return
* Return compilation log files on failure (default true with option `options.response.log_files_on_failure`)

## 2025-08-06-1

* Switch to TexLive 2025
* Use `latexmk` as default runner instead of `latexrun`
* Add PostgreSQL database in prevision of job status

## 2025-02-13-1

* Fix build with XelaTeX [#43](https://github.com/YtoTech/latex-on-http/issues/43)

## 2024-06-28-2

* Run all commands in same directory to simplify path resolution for `filecontents` and uploaded resources

## 2024-06-28-1

* Set `cwd` for latexrun.py so the `filecontents` directives can work as expected #42

## 2023-06-12-1

* Timeout long LaTeX compilations and prevent zombie processes (the timeout is of 100 seconds for now)

## 2022-12-07-1

* Add clearer input spec (payload) validation

## 2022-08-03-1

* Add ghostscript runtime to the base Docker image

## 2022-07-31-1

* Make sync cache socket more reliable with lazy pirate pattern (prevent dead-lock on server crash)

## 2022-07-30-4

* Fix missing import on `app_cache.py`

## 2022-07-30-1

* Fix caching API

## 2022-05-23-1

* Fix Sentry Flask integration import

## 2022-05-17-3

* Add an environment variable `SENTRY_DSN` for Sentry tracking

## 2022-05-17-2

* Forget Alpine as Context seems [not to run](https://mailman.ntg.nl/pipermail/ntg-context/2021/101979.html) on it, keep to Debian

## 2022-05-17-1

* Use Alpine as default base image

## 2022-05-16-2

* Fix some Hy implementations after `1.0a4` bump 

## 2022-05-16-1

* Update Hy to `1.0a4`, as a consequence LaTeX-on-HTTP now require Python 3.7+
