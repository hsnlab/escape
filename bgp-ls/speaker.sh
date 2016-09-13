#!/usr/bin/env bash

ROOT=$PWD
cd netphony-topology
if [ "$#" -eq 0 ]; then
	java -Dlog4j.configurationFile=log4j2.xml \
	    -jar target/bgp-ls-speaker-jar-with-dependencies.jar \
	    ${ROOT}/BGP4Parameters_1_esc.xml
else
	java -Dlog4j.configurationFile=log4j2.xml -jar target/bgp-ls-speaker-jar-with-dependencies.jar $@
fi
