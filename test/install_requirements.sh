#!/usr/bin/env sh

#SHELL_DEPS="sudo net-tools"
#
#if type apt >> /dev/null; then
#    sudo apt-get install -y ${SHELL_DEPS}
#elif type apk >> /dev/null; then
#    apk add ${SHELL_DEPS}
#fi
pip install pexpect unittest-xml-reporting pyyaml requests