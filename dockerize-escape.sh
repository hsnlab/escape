#!/usr/bin/env bash
# Copyright 2016 Janos Czentye <czentye@tmit.bme.hu>
# Install ESCAPE with all the dependencies into a Docker container
# based on Ubuntu 14.04.4 LTS

# Constants for colorful logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

set -euo pipefail

# Fail on error
trap "on_error 'Got signal: SIGHUP'" SIGHUP
trap "on_error 'Got signal: SIGINT'" SIGINT
trap "on_error 'Got signal: SIGTERM'" SIGTERM
trap on_error ERR

function on_error() {
    echo -e "\n${RED}Error during installation! ${1-}${NC}"
    exit 1
}

function info() {
    echo -e "${GREEN}${1}${NC}"
}

### Constants
IMAGE_NAME="escape/mdo"
CONTAINER_NAME="ESCAPE"

# Distributor constants
if [ -f /etc/lsb-release ]; then
    DISTRIB_VER=$(lsb_release -sr)
else
    on_error "Missing distributor version! Maybe the current platform is not Ubuntu?"
fi

# Install docker dependencies
if [[ ! $(sudo apt-cache -q show docker-engine) ]]; then
    # Install dependencies
    sudo apt-get install apt-transport-https ca-certificates
    sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
    if [ "$DISTRIB_VER" = "14.04" ]; then
        echo "deb https://apt.dockerproject.org/repo ubuntu-trusty main" | sudo tee /etc/apt/sources.list.d/docker.list
    elif [ "$DISTRIB_VER" = "16.04" ]; then
        echo "deb https://apt.dockerproject.org/repo ubuntu-xenial main" | sudo tee /etc/apt/sources.list.d/docker.list
    else
        on_error "Only Ubuntu 14.04 and 16.104 LTS are supported! This version: $DISTRIB_VER"
    fi
    sudo apt-get update
    sudo apt-get install -y docker-engine
    sudo usermod -aG docker $(whoami)
fi

# Dockerize
cp -R ~/.ssh .ssh

sudo docker build --rm -t ${IMAGE_NAME} .
sudo docker create --name ${CONTAINER_NAME} -p 8008:8008 -p 8888:8888 -p 8889:8889 -it ${IMAGE_NAME}

rm -rf .ssh

info "To start the default container use the following command: sudo docker start -i ESCAPE \n
or run a new one with different ESCAPE parameters: sudo docker run -p 8008:8008 -p 8888:8888 -p 8889:8889 --name <new name> -it ${IMAGE_NAME} <new parameters...>"