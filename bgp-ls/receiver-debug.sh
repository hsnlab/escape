#!/usr/bin/env bash

if [ "$#" -eq 0 ]; then
	java -Dlog4j.configurationFile=log4j2-debug.xml -jar topology-1.3.2-shaded.jar receiver-TMConfig_esc.xml
else
	java -Dlog4j.configurationFile=log4j2-debug.xml -jar topology-1.3.2-shaded.jar $@
fi
