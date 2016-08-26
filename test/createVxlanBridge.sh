#!/usr/bin/env bash
# Copyright 2016 Mark Szalai <szalay91@gmail.com> Janos Czentye <czentye@tmit.bme.hu>
# Setup VxLAN-based tunnel between two VM our OpenStack environment

BRIDGE="br-vxlan"
VETHS=(vxlan_sap14 veth_sap14)

function print_help
{
    echo -e "Usage: $0  [-a tunnel_remote_ip] [-r]"
    echo -e "Setup VxLAN tunnel in OpenStack test environment\n"
    echo -e "options:"
    echo -e "\t-a:   setup VxLAN with the given remote tunnel address"
    echo -e "\t-r:   remove VxLAN related interfaces and veth pair"
    exit -1
}

function setup () {
    remoteIP=$1

    #Create veth interfaces
    for ((i=0; i<${#VETHS[@]}; i+=2)); do
        echo "Add veth pair: ${VETHS[$i]} - ${VETHS[$((i+1))]}"
        sudo ip link add "${VETHS[$i]}" type veth peer name "${VETHS[$((i+1))]}"
    done
    for veth in "${VETHS[@]}"; do
        echo "Bring up interfaces: $veth"
        sudo ifconfig ${veth} up
    done

    #Create Vxlan OVS
    echo "Add OVS bridge: $BRIDGE"
    sudo ovs-vsctl add-br ${BRIDGE}
    sudo ovs-vsctl add-port ${BRIDGE} vxlan -- set Interface vxlan type=vxlan options:remote_ip=${remoteIP}
    for ((i=0; i<${#VETHS[@]}; i+=2)); do
        echo "Add veth end: ${VETHS[$i]} to bridge: $BRIDGE"
        sudo ovs-vsctl add-port ${BRIDGE} "${VETHS[$i]}"
    done

    #Add entries
    sudo ovs-ofctl del-flows ${BRIDGE}
    # TODO get smarter!!!!!!!!!!!
    sudo ovs-ofctl add-flow ${BRIDGE} in_port=1,action=output:2
    sudo ovs-ofctl add-flow ${BRIDGE} in_port=2,action=output:1

    sudo ovs-ofctl dump-flows ${BRIDGE}
}

function shutdown {
        #Create veth interfaces
    for ((i=0; i<${#VETHS[@]}; i+=2)); do
        echo "Remove veth pair: ${VETHS[$i]}-${VETHS[$((i+1))]}"
        sudo ip link del "${VETHS[$i]}"
    done
    echo "Remove OVS bridge: $BRIDGE"
    sudo ovs-vsctl del-br ${BRIDGE}
    echo "Remove VXLAN interface"
    sudo ip link del $(ip link show | egrep -o '(vxlan_\w+)')
}

if [ $# -eq 0 ]; then
    print_help
else
    while getopts 'a:r' OPTION; do
        case ${OPTION} in
            a)  setup $OPTARG ;;
            r)  shutdown;;
            \?)  print_help;;
         esac
     done
fi