#!/usr/bin/env bash

function print_help {
    echo -e "Usage: $0  [-a tunnel_remote_ip] [-r]"
    echo -e "Setup VxLAN tunnel in OpenStack test environment\n"
    echo -e "options:"
    echo -e "\t-a:   setup VxLAN with the given remote tunnel address"
    echo -e "\t-r:   remove VxLAN related interfaces and veth pair"
    exit -1
}

function setup {
    sudo ovs-vsctl add-br br-vxlan
    sudo ovs-vsctl add-port br-vxlan vxlan42 -- set Interface vxlan42 type=vxlan options:remoe_ip=172.16.178.1

}

function shutdown {
    -
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