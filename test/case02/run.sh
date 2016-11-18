#!/usr/bin/env bash

CWD="test/case02"

echo -e "\n======================================================================"
echo -e "==                        TEST CASE 2                               =="
echo -e "======================================================================\n"

sudo ./escape.py --debug --test --quit --log ${CWD}/escape.log --full --config ${CWD}/test.config --service ${CWD}/request.nffg