## -------------------------------
## Running Python app ##
## -------------------------------
install:
	pipenv install

start:
	pipenv run gunicorn --workers=2 --threads=8 --bind=0.0.0.0:8080 app:app

debug:
	pipenv run python app.py --verbose --debug


## -------------------------------
## Running cache app ##
## -------------------------------
start-cache:
	pipenv run python app_cache.py

debug-cache:
	pipenv run python -u app_cache.py --debug


## -------------------------------
## Dev tools ##
## -------------------------------
install-dev:
	pipenv install --dev


## -------------------------------
## Docker build/images ##
## -------------------------------
docker-pull-yoant-texlive-debian:
	docker pull yoant/docker-texlive:debian

docker-pull-yoant-texlive-alpine:
	docker pull yoant/docker-texlive:alpine

docker-build-tl-distrib-debian:
	docker build -f container/tl-distrib-debian.Dockerfile -t yoant/latexonhttp-tl-distrib:debian .

docker-build-tl-distrib-alpine:
	docker build -f container/tl-distrib-alpine.Dockerfile -t yoant/latexonhttp-tl-distrib:alpine .

docker-build-python-debian:
	docker build -f container/python-debian.Dockerfile -t yoant/latexonhttp-python:debian .

docker-build-python-alpine:
	docker build -f container/python-alpine.Dockerfile -t yoant/latexonhttp-python:alpine .

docker-build-main:
	docker build -f Dockerfile .

docker-build-all-debian: docker-pull-yoant-texlive-debian docker-build-tl-distrib-debian docker-build-python-debian docker-build-main

docker-build-all-alpine: docker-pull-yoant-texlive-alpine docker-build-tl-distrib-alpine docker-build-python-alpine docker-build-main

docker-build-all: docker-build-all-debian

## -------------------------------
## Docker push/images ##
## -------------------------------
docker-push-tl-distrib-debian:
	docker push yoant/latexonhttp-tl-distrib:debian

docker-push-python-debian:
	docker push yoant/latexonhttp-python:debian


## -------------------------------
## Docker Compose for dev ##
## -------------------------------
dev:
	docker-compose -f docker-compose.dev.yml up

dev-build:
	docker-compose -f docker-compose.dev.yml build --no-cache

dev-sh-latex:
	docker-compose -f docker-compose.dev.yml exec latex /bin/bash

## -------------------------------
## Tests ##
## -------------------------------
test:
	pipenv run pytest -vv

test-x:
	pipenv run pytest -vv -x

test-docker-compose: test-docker-compose-start
	sleep 3
	make test
	sleep 2
	make test-docker-compose-stop

test-docker-compose-up:
	docker compose -f docker-compose.test.yml -p latex-on-http-test up

test-docker-compose-bash:
	docker compose -f docker-compose.test.yml -p latex-on-http-test exec -it latex bash

test-docker-compose-start:
	docker compose -f docker-compose.test.yml -p latex-on-http-test up --no-start
	docker compose -f docker-compose.test.yml -p latex-on-http-test start

test-docker-compose-stop:
	docker compose -f docker-compose.test.yml -p latex-on-http-test stop

test-docker-compose-rm:
	docker compose -f docker-compose.test.yml -p latex-on-http-test rm

test-docker-compose-build:
	docker compose -f docker-compose.test.yml -p latex-on-http-test build

test-docker-compose-build-no-cache:
	docker compose -f docker-compose.test.yml -p latex-on-http-test build --no-cache

## -------------------------------
## Code conventions and formatting ##
## -------------------------------
format:
	pipenv run black .
