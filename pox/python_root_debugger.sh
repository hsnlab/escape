#!/bin/bash
# Workaround for PyCharm IDE to debug POX with root privilage
# sudo visudo --> czentye ALL = NOPASSWD: /usr/bin/python, /usr/bin/python2.7, /usr/bin/env
sudo python $@
