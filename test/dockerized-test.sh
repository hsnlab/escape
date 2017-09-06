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

function print_help {
    echo -e "Run testcases in a docker container.\n"
    echo -e "Usage: $0 [-b] | ..."
    echo -e "Parameters:"
    echo -e "\t -b, --build   force to rebuild the Docker image"
    echo -e "\t -h, --help    show this help message and exit"
    echo -e "\t ...           runner parameters, see run_tests.py -h"
    echo -e "\nExample: $0 -b | $0 case15 -o"
    exit 2
}

IMAGE="escape-test"

function build {
    info "======================================================================"
    info "===                        Build test image                        ==="
    info "======================================================================"
    docker build --force-rm --no-cache -t ${IMAGE} -f testframework/Dockerfile ..
}

function run () {
    if [ -z $(docker images -q ${IMAGE} ) ]; then build; fi
    info "======================================================================"
    info "===                            Run tests                           ==="
    info "======================================================================"
    docker run --rm --volume "$PWD/../escape:/opt/escape/escape:ro" \
                    --volume "$PWD:/opt/escape/test" -ti ${IMAGE} ${@}
}

function clean () {
    info "======================================================================"
    info "===                             Cleanup                            ==="
    info "======================================================================"
    if [ ! -z $(docker images -q ${IMAGE} ) ]; then docker rmi ${IMAGE}; fi
    ../tools/clear_docker.sh
}

while getopts ':bch' OPTION; do
    case ${OPTION} in
        b|--build)  build && exit;;
        c|--clean)  clean && exit;;
        h)  print_help;;
    esac
done
run ${@}