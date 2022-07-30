#!/bin/bash

echo "$DOCKER_USERNAME"
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
docker push yoant/latexonhttp-tl-distrib:debian
docker push yoant/latexonhttp-python:debian
