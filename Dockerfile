# Latex On HTTP Docker container.
#
# Try an installation based on Alpine.
FROM debian:latest
MAINTAINER Yoan Tournade <yoan@ytotech.com>

RUN apt-get update \
  && apt-get install -y \
    # TODO How do we select the list of Latex packages to install?
    # (texlive-full is heavy!)
    texlive-fonts-extra \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-luatex \
    texlive-math-extra \
    texlive-xetex \
    # TODO We need Python (go for Python 3!)
    python3 \
    python-pip \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install Virtualenv
RUN pip install \
  virtualenv

# TODO Then install Flask & co? (requirements.txt)
# See https://github.com/gliderlabs/docker-alpine/blob/master/docs/usage.md
# RUN sh /check.sh

# TODO Copy application source code. (Or use a mount point?)
# COPY ./docker-entrypoint.sh /

EXPOSE 80

CMD ["python app.py"]
ENTRYPOINT ["mysql"]
