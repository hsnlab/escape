#!/usr/bin/env bash

sudo apt-get install maven
git clone https://github.com/jgrajos/netphony-network-protocols.git
cd netphony-network-protocols
git checkout feature/BGPLS-IT-v2
mvn install
cd ..
#git clone git@5gexgit.tmit.bme.hu:ogd/netphony-topology.git
git submodule update --recursive
cd netphony-topology
mvn clean package -P generate-full-jar -P bgp-ls-speaker assembly:single