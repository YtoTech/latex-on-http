## Running Python app ##
install:
	pipenv install

start:
	pipenv run gunicorn --workers=2 --threads=8 --bind=0.0.0.0:8080 app:app

debug:
	pipenv run python app.py --verbose --debug

## Dev tools ##
install-dev:
	pipenv install --dev

## Docker Compose for dev ##
dev:
	docker-compose -f docker-compose.dev.yml up

## Tests ##
test:
	pipenv run pytest -vv

test-docker-compose: test-docker-compose-start
	make test
	make test-docker-compose-stop

test-docker-compose-up:
	docker-compose -f docker-compose.test.yml -p latex-on-http-test up

test-docker-compose-start:
	docker-compose -f docker-compose.test.yml -p latex-on-http-test up

test-docker-compose-stop:
	docker-compose -f docker-compose.test.yml -p latex-on-http-test up

## Code conventions and formatting ##
format:
	pipenv run black .
