## Installing all environment through Docker ##
docker-build:
	docker build -t latex-on-http .

docker-delete:
	docker stop latex-on-http
	docker rm latex-on-http

docker-start:
	docker run -d -p 127.0.0.1:80:8080 --name latex-on-http latex-on-http

## Running Python app ##
install:
	pipenv install

start:
    # TODO use --workers=2 --threads=8
	pipenv run gunicorn --workers=1 --bind=0.0.0.0:8080 app:app

debug:
	pipenv run python app.py --verbose

## Tests ##
test:
	pipenv run pytest

install-dev:
	pipenv install --dev
