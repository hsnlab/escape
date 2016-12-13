#!/usr/bin/env bash

## Test case header - START
# Get directory path of current test case
CWD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get test case name
TEST_CASE="$( basename ${CWD} | tr '[:lower:]' '[:upper:]' )"
# Get ESCAPE command
ESCAPE="$( readlink -f ${CWD}/../../escape.py )"
# Print header
echo -e "\n==============================================================================="
echo -e "==                             TEST $TEST_CASE                                   =="
echo -e "===============================================================================\n"

# Print test case description
cat ${CWD}/README.txt
echo -e "\n===============================================================================\n"
echo
## Test case header - END

# Print test case description
cat ${CWD}/README.txt
echo -e "\n=============================== START TEST CASE ===============================\n"
echo
## Test case header - END

# Define run command here
ESCAPE_CMD="sudo ${ESCAPE} --debug --test --quit --log ${CWD}/escape.log --full \
                --config ${CWD}/test.config --service ${CWD}/request.nffg"

# Invoke ESCAPE with test parameters
time ${ESCAPE_CMD} $@

## Test case footer - START
echo -e "\n===================================== END =====================================\n"
## Test case footer - END