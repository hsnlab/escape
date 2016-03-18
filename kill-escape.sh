#!/usr/bin/env bash
# Kill running ESC process(es) and clear remained subprocesses/files/infs

pgrep -af "unify"
sudo pkill -f "unify"
sudo ./escape.py -x