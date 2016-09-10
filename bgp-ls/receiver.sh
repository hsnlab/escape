#!/usr/bin/env bash

ROOT=$PWD
cd netphony-topology
if [ "$#" -eq 0 ]; then
	java -Dlog4j.configurationFile=log4j2.xml \
	    -jar target/topology-1.3.2-shaded.jar \
	    ${ROOT}/TMConfig_esc.xml
else
	java -Dlog4j.configurationFile=log4j2.xml -jar target/topology-1.3.2-shaded.jar $@
fi
