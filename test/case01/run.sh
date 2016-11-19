#!/usr/bin/env bash

CWD="test/case01"

echo -e "\n======================================================================"
echo -e "==                        TEST CASE 1                               =="
echo -e "======================================================================\n"

# sudo ./escape.py --debug --test --quit --log  $CWD/escape.log  --full --mininet $CWD/mn-topology.nffg --service $CWD/request.nffg
sudo ./escape.py --debug --test --quit --log ${CWD}/escape.log --full --config ${CWD}/test.config --service ${CWD}/request.nffg