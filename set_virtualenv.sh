#!/usr/bin/env bash

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Fail on error
trap on_error ERR

function on_error() {
    echo -e "${RED}Error during installation!${NC}"
    exit 1
}

function info() {
    echo -e "${GREEN}$1${NC}"
}

VERSION=2.7.10
ENABLE=".use_virtualenv"

info  "=== Install virtualenv for ESCAPEv2 ==="

echo "Used Python version: $VERSION"

info "=== Installing dependencies ==="
sudo apt-get update && sudo apt-get install libsqlite3-dev libssl-dev
sudo pip install virtualenv

info "=== Download,compile and install Python in a separate folder ==="
wget "https://www.python.org/ftp/python/${VERSION}/Python-${VERSION}.tar.xz"
tar xvJf "Python-${VERSION}.tar.xz"
cd ./"Python-${VERSION}"
PYTHON_DIR=$PWD
./configure --prefix=${PYTHON_DIR}
make altinstall
make install
cd ..
PROJECT_DIR=$PWD
cd ..

info "=== Set up virtualenv ==="
virtualenv --python="${PYTHON_DIR}/bin/python" --no-site-packages $PROJECT_DIR

info "=== Install Python dependencies into virtual environment ==="
cd $PROJECT_DIR
source ./bin/activate
pip install requests jinja2 ncclient lxml networkx py2neo numpy
deactivate

info "=== Enable virtualenv for 'escape.py' script ==="
echo $ENABLE && touch $ENABLE

info "=== Done ==="