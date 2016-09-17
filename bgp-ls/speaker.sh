#!/usr/bin/env bash

if [ "$#" -eq 0 ]; then
	java -Dlog4j.configurationFile=log4j2.xml -jar bgp-ls-speaker-jar-with-dependencies.jar speaker-BGP4Parameters_1_esc.xml
else
	java -Dlog4j.configurationFile=log4j2.xml -jar bgp-ls-speaker-jar-with-dependencies.jar $@
fi
