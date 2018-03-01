#!/usr/bin/env bash
# Copyright 2018 Janos Czentye
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

RESTART_VALUE=42
UPDATE_VALUE=142
STOP_VALUE=242

function update() {
    echo "Updating ESCAPE source base..."
    git pull
    git submodule update
}

while true
do
    echo "Received params: $@"
    python escape.py ${@}
    ret_value=${?}
    echo "Received exit code from ESCAPE: $ret_value"
    if [ ${ret_value} -eq ${RESTART_VALUE} ]; then
        echo "Restarting..."
    elif [ ${ret_value} -eq ${UPDATE_VALUE} ]; then
        update
    elif [ ${ret_value} -eq ${STOP_VALUE} ]; then
        python start_waiter.py ${@}
        if [ ${?} -ne 0 ]; then
            exit -1
        fi
    else
        echo "Exit."
        exit 0
    fi
    echo "Restarting ESCAPE..."
    sleep 2
done