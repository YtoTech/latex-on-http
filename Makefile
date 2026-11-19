# Docker Compose loads .env itself. Include it here as well so the test
# targets can carry non-base Compose overrides into docker-compose.test.yml.
-include .env

# Image tags, overridable for CI.
DOCKER_IMAGE_TAG ?= latest
DOCKER_MAIN_IMAGE ?= yoant/latexonhttp:$(DOCKER_IMAGE_TAG)
DOCKER_CACHE_IMAGE ?= yoant/latexonhttp-cache:$(DOCKER_IMAGE_TAG)

COMPOSE_FILE ?= docker-compose.yml
COMPOSE_PATH_SEPARATOR ?= :
COMPOSE_OVERRIDE_FILES = $(filter-out docker-compose.yml ./docker-compose.yml,$(subst $(COMPOSE_PATH_SEPARATOR), ,$(COMPOSE_FILE)))
COMPOSE_TEST_FILES ?= docker-compose.test.yml $(COMPOSE_OVERRIDE_FILES)
COMPOSE_TEST_FLAGS = $(foreach file,$(COMPOSE_TEST_FILES),-f $(file))
DOCKER_COMPOSE_TEST = docker compose $(COMPOSE_TEST_FLAGS) -p latex-on-http-test

## -------------------------------
## Running Python app ##
## -------------------------------
install:
	uv sync

start:
	uv run gunicorn --workers=2 --threads=8 --bind=0.0.0.0:8080 app:app

debug:
	uv run python app.py --verbose --debug


## -------------------------------
## Running cache app ##
## -------------------------------
start-cache:
	uv run python app_cache.py

debug-cache:
	uv run python -u app_cache.py --debug

## -------------------------------
## Docker build/images ##
## -------------------------------
docker-pull-yoant-texlive-debian:
	docker pull yoant/docker-texlive:debian

docker-build-tl-distrib-debian:
	docker build -f container/tl-distrib-debian.Dockerfile -t yoant/latexonhttp-tl-distrib:debian .

docker-build-python-debian:
	docker build -f container/python-debian.Dockerfile -t yoant/latexonhttp-python:debian .

docker-build-main:
	docker build -f Dockerfile -t $(DOCKER_MAIN_IMAGE) .

docker-build-cache:
	docker build -f cache.Dockerfile -t $(DOCKER_CACHE_IMAGE) .

docker-build-all-debian: docker-pull-yoant-texlive-debian docker-build-tl-distrib-debian docker-build-python-debian docker-build-main

docker-build-all: docker-build-all-debian docker-build-cache

## -------------------------------
## Docker push/images ##
## -------------------------------
docker-push-tl-distrib-debian:
	docker push yoant/latexonhttp-tl-distrib:debian

docker-push-python-debian:
	docker push yoant/latexonhttp-python:debian

docker-push-all: docker-push-tl-distrib-debian docker-push-python-debian

## -------------------------------
## Docker Compose for dev ##
## -------------------------------
dev:
	docker compose up

dev-build:
	docker compose build --no-cache

dev-sh-latex:
	docker compose exec latex /bin/bash

set-permissions-migrations:
	chown -R $(SUDO_USER):$(SUDO_USER) ./tools/migrations

## -------------------------------
## Tests ##
## -------------------------------
# Dedicated virtual environment for unit-tier tests, usable in
# agent/LLM containers (no Docker, no LaTeX, possibly unsupported Python).
# Leaves the main .venv untouched.
TEST_VENV ?= .venv-cline

test-env:
	python3 -m venv $(TEST_VENV)
	$(TEST_VENV)/bin/pip install --quiet --upgrade pip
	$(TEST_VENV)/bin/pip install --quiet $$($(TEST_VENV)/bin/python -c "import tomllib; data = tomllib.load(open('pyproject.toml', 'rb')); deps = data['project']['dependencies'] + data['dependency-groups']['dev']; print(' '.join(dep.replace(' ', '') for dep in deps))")

# Unit tier: no running app, no LaTeX, no database needed.
# Integration tests skip automatically when LATEX_ON_HTTP_API_URL is unset.
test-unit:
	LATEX_ON_HTTP_API_URL= $(TEST_VENV)/bin/python -m pytest -q tests/

test:
	$(DOCKER_COMPOSE_TEST) exec latex uv run pytest -vv

test-x:
	$(DOCKER_COMPOSE_TEST) exec latex uv run pytest -vv -x

test-docker-compose: test-docker-compose-start
	sleep 3
	$(MAKE) test
	sleep 2
	$(MAKE) test-docker-compose-stop

test-docker-compose-up:
	$(DOCKER_COMPOSE_TEST) up

test-docker-compose-up-recreate:
	$(DOCKER_COMPOSE_TEST) up --build --force-recreate

test-docker-compose-bash:
	$(DOCKER_COMPOSE_TEST) exec -it latex bash

test-docker-compose-start:
	$(DOCKER_COMPOSE_TEST) up --no-start
	$(DOCKER_COMPOSE_TEST) start

test-docker-compose-stop:
	$(DOCKER_COMPOSE_TEST) stop

test-docker-compose-logs:
	$(DOCKER_COMPOSE_TEST) logs --no-color --tail=500 latex

test-docker-compose-rm:
	$(DOCKER_COMPOSE_TEST) rm

test-docker-compose-build:
	$(DOCKER_COMPOSE_TEST) build

test-docker-compose-build-no-cache:
	$(DOCKER_COMPOSE_TEST) build --no-cache

## -------------------------------
## Code conventions and formatting ##
## -------------------------------
format:
	uv run black .

lint:
	uv run black --check .
