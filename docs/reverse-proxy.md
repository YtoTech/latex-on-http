# Keeping the docs and API responsive: gunicorn sizing and a reverse proxy

`/builds/sync` is fully synchronous: the request thread is held for the whole build — parsing, fetching remote resources (up to 15 s connect / 60 s read per URL, see `FETCHER_HTTP_REQ_CONNECT_TIMEOUT` / `FETCHER_HTTP_REQ_READ_TIMEOUT`) and the sandboxed compilation itself (up to `DEFAULT_COMPILE_TIMEOUT`, 100 s by default). The server therefore has a bounded number of request slots, and every slot consumed by an in-flight compilation is a slot the documentation site and the light endpoints (`/`, `/fonts`, `/packages`, `/texlive`) cannot use.

The documentation site is 100 % static (built by Node/Eleventy into `docs/_build/`, served by the app from `/docs/`), and a page load is several small requests (HTML, CSS, JS, woff2 fonts, SVGs). When every slot is busy compiling, those requests queue in Gunicorn's listen backlog and the docs feel slow — the classic symptom being "the docs page takes 30 s to load while builds are running".

Two levers keep the non-compiling routes responsive:

1. **Give the server more slots** — `GUNICORN_WORKERS` / `GUNICORN_THREADS` (this repository, `make start`).
2. **Serve the static docs from the reverse proxy** — the docs then never reach the Python app at all (this guide, Caddy below).

## Gunicorn sizing

`make start` runs:

```sh
gunicorn --workers=$(GUNICORN_WORKERS) --threads=$(GUNICORN_THREADS) --bind=0.0.0.0:8080 app:app
```

Both variables default to `2` and `16` respectively, and are overridable from `.env` (the Makefile includes it; see `.env.example`). Total request slots = `GUNICORN_WORKERS x GUNICORN_THREADS`.

Why threads, not more workers: a slot is mostly *waiting* — on the fetch (network) and on the compilation (a subprocess the thread simply waits on). A waiting Python thread releases the GIL and costs almost nothing; the slots only become expensive when they are actually used in parallel, which is bounded by the machine's CPU. More threads therefore directly raise the ceiling on concurrent compilations *and* keep spare slots for the light routes.

The trade-off is memory, not CPU: each in-flight build can hold up to `MAX_PDF_SIZE` (default 100 MiB) of generated PDF in memory before replying, plus the fetched workspace files. On a memory-constrained box, keep the product `GUNICORN_WORKERS x GUNICORN_THREADS` modest (8–16) and rely on lever 2 for the docs; on a comfortable box, 32+ slots are fine.

Recreate the service after changing either variable (`make start` reads them at invocation).

## Serving the documentation from the reverse proxy

Public instances terminate TLS in a reverse proxy (Caddy here). Let it serve the statically-built documentation site directly: `/docs/*` answers without ever waking the Python app, so the docs are instant no matter how saturated the compilation is. The Flask `/docs/` route stays as a fallback for self-hosted setups without a proxy (and for local dev), and the proxy config below mirrors its behavior:

| Request | Flask route | Proxy equivalent |
|---|---|---|
| `/docs` | 302 redirect to `/docs/` | `redir /docs /docs/ 308` |
| `/docs/`, `/docs/guides/server/` | `index.html` of the directory | `file_server` directory index |
| `/docs/guides/server` (no slash) | `index.html` via the pretty-URL fallback | `try_files {path} {path}/index.html` |
| `/docs/assets/*` | `Cache-Control: max-age=600` | long-lived `Cache-Control` (assets are content-hashed-free but rarely change) |
| everything else | — | proxied to the app |

### Where the proxy reads the built files

The proxy needs `docs/_build/` on the **host** filesystem (the built copy inside the container image is not visible to it). Two options:

* **Build on the host** (recommended when you have Node ≥ 20): `make build-docs` in the repository checkout, then point the proxy at `./docs/_build`. This is also what the dev Compose bind-mount makes the *app* serve, so both layers stay in sync.
* **Copy out of the image** (no Node needed): the Dockerfile already builds the site at image build time, so

  ```sh
  docker run --rm -v /opt/latex-on-http:/out yoant/latexonhttp:latest \
      cp -r /app/latex-on-http/docs/_build /out/docs/
  ```

  lands `_build` where a proxy on the host can read it. Re-run after every image rebuild.

### Caddy

`/etc/caddy/Caddyfile` (adjust the domain, the `_build` path and the upstream port):

