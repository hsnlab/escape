#!/usr/bin/env python
__author__ = 'David Jocha'
__copyright__ = 'Copyright Ericsson Hungary Ltd 2015'

__maintainer__ = 'David Jocha'
__email__ = 'david.jocha@ericsson.com'

import logging
import urllib2

import nffglib

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
LOG.propagate = False
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
f = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
sh.setFormatter(f)
LOG.addHandler(sh)


def main():
    LOG.debug('Get help page')
    url = 'http://127.0.0.1:8080'
    # by default a GET request is created:
    req = urllib2.Request(url)
    response = urllib2.urlopen(req)
    LOG.debug('Response: %s', response.read())


    LOG.debug('Query infrastructure')
    url = 'http://127.0.0.1:8080/get-config'
    # need the empty second parameter to create a POST request (and not a GET):
    req = urllib2.Request(url, '')
    response = urllib2.urlopen(req)
    infrastructure_xml = response.read()
    LOG.debug('Received infrastructure: %s', infrastructure_xml)

    LOG.debug('Parse infrastructure')
    infrastructure = nffglib.Virtualizer.parse(text=infrastructure_xml)
    LOG.debug('Parsed infrastructure to: %s', infrastructure)


    LOG.debug('Edit infrastructure')
    # get existing elements:
    infranode = infrastructure.c_nodes.list_node[0]; """:type : nffglib.InfraNodeGroup""" # assuming there is at least one node
    flowtablegroup = infranode.g_flowtable;
    infraport0 = infranode.g_node.c_ports.list_port[0]
    infraport1 = infranode.g_node.c_ports.list_port[1] # assuming node has two ports
    supported_nf = infranode.c_capabilities.g_capabilities.c_supportedNFs.list_node[0]; """:type : nffglib.NodeGroup""" # assuming there is at least one supported nf by the node

    # create new elements & insert to object structure:
    nfinstances = nffglib.NFInstances(infranode)
    infranode.c_NFInstances = nfinstances

    nf = nffglib.NodeGroup(nfinstances)
    nfinstances.list_node.append(nf)

    nfidt = nffglib.IdNameTypeGroup(nf)
    nf.g_idNameType = nfidt

    nfid = nffglib.IdNameGroup(nfidt)
    nfidt.g_idName = nfid

    nfports = nffglib.Ports(nf)
    nf.c_ports = nfports

    nfport1 = nffglib.PortGroup(nfports)
    nfports.list_port.append(nfport1)

    nfportid1 = nffglib.IdNameGroup(nfport1)
    nfport1.g_idName = nfportid1

    nfporttype1 = nffglib.PortTypeGroup(nfport1)
    nfport1.g_portType = nfporttype1

    nfport2 = nffglib.PortGroup(nfports)
    nfports.list_port.append(nfport2)

    nfportid2 = nffglib.IdNameGroup(nfport2)
    nfport2.g_idName = nfportid2

    nfporttype2 = nffglib.PortTypeGroup(nfport2)
    nfport2.g_portType = nfporttype2

    flowtable = nffglib.FlowTable(flowtablegroup)
    flowtablegroup.c_flowtable = flowtable

    flowentry1 = nffglib.FlowEntry(flowtable)
    flowtable.list_flowentry.append(flowentry1)

    flowentry2 = nffglib.FlowEntry(flowtable)
    flowtable.list_flowentry.append(flowentry2)

    # configure elements:
    nfid.l_id = 'NF1'
    nfid.l_name = 'example NF'
    nfidt.l_type = supported_nf.g_idNameType.l_type

    nfportid1.l_id = supported_nf.c_ports.list_port[0].g_idName.l_id
    nfportid1.l_name = 'Example NF input port'
    nfporttype1.l_portType = supported_nf.c_ports.list_port[0].g_portType.l_portType

    nfportid2.l_id = supported_nf.c_ports.list_port[1].g_idName.l_id
    nfportid2.l_name = 'Example NF output port'
    nfporttype2.l_portType = supported_nf.c_ports.list_port[1].g_portType.l_portType

    # from first port of node to NF input:
    flowentry1.l_port = '../../ports/port[id=' + infraport0.g_idName.l_id + ']'
    flowentry1.l_match = ''
    flowentry1.l_action = 'output:../../NF_instances/node[id=' + nfid.l_id + ']/ports/port[id=' + nfportid1.l_id + ']'

    # from NF output to second port of node, with MAC src rewrite:
    flowentry2.l_port = '../../NF_instances/node[id=' + nfid.l_id + ']/ports/port[id=' + nfportid2.l_id + ']'
    flowentry2.l_match = ''
    flowentry2.l_action = 'output:../../ports/port[id=' + infraport1.g_idName.l_id + '];mod_dl_src=12:34:56:78:90:12'

    requested_config_xml = infrastructure.xml()

    LOG.debug('Send new config')
    url = 'http://127.0.0.1:8080/edit-config'
    req = urllib2.Request(url, requested_config_xml)
    response = urllib2.urlopen(req)
    LOG.debug('Requested config sent %s', response.read())


if __name__ == '__main__':
    main()
