#!/bin/bash

function print_help
{
  echo -e $1
  echo -e "Usage: ./createVxlanBridge.sh <tunnel_remote_ip>"
  exit -1
}

if [ $# -ne 1 ]
then
  print_help "Not enough parameters"
fi


remoteIP=$1

#Create veth interfaces
sudo ip link add veth0 type veth peer name veth1
sudo ifconfig veth0 up
sudo ifconfig veth1 up

#Create Vxlan OVS
sudo ovs-vsctl add-br br-vxlan
sudo ovs-vsctl add-port br-vxlan vxlan -- set Interface vxlan type=vxlan options:remote_ip=${remoteIP}
sudo ovs-vsctl add-port br-vxlan veth1

#Add entries
sudo ovs-ofctl del-flows br-vxlan
sudo ovs-ofctl add-flow br-vxlan in_port=1,action=output:2
sudo ovs-ofctl add-flow br-vxlan in_port=2,action=output:1

