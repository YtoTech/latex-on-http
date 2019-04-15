set -e

# git is used for some package installs.
# TODO This is an "old" Python version.
# Drop Debian to get more recent Python version?
# apt-get update -qq && apt-get install -y \
#     python3 \
#     python3-pip \
#     git

apk --no-cache add \
    python3 \
    git \
    make \
    python3-dev \
    libffi-dev \
    gcc \
    musl-dev

# Update pip and install Pipenv.
# TODO --user install + add ~/.local/bin to path.
pip3 install -U \
  pip \
  pipenv
