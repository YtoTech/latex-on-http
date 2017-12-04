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
	venv/bin/python3 latex-on-http/app.py

debug: install
	venv/bin/python3 latex-on-http/app.py --verbose
