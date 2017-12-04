docker-build:
	docker build -t latex-on-http .

docker-delete:
	docker stop latex-on-http
	docker rm latex-on-http

docker-start:
	docker run -d -p 127.0.0.1:80:8080 --name latex-on-http latex-on-http

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
