#!/usr/bin/env bash

sudo apt-get update && sudo apt-get install maven
git submodule update --init --recursive --merge --remote
cd netphony-network-protocols
mvn install
cd ../netphony-topology
#mvn clean package -P generate-full-jar -P bgp-ls-speaker assembly:single
mvn clean package -P generate-full-jar