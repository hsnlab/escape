#!/usr/bin/env bash

echo -e "\n======================================================================"
echo -e "==                       RUN TEST CASES                              =="
echo -e "======================================================================\n"

cd ..
for dir in ./test/case[0-9][0-9]; do
    bash -vc "$dir/run.sh"
done