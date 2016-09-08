#!/usr/bin/env bash

cd netphony-topology
if [ "$#" -eq 0 ]; then
	java -Dlog4j.configurationFile=log4j2.xml \
	    -jar target/bgp-ls-speaker-jar-with-dependencies.jar \
	    src/test/resources/BGP4Parameters_1.xml
else
	java -Dlog4j.configurationFile=log4j2.xml -jar target/bgp-ls-speaker-jar-with-dependencies.jar $@
fi
