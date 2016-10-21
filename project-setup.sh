#!/usr/bin/env bash

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
    echo -e "Usage: $0 [project]"
    echo -e "Setup submodules according to given project for ESCAPE.\n"
    echo -e "parameters:"
    echo -e "\t project: setup project [sb|5gex]"
    exit 0
}

function setup () {
    info "==== Set project module file ===="
    if [ -f ".gitmodules.$PROJECT" ]; then
        # Create symlink for main repo
        ln -vfs .gitmodules.${PROJECT} .gitmodules
        # Sync to other project
        git submodule sync
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
    git submodule update --remote --recursive

    info "=== Init submodules recursively ==="
    # Add symlink to the referenced submodules and init them
    for dir in "dummy-orchestrator" "mapping"; do
        echo -en "$ROOT_DIR/$dir\t\t\t"
        cd ${dir}
        if [ -f ".gitmodules.$PROJECT" ]; then
            ln -vfs .gitmodules.${PROJECT} .gitmodules
        else
            on_error "Missing submodule file of project: $PROJECT for repo: $dir!"
        fi
        git submodule init
        cd ..
    done

    info "=== Sync and update submodules recursively ==="
    # Sync and update all the submodules
    git submodule sync --recursive
    git submodule update --remote --recursive --merge

    info "=== Defined submodules ==="
    git submodule status --recursive
}

if [ $# -lt 1 ]; then
    print_help
fi
# Read initial parameters
PROJECT=$1

# START script here

info "Project: $PROJECT\n"
cd ${ROOT_DIR}
setup
