# CHANGELOG

## 2026-11-25-1

* Upgrade Gunicorn from 26.2.0 to 27.0.1: an invalid response header now answers `500 Internal Server Error` instead of dropping the connection with no reply (and the header value is kept out of the error log), request bodies of known length are read in large steps so large multipart uploads are much faster while other threads keep the worker busy, and gthread keep-alive fixes serve requests arriving while a previous body is drained and keep client connections usable across worker recycling/shutdown.
* Fix a server error on `/builds/sync` under concurrent requests (GlitchTip #11969): the endpoint validated the input spec with a single module-level `cerberus.Validator`, but Cerberus validator instances keep per-validation state on the instance (document, schema, remaining rules), so requests handled by different threads of the same gunicorn worker clobbered each other's state mid-validation, producing `500` crashes (`IndexError: pop from empty list` inside Cerberus) or the wrong `INVALID_PAYLOAD_SHAPE` verdict from another request's spec. The endpoint now builds a fresh validator per request, pinned by a concurrency unit test.
* Return `400 MISSING_COMPILATION_SPECIFICATION` for an empty or missing `resources` list (e.g. a browser navigating to `/builds/sync` with no parameters) instead of letting the request proceed into the compilation pipeline and crash with a `500`.
* Fix a server error when the compilation output filename contains non-ASCII characters (e.g. an uploaded `Lab02-肖奕然.tex`): the `Content-Disposition` header echoed the raw filename, while HTTP header values must stay printable ASCII (RFC 9110), so Gunicorn rejected the whole response with `InvalidHeader` after a successful compilation — the client received no reply at all while the job was recorded as completed. The header is now built to be RFC 6266-compliant: quoted and escaped for ASCII filenames, percent-encoded with an RFC 5987 `filename*=UTF-8''` parameter for non-ASCII ones (with the percent-encoded form as `filename` fallback), control characters neutralized and directory prefixes dropped.
* Fix a Server-Side Request Forgery (SSRF) in the `url` resource fetcher: user-supplied URLs were fetched with no validation, letting an unauthenticated client make the application read internal services, loopback, or cloud instance metadata (`169.254.169.254`). The new `latexonhttp/resources/urlguard.py` validates the scheme and host, resolves the address and rejects loopback/private/link-local/reserved/multicast/unspecified and any non-globally-routable address (including CGNAT and IPv4-mapped IPv6), pins the connection to a validated address to defeat DNS rebinding, and re-validates every redirect hop (bounded). URLs that would reach an internal address return `400 RESOURCE_FETCH_FAILURE` with `fetch_error.type = "ssrf_blocked"` and a machine-readable `reason`; URLs that simply cannot be fetched (missing or unsupported scheme, missing host, or an invalid port) return the same `400 RESOURCE_FETCH_FAILURE` with `fetch_error.type = "invalid_url"`, a `reason`, and the `allowed_schemes`, so a typo such as a missing scheme is reported clearly instead of as an SSRF block. Schemes are restricted to `http,https` by default (`FETCHER_ALLOWED_SCHEMES`) and redirects to `FETCHER_MAX_REDIRECTS` (default 3).
* Log every quota enforcement event for operators: rate-limit denials and ban re-arms at `INFO` (re-arms were `DEBUG`-only and now have a dedicated `re-armed` message), new and escalated bans at `WARNING`; the log lines are pinned by unit tests and their levels documented in the rate-limiting guide.
* Persist quota ban decisions in PostgreSQL (`quota_bans`): one row per ban arming or escalation, with the client IP, level, source, breached window and the violation counters snapshot; re-arms and denials stay out of the database so a hammering client never adds write load, and a persistence failure never changes the decision (best effort, logged).

## 2026-11-19-4

* Add fair-use quota and rate limiting on `/builds/sync`: per-client-IP counters in a Valkey store across second/minute/hour/day/week windows, `429 QUOTA_EXCEEDED` responses with `Retry-After` and `X-RateLimit-*` headers and a link to the instance-served rate-limiting documentation, and automatic escalation to 1-hour/24-hour bans for clients that keep firing while over quota. The quota is active only when `VALKEY_HOST` is configured, and fails open when the store is unreachable; documented in `docs/rate-limiting-and-quotas.md`.
* Add the `valkey` Docker Compose service (ephemeral, memory-bounded) and the `VALKEY_*`/`QUOTA_*` configuration.
* Persist the Valkey quota state across restarts: the Compose service now takes RDB snapshots every 60 s (and on clean shutdown) into `./data/valkey`, so window counters and bans survive reboots instead of being wiped (at most the last minute of counters can be lost).
* Add PostgreSQL indexes on `(remote_ip, received_at)`, `(forwarded_remote_ip, received_at)` and `received_at` for performant IP/period lookups on the durable jobs record.

## 2026-11-19-3

* Distribute a documentation site from the service: API reference (endpoints, parameters, code samples for curl, HTTPie, Python, PHP, Go, Elixir, JavaScript and ClojureScript), usage guides for server code, CI pipelines and browser integrations (JSON and multipart), and a live in-browser playground to try the endpoints. Built with Node/Eleventy at Docker image build and served from the `/docs/` route; the API index response now points `documentation` to it.

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
