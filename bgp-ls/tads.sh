#!/usr/bin/env bash

CONFIG=$(realpath "$1")
LOG4J=$(realpath "$PWD/netphony-topology/target/log4j2.xml")
cd netphony-topology
sudo java -Dlog4j.configurationFile=${LOG4J} -jar target/topology-1.3.2-shaded.jar ${CONFIG}
