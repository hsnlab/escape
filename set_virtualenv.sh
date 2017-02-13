#!/usr/bin/env bash

# Install script for ESCAPEv2 to setup virtual environment
# Copyright 2016 Janos Czentye <czentye@tmit.bme.hu>

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Fail on error
trap on_error ERR

function on_error {
    echo -e "${RED}Error during installation!${NC}"
    exit 1
}

function info() {
    echo -e "${GREEN}$1${NC}"
}

function print_usage {
    echo -e "Usage: $0 [-p python_version] [-h]"
    echo -e "Install script for ESCAPEv2 to setup virtual environment\n"
    echo -e "optional parameters:"
    echo -e "\t-p:   set Python version (default: $VERSION)"
    echo -e "\t-h:   show this help message and exit"
    echo -e "Example: ./set_virtualenv.sh -p 2.7.13"
    echo -e "Based on virtualenv. More information: virtualenv -h"
    exit 0
}

# Default variables
VERSION=2.7.13
ENABLE=".use_virtualenv"

# Read initial parameters
while getopts ":p:h" OPTION;
do
    case ${OPTION} in
    p)
        VERSION=${OPTARG};;
    h)
        print_usage;;
    :)
        echo "Option -$OPTARG requires an argument." >&2
        exit 1;;
    \?)
        echo "Invalid option: -$OPTARG" >&2
        exit 1;;
    esac
done

info  "======================================="
info  "==  Install virtualenv for ESCAPEv2  =="
info  "======================================="
echo "Used Python version: $VERSION"

info "=== Download Python in a separate folder ==="
wget "https://www.python.org/ftp/python/${VERSION}/Python-${VERSION}.tar.xz"

info "=== Installing dependencies ==="
sudo apt-get update && sudo apt-get install -y python-dev python-pip zlib1g-dev \
libxml2-dev libxslt1-dev libssl-dev libffi-dev python-crypto
sudo pip install virtualenv

info "=== Compile and install Python ==="
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
virtualenv --python="${PYTHON_DIR}/bin/python" --no-site-packages ${PROJECT_DIR}

info "=== Install Python dependencies into virtual environment ==="
cd ${PROJECT_DIR}
source ./bin/activate
pip install numpy jinja2 py2neo networkx requests ncclient pyyaml cryptography==1.3.1
deactivate

info "=== Enable virtualenv for 'escape.py' script ==="
echo ${ENABLE} && touch ${ENABLE}

info "============"
info "==  Done  =="
info "============"
