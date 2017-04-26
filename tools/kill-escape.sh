#!/usr/bin/env bash
# Kill running ESC process(es) and clear remained subprocesses/files/infs

pgrep -af "escape.py"
# -S read password from STDIN - but it will be shown on console in PyCharm!
sudo -S pkill -f "escape.py"
sudo -S ./escape.py -x