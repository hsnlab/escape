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
    echo -e "Example: ./set_virtualenv.sh -p 5gex"
    exit 0
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

info "Project: $PROJECT\n"
cd ${ROOT_DIR}
info "=== Deinit all the submodules ==="
git submodule deinit -f .
info "=== Resync main modules ==="
ln -vfs .gitmodules.${PROJECT} .gitmodules
git submodule sync
info "=== Recreate symlinks ==="
for dir in mapping dummy-orchestrator; do
    echo -en "$ROOT_DIR/$dir\t\t\t"
    cd ${ROOT_DIR}/${dir}
    ln -vfs .gitmodules.${PROJECT} .gitmodules
done

cd ${ROOT_DIR}
info "==== Sync submodules ===="
git submodule sync --recursive
info "=== Update submodules ==="
git submodule update --remote --recursive --merge --init
info "==== Submodules ===="
git submodule status --recursive