#!/usr/bin/env bash

cloc --unicode --exclude-ext=config,xml,json --exclude-dir=mininet,pox,OpenYuma,bgp-ls/netphony-topology,escape/doc  .. 
