#!/usr/bin/env bash

if [ ! -d netphony-network-protocols ]; then
    pushd
    sudo apt-get update && sudo apt-get install maven
    git clone https://github.com/jgrajos/netphony-network-protocols.git
    cd netphony-network-protocols
    git checkout feature/BGPLS-IT-v2
    mvn install
    popd
fi
git submodule update --init --recursive --merge --remote
cd netphony-topology
mvn clean package -P generate-full-jar -P bgp-ls-speaker assembly:single