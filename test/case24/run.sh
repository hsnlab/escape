#!/usr/bin/env sh

## Test case header - START
# Get directory path of current test case
CWD="$(dirname $(readlink -f "$0"))"
# Get test case name
TEST_CASE="$( basename ${CWD} | tr '[:lower:]' '[:upper:]' )"
# Get ESCAPE command
ESCAPE="$( readlink -f ${CWD}/../../escape.py )"
if which time >> /dev/null; then
    RUN_WITH_MEASUREMENT="$(which time) -v"
elif which bash >> /dev/null; then
    RUN_WITH_MEASUREMENT=""
fi
# Print header
echo
echo "==============================================================================="
echo "==                             TEST $TEST_CASE                                   =="
echo "==============================================================================="
echo
# Print test case description
cat ${CWD}/README.txt
echo
echo "=============================== START TEST CASE ==============================="
echo
## Test case header - END

# Define run command here
ESCAPE_CMD="${ESCAPE} --debug --test --quit --log ${CWD}/escape.log \
            --config ${CWD}/test.config --service ${CWD}/sapalias-antiaff-req2.nffg"

# Invoke ESCAPE with test parameters
${RUN_WITH_MEASUREMENT} ${ESCAPE_CMD} $@

## Test case footer - START
echo
echo "===================================== END ====================================="
echo
## Test case footer - END