```caddy
https://latex.example.com {
	# Mirror the app's canonical /docs -> /docs/ redirect.
	redir /docs /docs/ 308

	# Static documentation site: served by the proxy, never reaches the
	# Python app. The /docs prefix is stripped, so /docs/guides/server/
	# maps to <_build>/guides/server/.
	handle_path /docs/* {
		root * /opt/latex-on-http/docs/_build
		# Pretty URLs (Eleventy): /docs/guides/server -> .../server/index.html.
		try_files {path} {path}/index.html
		# Long-lived cache for the static assets.
		@assets path /assets/*
		header @assets Cache-Control "public, max-age=31536000"
		file_server
	}

	# Everything else (/, /builds, /fonts, /packages, /texlive, /caches).
	reverse_proxy 127.0.0.1:8080
}
```

Caddy's `reverse_proxy` sets `X-Forwarded-For` and `X-Forwarded-Proto` automatically — the latter matters: the app derives the `documentation` URLs it embeds in API responses (and error payloads) from the announced scheme.

Then `sudo systemctl reload caddy` (or `caddy validate --config /etc/caddy/Caddyfile` first). Verify:

```sh
# Served by the proxy, with the long asset cache header:
curl -sI https://latex.example.com/docs/assets/css/styles.css | grep -i cache-control
# Still proxied to the app:
curl -s https://latex.example.com/ | head -1
```

### nginx (reference)

```nginx
server {
    # Canonical /docs -> /docs/ (the app does the same redirect).
    location = /docs {
        return 308 /docs/;
    }

    # Static assets, long-lived cache.
    location ~* ^/docs/assets/ {
        alias /opt/latex-on-http/docs/_build/assets/;
        add_header Cache-Control "public, max-age=31536000";
    }

    # Documentation site (Eleventy pretty URLs -> index.html fallback).
    location /docs/ {
        alias /opt/latex-on-http/docs/_build/;
        try_files $uri $uri/index.html =404;
    }

    # Everything else: the app.
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

(`proxy_set_header X-Forwarded-Proto` is the piece Caddy does by default — keep it, the app uses it to build absolute documentation URLs.)

### Rebuilding the site

The proxy serves whatever is on disk at `docs/_build/`, so after content changes run `make build-docs` (or the `docker run … cp -r` above) and reload the proxy (`sudo systemctl reload caddy`). No app redeploy is needed.

## Verifying the effect

Saturate the instance with slow compilations, then time the docs time-to-first-byte:

```sh
BASE_URL="${1:-http://127.0.0.1:8080}"
N="${2:-20}"

# A document that keeps the compiler busy for a few seconds.
SLOW_DOC='{"compiler":"pdflatex","resources":[{"main":true,"content":"\\documentclass{article}\n\\begin{document}\n\\newcount\\i\n\\i=0\n\\loop\\advance\\i by 1\n\\ifnum\\i<5000000\n\\repeat\nDone.\n\\end{document}"}]}'

# Fire N concurrent compilations in the background.
for i in $(seq 1 "$N"); do
    curl -s -o /dev/null --max-time 300 -X POST "$BASE_URL/builds/sync" \
        -H 'Content-Type: application/json' -d "$SLOW_DOC" &
done

# While they are in flight:
curl -s -o /dev/null -w 'docs TTFB: %{time_starttransfer}s\n' "$BASE_URL/docs/"
wait
```

Expected: with the proxy serving `/docs/*`, the TTFB stays in the milliseconds (a local `200`, or a CDN hit) regardless of the in-flight builds; on the app-only route (before the proxy change), the same measurement waits for a free worker thread and tracks the compilation load. On public instances behind Cloudflare, the docs are additionally cached at the edge — the origin measurement above is the worst case.

## Known limits

* The proxy serves what is on disk: a stale `docs/_build/` means stale docs even after an app redeploy (the app and the proxy no longer share a source of truth). Rebuild the site whenever the docs change.
* Serving docs from the proxy does not protect the *compilation* throughput from a flood of light API requests — that is the other direction of the same shared pool and is bounded by the machine; the quota (see [Rate limiting and quotas](rate-limiting-and-quotas.md)) bounds request count, and a Valkey-based per-IP semaphore on in-flight compilations would cap concurrency directly.
* The long-term structural fix is moving compilation out of the API process (dedicated compile workers / an async job API); until then, the two levers above are the operational answer.
