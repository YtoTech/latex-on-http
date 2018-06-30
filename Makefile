## Running Python app ##
install:
	pipenv install

start:
	pipenv run gunicorn --workers=2 --threads=8 --bind=0.0.0.0:8080 app:app

debug:
	pipenv run python app.py --verbose --debug

## Tests ##
test:
	pipenv run pytest -vv

install-dev:
	pipenv install --dev

## Code conventions and formatting ##
format:
	pipenv run black .
