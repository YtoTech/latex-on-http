# Dev guide

## Create a migration file

```sh
docker-compose run --entrypoint /bin/bash latex -c "goose -s create <migration_name> sql"
sudo 
make set-permissions-migrations
```

## Running tests without Docker (agent/LLM containers)

A dedicated virtualenv (`.venv-cline`, git-ignored) allows running the unit
tier without Docker, LaTeX or a database — the main `.venv` is left untouched:

```sh
make test-env   # create/refresh .venv-cline from pyproject.toml
make test-unit  # unit tier; integration tests skip when LATEX_ON_HTTP_API_URL is unset
```

Integration tests using `latex_on_http_api_url` are skipped unless
`LATEX_ON_HTTP_API_URL` is configured; `make test` (docker compose) sets it.
See `.cline/skills/testing/SKILL.md` for the full testing guide.

## Documentation site

The documentation site (API reference, guides, live playground) is an
Eleventy static site in `docs/site/`, built to `docs/_build/` (git-ignored)
and served by the application from the `/docs/` route. The Docker build runs
it in a Node stage and copies the output into the final image.

```sh
make docs-install  # npm ci in docs/site/
make serve-docs    # dev server with live reload (http://localhost:8081)
make build-docs    # build to docs/_build/
```

Endpoint definitions, parameter tables and code samples are declared once in
`docs/site/_data/endpoints.js` and consumed by both the reference pages and
the playground; playground behaviour lives in
`docs/site/_data/playground.js` + `docs/site/assets/js/playground.js`.

## Compilation job tracking

The application reads PostgreSQL from `DATABASE_URL` (falling back to
`GOOSE_DBSTRING`) and runs Goose migrations during container startup. Compilation
jobs require this database: an initial insert failure stops the compilation.
Subsequent tracking-update failures are logged without replacing the response.
Run `docker compose build` before `docker compose up` so the image contains the
runtime psycopg dependency and migrations; bind-mounted source alone does not
update the packages installed in an existing image.

Each accepted `/builds/sync` response includes an `X-Job-ID` header. Stored input
specifications omit document and Base64 contents as well as URL credentials,
queries, and fragments. The full incoming request body is buffered before
parsing to record its exact byte size, so request-size limits and storage should
be sized accordingly.

`DATABASE_POOL_MIN_SIZE`, `DATABASE_POOL_MAX_SIZE`, and `DATABASE_POOL_TIMEOUT`
control the lazy psycopg pool. The Compose test service sets
`TEST_DATABASE_URL`; tests using it truncate the jobs and user-agent tables, so
it must only point to a disposable test database. The PostgreSQL integration
tests are skipped when this variable is absent.

