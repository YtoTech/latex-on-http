set -e

# git is used for some package installs.
apt-get update -qq && apt-get install -y \
    python3 \
    python3-pip \
    git

# Update pip and install Pipenv.
# TODO --user install + add ~/.local/bin to path.
pip3 install -U \
  pip \
  pipenv
