#!/usr/bin/env bash

echo -e "\n======================================================================"
echo -e "==                        TEST CASE 1                               =="
echo -e "======================================================================\n"

# sudo ./escape.py --debug --test --quit --log test/case1/escape.log --full --mininet test/case1/mn-topology.nffg --service test/case1/request.nffg
sudo ./escape.py --debug --test --quit --log test/case01/escape.log --full --config test/case01/test.config --service test/case01/request.nffg