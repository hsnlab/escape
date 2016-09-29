#!/usr/bin/env bash

TM_JAR="target/topology-1.3.2-shaded.jar"
LOG4J=$(realpath "$PWD/log4j2-info.xml")

while getopts 'd' OPTION; do
    case ${OPTION} in
        d)
            # Set DEBUG logger config
            LOG4J=$(realpath "$PWD/log4j2-debug.xml")
            # Remove -d from command line arguments
            shift $((OPTIND-1))
            ;;
    esac
done

CONFIG=$(realpath "$1")
cd netphony-topology
sudo java -Dlog4j.configurationFile=${LOG4J} -jar ${TM_JAR} ${CONFIG}