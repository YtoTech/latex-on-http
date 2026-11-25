---
name: testing
description: How to run the LaTeX-on-HTTP test suite in the LLM/AI coding container. Covers the dedicated .venv-cline virtualenv, the unit tier (no Docker, no LaTeX, no DB), the docker-compose integration tier, key environment variables, and this container's known limitations. Read this before running or debugging tests.
---

# Testing LaTeX-on-HTTP (LLM / AI coding container)

## Environment map

| Path / tool | Role |
|---|---|
| `/workspace/fire-latex/latex-on-http` | The project (bind-mounted in the LLM container). |
| `.venv/` | The maintainer's main virtualenv, **owned by the host**. Never create, modify, install into or delete it from the container. |
| `.venv-cline/` | Dedicated virtualenv for unit-tier tests (git-ignored, safe to delete/recreate). |
| `make test-env` | Creates/refreshes `.venv-cline` from `pyproject.toml` (runtime + dev deps). |
| `make test-unit` | Runs the unit tier with `.venv-cline` (no Docker, no LaTeX, no DB). |
| `make test` / `make test-docker-compose` | Full integration tier; requires Docker on the host — **not available inside the LLM container**. |

## Running tests

```sh
# One-time (or after dependency changes):
make test-env

# Unit tier (~few seconds; integration tests skip automatically):
make test-unit

# Single file / single test:
.venv-cline/bin/python -m pytest tests/test_compiler.py -q
.venv-cline/bin/python -m pytest tests/test_compiler.py -k timeout -q

# With skip reasons visible:
.venv-cline/bin/python -m pytest -q -rs tests/
```

## Test tiers

1. **Unit tier** — runs green in the LLM container:
   `test_compiler.py`, `test_cache_decisions.py`, `test_compilation_hash.py`,
   `test_resource_logging.py`, `test_jobs_repository.py` (fake connections),
   `test_api_validations.py`, and `test_sandbox.py`/`test_sandbox_diagnostics.py`
   (except the real-sandbox compile test, see limitations).
2. **Integration tier** — needs a running app + TeX Live (docker compose):
   everything using the `latex_on_http_api_url` fixture
   (`test_compiling`, `test_api_*`, `test_fetchers`, `test_fonts`,
   `test_packages`, `test_up_and_running`, `test_cors`, `test_workspaces`,
   `test_job_tracking` partial). These tests skip automatically when
   `LATEX_ON_HTTP_API_URL` is unset (see `tests/conftest.py`); the docker
   compose test service sets it, so `make test` runs them all.
3. **PostgreSQL tier** — `test_jobs_postgres.py` skips unless
   `TEST_DATABASE_URL` points to a disposable database.

## Rules and known limitations of this container

- **Never touch `.venv/`**: it belongs to the host (its interpreter path does
  not even exist inside the container). Use `.venv-cline` or `make test-env`.
- This container runs **Python 3.14**, while `pyproject.toml` declares
  `requires-python = ">=3.12,<3.14"`. Therefore do **not** `pip install -e .`;
  `make test-env` installs only the dependency list (the app runs from the
  repository, no installation needed). Behaviour of bleeding-edge deps may
  differ from the pinned `uv.lock` on the host — anything failing only here
  (and not under `make test`) should be attributed to the environment first.
- **No Docker socket** in the container: integration tier must run on the host
  (`make test-docker-compose`), or ask the user to run it.
- **User namespaces are disabled** in the kernel: Bubblewrap cannot sandbox,
  so `test_real_sandbox_hides_host_files_network_and_environment` skips itself
  (it hard-fails only when `LATEX_REQUIRE_SANDBOX_TESTS=1`, as enforced by
  `docker-compose.test.yml`). Never disable sandboxing in product code to make
  tests pass here.
- No TeX Live, no `latexmk`, no fonts, no PostgreSQL inside the container.
- Test-only configuration knobs (see `docker-compose.test.yml`):
  `FETCHER_HTTP_REQ_CONNECT_TIMEOUT` / `FETCHER_HTTP_REQ_READ_TIMEOUT` reduce
  the resource-fetch timeouts so timeout tests run quickly.

## Useful background

- `DEV.md` — dev guide (migrations, job tracking, database).
- `docs/sandboxing.md` — sandboxing model and its configuration variables.
- `docker-compose.test.yml` — the reference test configuration (env vars).

## Discovery across AI assistants

This file is the **single source of truth** for how to test this repo. It lives
at `.agents/skills/testing/SKILL.md` (a neutral, tool-agnostic location) and is
surfaced to AI coding assistants so it is loaded whenever tests are run or
debugged:

- **OpenCode** — discovered natively from `.agents/skills/` (a project
  compatibility source); also referenced from `AGENTS.md`.
- **Cline** — pointed here from `.clinerules`.
- **Claude Code** — pointed here from `CLAUDE.md`.

Keep this file as the canonical copy. Edit the pointer files only to change
*when* they fire, never to duplicate the instructions here. Do **not** create a
second skill folder (`.opencode/skills/`, `.claude/skills/`, …) for `testing` —
that would register a duplicate skill ID in OpenCode.
