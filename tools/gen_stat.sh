#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR=$( dirname "$DIR" )
echo "Project dir: $PROJECT_DIR"
CLOC="$DIR/cloc-1.72.pl"
if [ ! -f ${CLOC} ]; then
    echo "Missing script: $CLOC --> Download from https://github.com/AlDanial/cloc"
    cd ${DIR}
    wget https://github.com/AlDanial/cloc/releases/download/v1.72/cloc-1.72.pl
    chmod a+x ${CLOC}
    cd -
fi
echo "Source code stat:"
${CLOC} --unicode --exclude-ext=config,xml,json,nffg \
    --exclude-dir=mininet,pox,OpenYuma,netphony-topology,build \
    --not-match-f=cloc-.*.pl ${PROJECT_DIR}
