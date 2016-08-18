#!/usr/bin/env bash

# Init script for docker container
echo -e "Check necessary services...\n"

if [ -f /etc/init.d/neo4j-service ]; then
    if ! pgrep -af neo4j; then
        sudo service neo4j-service start
    fi
fi

# Skip in case of ESCAPE MdO
if [ -f /etc/init.d/ssh ]; then
    if ! pgrep -af sshd; then
        sudo service ssh start
    fi
fi

# Skip in case of ESCAPE MdO
if [ -f /etc/init.d/openvswitch-switch ]; then
    if ! pgrep -af ovs-vswitchd; then
        sudo service openvswitch-switch start
    fi
fi