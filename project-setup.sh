#!/usr/bin/env bash

PROJECT=""
ROOT_DIR=$PWD

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

function info() {
    echo -e "${GREEN}$1${NC}"
}

function print_help {
    echo -e "Usage: $0 [-p project] [-h]"
    echo -e "Setup submodules according to given project for ESCAPE.\n"
    echo -e "optional parameters:"
    echo -e "\t-p:   setup project [sb|5gex]"
    echo -e "\t-h:   show this help message and exit"
    exit 0
}

function setup () {
    # git submodule deinit -f .

    info "==== Init top submodules ===="
    # Create symlink for main repo
    ln -vfs .gitmodules.${PROJECT} .gitmodules
    # Init submodules
    git submodule update --init --recursive

    if [ ${PROJECT} = "sb" ]; then
        info "=== Deinit unnecessary modules ==="
        # Deinit only 5GEx submodules
        for i in bgp-ls/netphony-topology bgp-ls/netphony-network-protocols tnova_connector; do
            git submodule deinit ${i}
        done
    fi

    info "==== Sync and update top submodules ===="
    # Sync and update top submodules
    git submodule sync --recursive
    git submodule update --remote

    info "=== Init submodules recursively ==="
    # Add symlink to the referenced submodules and init them
    for dir in "dummy-orchestrator" "mapping"; do
        echo -en "$ROOT_DIR/$dir\t\t\t"
        cd ${dir}
        ln -vfs .gitmodules.${PROJECT} .gitmodules
        git submodule init
        cd ..
    done

    info "=== Sync and update  submodules recursively ==="
    # Sync and update all the submodules
    git submodule sync --recursive
    git submodule update --remote --recursive

    info "=== Defined submodules ==="
    git submodule status --recursive
}

if [ $# -lt 1 ]; then
    print_help
fi
# Read initial parameters
while getopts "p:h" OPTION; do
    case ${OPTION} in
        p)
            PROJECT=${OPTARG};;
        h)
            print_help;;
    esac
done

# START script here

info "Project: $PROJECT\n"
cd ${ROOT_DIR}
setup
