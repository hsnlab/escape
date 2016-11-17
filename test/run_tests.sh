#!/usr/bin/env bash

echo -e "\n======================================================================"
echo -e "==                       RUN TEST CASES                              =="
echo -e "======================================================================\n"

cd ..
for dir in ./test/case[0-9][0-9]; do
    echo "$dir/run.sh"
    bash -vc "$dir/run.sh"
done