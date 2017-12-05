apt-get update -qq
apt-get install -y \
    python3 \
    python3-pip \
    wget

# TODO Why wget? For CTAN?

# Update pip and install virtualenv.
pip3 install -U \
  pip \
  virtualenv
