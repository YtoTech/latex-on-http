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
    # TODO use --threads=8
	# pipenv shell && cd latex-on-http && gunicorn --workers=2 --bind=0.0.0.0:8080 app:app
	pipenv run gunicorn --workers=2 --bind=0.0.0.0:8080 latex-on-http.app:app

debug:
	pipenv run python latex-on-http/app.py --verbose

## Tests ##
test:
	pipenv run pytest

install-dev:
	pipenv install --dev
