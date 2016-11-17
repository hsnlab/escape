#!/usr/bin/env bash
# Copyright 2016 Mark Szalai <szalay91@gmail.com> Janos Czentye <czentye@tmit.bme.hu>
# Setup VxLAN-based tunnel between two VM our OpenStack environment

BRIDGE="br-vxlan"
# veth pain names in array: [pair1_ovs, pair1_mininet, pair2_ovs, pair2_mininet, ...]
VETHS=(vxlan_sap14 sap14_veth)

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
    # Save IP parameter
    remoteIP=$1
    echo "------------------------------------------------------------------"
    # Create Vxlan OVS
    echo "Add OVS bridge: $BRIDGE"
    sudo ovs-vsctl add-br ${BRIDGE}
    # Add VXLAN interface to bridge --> create vxlan_sys_ interface and add to bridge as port 1
    sudo ovs-vsctl add-port ${BRIDGE} vxlan -- set Interface vxlan type=vxlan options:remote_ip=${remoteIP}
    # Remove default flow
    sudo ovs-ofctl del-flows ${BRIDGE}
    # Create veth pairs and connect them to the VXLAN interface
    VXLAN_OVS_PORT=1
    veth_port_cntr=2
    for ((i=0; i<${#VETHS[@]}; i+=2)); do
        echo "------------------------------------------------------------------"
        # Create veth pairs
        echo "Add veth pair: ${VETHS[$i]} <--> ${VETHS[$((i+1))]}"
        sudo ip link add "${VETHS[$i]}" type veth peer name "${VETHS[$((i+1))]}"
        # Bring up created interfaces
        echo "Bring up interface: ${VETHS[$i]}"
        sudo ifconfig "${VETHS[$i]}" up
        echo "Bring up interface: ${VETHS[$((i+1))]}"
        sudo ifconfig "${VETHS[$((i+1))]}" up
        echo "Add veth end: ${VETHS[$i]} to bridge: $BRIDGE"
        sudo ovs-vsctl add-port ${BRIDGE} "${VETHS[$i]}"
        echo "Add flowrules between OVS ports: ${VXLAN_OVS_PORT} <--> ${veth_port_cntr}"
        sudo ovs-ofctl add-flow ${BRIDGE} in_port=${VXLAN_OVS_PORT},action=output:${veth_port_cntr}
        sudo ovs-ofctl add-flow ${BRIDGE} in_port=${veth_port_cntr},action=output:${VXLAN_OVS_PORT}
        # Increase veth port counter
        ((veth_port_cntr++))
        echo "------------------------------------------------------------------"
    done
    # Dump configures OVS bridge
    sudo ovs-ofctl show ${BRIDGE}
    echo "------------------------------------------------------------------"
    sudo ovs-ofctl dump-flows ${BRIDGE}
}

function shutdown {
    echo "Remove OVS bridge: $BRIDGE"
    sudo ovs-vsctl del-br ${BRIDGE}
    #Create veth interfaces
    for ((i=0; i<${#VETHS[@]}; i+=2)); do
        echo "Remove veth pair: ${VETHS[$i]} <--> ${VETHS[$((i+1))]}"
        sudo ip link del "${VETHS[$i]}"
    done
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