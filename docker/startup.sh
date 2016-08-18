#!/usr/bin/env bash

# Init script for docker container
sudo service neo4j-service start

# Skip in case of ESCAPE MdO
if [ -f /etc/init.d/ssh ]; then
    sudo service ssh start
fi

# Skip in case of ESCAPE MdO
if [ -f /etc/init.d/openvswitch-switch ]; then
    sudo service openvswitch-switch start
fi