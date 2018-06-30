## Running Python app ##
install:
	PIPENV_VENV_IN_PROJECT=true pipenv install

start:
	PIPENV_VENV_IN_PROJECT=true pipenv run gunicorn --workers=2 --threads=8 --bind=0.0.0.0:8080 app:app

debug:
	PIPENV_VENV_IN_PROJECT=true pipenv run python app.py --verbose --debug

## Tests ##
test:
	PIPENV_VENV_IN_PROJECT=true pipenv run pytest -vv

install-dev:
	PIPENV_VENV_IN_PROJECT=true pipenv install --dev

## Code conventions and formatting ##
format:
	PIPENV_VENV_IN_PROJECT=true pipenv run black .
