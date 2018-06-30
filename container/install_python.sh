set -e

apt-get update -qq && apt-get install -y \
    python3 \
    python3-pip

# Update pip and install Pipenv.
pip3 install -U \
  pip \
  pipenv
