#!/usr/bin/env bash
# Kill running ESC process(es) and clear remained subprocesses/files/infs

pgrep -af ESCAPE
# -S read password from STDIN - but it will be shown on console in PyCharm!
sudo -S pkill -f ESCAPE
sudo -S ./escape.py -x