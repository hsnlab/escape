#!/usr/bin/env bash

echo -e "\n======================================================================"
echo -e "==                         RUN TEST CASES                           =="
echo -e "======================================================================\n"

BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

trap ctrl_c INT

function ctrl_c() {
        echo "Received CTRL-C from user! Abort overall testing..."
        exit 0
}

# Enter project root
cd ${BASE_DIR}/..

# Invoke test cases relative to project root
for dir in ./test/case[0-9][0-9]; do
    bash -vc "$dir/run.sh"
done