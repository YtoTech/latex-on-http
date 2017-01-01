# Latex On HTTP Docker container.
#
MAINTAINER Yoan Tournade <yoan@ytotech.com>

# Try an installation based on Alpine.
FROM alpine:3.5
# TODO Do not use the full texlive distribution but a subset?
RUN apk add --no-cache texlive-full
# TODO We need Python (go for Python 3!)
RUN apk add --no-cache python3 py-pip

# Install Virtualenv
RUN pip install virtualenv
# TODO Then install Flask & co? (requirements.txt)
# See https://github.com/gliderlabs/docker-alpine/blob/master/docs/usage.md
# RUN sh /check.sh

# TODO Copy application source code. (Or use a mount point?)
# COPY ./docker-entrypoint.sh /
EXPOSE 80
CMD ["python app.py"]
ENTRYPOINT ["mysql"]
