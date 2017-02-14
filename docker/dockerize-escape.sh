#!/usr/bin/env bash
# Copyright 2016 Janos Czentye <czentye@tmit.bme.hu>
# Install ESCAPE with all the dependencies into a Docker container
# based on Ubuntu 14.04.5 LTS

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
IMAGE_NAME="escape"
CONTAINER_NAME="ESCAPE"

function docker-dep {
    # Install docker and related packages is it's necessary
    if [ -f /etc/lsb-release ]; then
        #DISTRIB_VER=$(lsb_release -sr)
        source /etc/lsb-release
    else
        on_error "Missing distributor version! Maybe the current platform is not Ubuntu?"
    fi
    # Install docker dependencies
    if [[ ! $(sudo apt-cache -q show docker-engine) ]]; then
        # Install dependencies
        sudo apt-get install apt-transport-https ca-certificates
        sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
        if [ "$DISTRIB_RELEASE" = "14.04" ]; then
            echo "deb https://apt.dockerproject.org/repo ubuntu-trusty main" | sudo tee /etc/apt/sources.list.d/docker.list
        elif [ "$DISTRIB_RELEASE" = "16.04" ]; then
            echo "deb https://apt.dockerproject.org/repo ubuntu-xenial main" | sudo tee /etc/apt/sources.list.d/docker.list
        else
            on_error "Only Ubuntu 14.04 and 16.104 LTS are supported! This version: $DISTRIB_RELEASE"
        fi
        sudo apt-get update
        sudo apt-get install -y docker-engine
        sudo usermod -aG docker $(whoami)
    fi
}


function mdo {
    # Create image and container for Global Orchestrator
    docker-dep
    cp -R ~/.ssh .ssh
    sudo docker build --rm --no-cache -f ../Dockerfile -t "$IMAGE_NAME/mdo" ..
    sudo docker create --name "mdo$CONTAINER_NAME" -p 8008:8008 -p 8888:8888 -p 8889:8889 -it "$IMAGE_NAME/mdo"
    rm -rf .ssh
    info "To start the default container use the following command: sudo docker start -i mdo$CONTAINER_NAME"
}

function lo {
    # Create image and container for Local Orchestrator
    docker-dep
    cp -R ~/.ssh .ssh
    sudo docker build --rm --no-cache -f ../Dockerfile --build-arg ESC_INSTALL_PARAMS=ci -t "$IMAGE_NAME/lo" ..
    sudo docker create --name "lo$CONTAINER_NAME" -p 8008:8008 -p 8888:8888 -p 8889:8889 -e DISPLAY=${DISPLAY} --privileged --cap-add NET_ADMIN -it "$IMAGE_NAME/lo"
    rm -rf .ssh
    info "To start the default container use the following command: sudo docker start -i lo$CONTAINER_NAME"
}


function all {
    # Create all the images and containers
    docker-dep
    lo
    mdo
}

function print_usage {
    # Print help
    echo -e "Usage: $0 [-a] [-g] [-l] [-h]"
    echo -e "Dockerize ESCAPE as a Multi-Domain(MdO) or a Local Orchestrator(LO).\n"
    echo -e "options:"
    echo -e "\t-a:   (default) create all the images and containers"
    echo -e "\t-g:   create the image and a default container from ESCAPE as a MdO"
    echo -e "\t-l:   create the image and the specific container from ESCAPE as a LO"
    echo -e "\t-h:   print this help message"
    exit 2
}

if [ $# -eq 0 ]; then
    # No param was given
    all
else
    while getopts 'aglh' OPTION; do
        case ${OPTION} in
        a)  all;;
        g)  mdo;;
        l)  lo;;
        h)  print_usage;;
        \?)  print_usage;;
        esac
    done
    #shift $(($OPTIND - 1))
fi