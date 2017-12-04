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
	if [ ! -d "venv" ]; then \
		virtualenv -p python3 venv; \
	fi
	venv/bin/pip3 install -r requirements.txt

start: install
    # TODO use --threads=8
	cd latex-on-http && ../venv/bin/gunicorn --workers=2 --bind=0.0.0.0:8080 app:app

debug: install
	venv/bin/python3 latex-on-http/app.py --verbose

## Tests ##
test: install-tests
	venv_tests/bin/pytest

install-tests:
	if [ ! -d "venv_tests" ]; then \
		virtualenv -p python3 venv_tests; \
	fi
	venv_tests/bin/pip3 install -r requirements-tests.txt
