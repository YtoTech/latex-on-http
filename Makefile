build:
	docker build -t latex-on-http .

delete:
	docker stop latex-on-http
	docker rm latex-on-http

start:
	docker run -d -p 127.0.0.1:80:80 --name latex-on-http latex-on-http
