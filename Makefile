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
## Dev tools ##
## -------------------------------
install-dev:
	pipenv install --dev


## -------------------------------
## Docker build/images ##
## -------------------------------
docker-build-tl-distrib-debian:
	docker build -f container/tl-distrib-debian.Dockerfile -t yoant/latexonhttp-tl-distrib:debian .

docker-build-tl-distrib-alpine:
	docker build -f container/tl-distrib-alpine.Dockerfile -t yoant/latexonhttp-tl-distrib:alpine .

docker-build-main:
	docker build -f Dockerfile .

docker-build-all: docker-build-tl-distrib-debian docker-build-main

## -------------------------------
## Docker Compose for dev ##
## -------------------------------
dev:
	docker-compose -f docker-compose.dev.yml up


## -------------------------------
## Tests ##
## -------------------------------
test:
	pipenv run pytest -vv

test-docker-compose: test-docker-compose-start
	sleep 3
	make test
	sleep 2
	make test-docker-compose-stop

test-docker-compose-up:
	docker-compose -f docker-compose.test.yml -p latex-on-http-test up

test-docker-compose-start:
	docker-compose -f docker-compose.test.yml -p latex-on-http-test up --no-start
	docker-compose -f docker-compose.test.yml -p latex-on-http-test start

test-docker-compose-stop:
	docker-compose -f docker-compose.test.yml -p latex-on-http-test stop


## -------------------------------
## Code conventions and formatting ##
## -------------------------------
format:
	pipenv run black .
