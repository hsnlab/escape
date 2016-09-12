#!/usr/bin/env bash

cd netphony-topology
if [ "$#" -eq 0 ]; then
	java -Dlog4j.configurationFile=log4j2.xml \
	    -jar target/topology-1.3.2-shaded.jar \
	    src/main/sample-config-files/TMConfiguration_BGPLSreader_UNIFYwriter.xml
else
	java -Dlog4j.configurationFile=log4j2.xml -jar target/topology-1.3.2-shaded.jar $@
fi
