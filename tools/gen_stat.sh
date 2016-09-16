#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR=$( dirname "$DIR" )
echo "Project dir: $PROJECT_DIR"
#cloc --unicode --exclude-ext=config,xml,json --exclude-dir=mininet,pox,OpenYuma,bgp-ls/netphony-topology,escape/doc  .. 
${DIR}/cloc-1.70.pl --unicode --exclude-ext=config,xml,json \
    --exclude-dir=mininet,pox,OpenYuma,netphony-topology,build \
    --not-match-f=cloc-.*.pl ${PROJECT_DIR}
