#!/usr/bin/env bash

# Init script for docker container
sudo service ssh start
sudo service neo4j-service start
sudo service openvswitch-switch start
/bin/bash