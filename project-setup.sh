#!/usr/bin/env bash
# Copyright 2017 Janos Czentye
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

PROJECT=""
ROOT_DIR=$PWD

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

function info() {
    echo -e "${GREEN}$1${NC}"
}

function on_error() {
    echo -e "\n${RED}Error during installation! ${1-}${NC}"
    exit 1
}

function print_help {
    echo -e "Setup submodules according to given project for ESCAPEe."
    echo -e "If project name is not given the script tries to detect it"
    echo -e "from the git's local configurations.\n"
    echo -e "Usage: $0 [-h] [-p project]"
    echo -e "Parameters:"
    echo -e "\t -h, --help      show this help message and exit"
    echo -e "\t -p, --project   setup project name based on: .gitmodules.<name>"
    echo -e "\nExample: $0 -p 5gex"
    exit 2
}

function setup () {
    info "==== Set project module file ===="
    if [ -f ".gitmodules.$PROJECT" ]; then
        # Create symlink for main repo
        ln -vfs .gitmodules.${PROJECT} .gitmodules
        # Sync to other project
    else
        on_error "Missing submodule file of project: $PROJECT for repo: $ROOT_DIR!"
    fi

    info "=== Reinitialize existing submodules ==="
    git submodule deinit -f .
    git submodule init

    info "=== Deinit unnecessary modules ==="
    if [ ${PROJECT} = "sb" ]; then
        # Deinit only 5GEx submodules
        for i in bgp-ls/netphony-topology bgp-ls/netphony-network-protocols tnova_connector; do
            git submodule deinit -f ${i}
        done
    fi

    info "=== Clone top submodules ==="
    # Clone top submodules with default submodule
#    git submodule update --remote
    git submodule update    # Following commits

    info "=== Init submodules recursively ==="
    # Add symlink to the referenced submodules and init them
    for dir in "mapping"; do
        echo -en "$ROOT_DIR/$dir\t\t\t"
        cd ${dir}
        if [ -f ".gitmodules.$PROJECT" ]; then
            ln -vfs .gitmodules.${PROJECT} .gitmodules
        else
            on_error "Missing submodule file of project: $PROJECT for repo: $dir!"
        fi
        cd ..
    done

    info "=== Sync and update submodules recursively ==="
    # Sync and update all the submodules
    git submodule foreach git submodule init
#    git submodule update --remote --recursive --merge
    git submodule update    # Following commits

    info "=== Defined submodules ==="
    git submodule status --recursive
}

while getopts ':hp:' OPTION; do
    case ${OPTION} in
        p|--project)  PROJECT=$OPTARG;;
        h)  print_help;;
    esac
done

# START script here
if [ -z ${PROJECT} ]; then
    echo "Detecting project name..."
    origin_url=$(git config --get remote.origin.url)

    if [[ ${origin_url} == *"sb.tmit.bme.hu"* ]]; then
        PROJECT="sb"
    elif [[ ${origin_url} == *"5gexgit.tmit.bme.hu"* ]]; then
        PROJECT="5gex"
    elif [[ ${origin_url} == *"213.16.101.153"* ]]; then
        PROJECT="ericsson"
    elif [[ ${origin_url} == *"github.com:hsnlab"* ]]; then
        PROJECT="hsnlab"
    elif [[ ${origin_url} == *"github.com:5GExchange"* ]]; then
        PROJECT="5gexchange"
    else
        on_error "Repo URL is not recognized: $origin_url!"
    fi
fi
info "Project: $PROJECT\n"
cd ${ROOT_DIR}
setup