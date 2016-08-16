#!/bin/bash
# Workaround for PyCharm IDE to debug POX with root privilege
# sudo visudo --> czentye ALL = NOPASSWD: /usr/bin/python, /usr/bin/python2.7,
# /usr/bin/python3.4, /usr/bin/env
sudo python $@
