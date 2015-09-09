#!/usr/bin/env python

__author__ = 'Janos Elek'
__copyright__ = 'Copyright Ericsson Hungary Ltd 2015'
__license__ = 'Unify project internal usage'
__credits__ = ['Janos Elek', 'David Jocha', 'Robert Szabo']
__maintainer__ = 'David Jocha'
__email__ = 'david.jocha@ericsson.com'

import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
import re

# unify_ns = "{urn:unify:virtualizer}"
unify_ns = ""

Delete = 'delete'
Default = 'default'


class base(object):
    def __init__(self, parent=None):
        self.operation = Default
        self.parent = parent


class InvalidXML(Exception):
    pass


class IdNameGroup(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.l_id = ""
        """:type: str"""
        self.l_name = ""
        """:type: str"""

    @classmethod
    def parse(cls, root, parent):
        idNameGroup = cls(parent)

        e_id = root.find(unify_ns + "id")
        if e_id is None:
            raise InvalidXML("No id element in id-name group")
        idNameGroup.l_id = e_id.text

        e_name = root.find(unify_ns + "name")
        if e_name is None:
            idNameGroup.l_name = None
            # name should be optional
            # raise InvalidXML("No name element in id-name group")
        else:
            idNameGroup.l_name = e_name.text  # theNFFG

        return idNameGroup

    def xml(self, e_root):
        if self.l_id:
            e_id = ET.SubElement(e_root, "id")
            e_id.text = self.l_id
        if self.l_name:
            e_name = ET.SubElement(e_root, "name")
            e_name.text = self.l_name


class IdNameTypeGroup(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.g_idName = None
        """:type: IdNameGroup"""
        self.l_type = ""
        """:type: str"""

    @classmethod
    def parse(cls, e_node, parent):
        intGrp = cls(parent)

        intGrp.g_idName = IdNameGroup.parse(e_node, intGrp)

        e_type = e_node.find(unify_ns + "type")
        if e_type is None:
            intGrp.l_type = None
            # type should be optional
            # raise InvalidXML("No type given")
        else:
            intGrp.l_type = e_type.text

        return intGrp

    def xml(self, e_root):
        self.g_idName.xml(e_root)
        if self.l_type:
            e_type = ET.SubElement(e_root, "type")
            e_type.text = self.l_type


class PortTypeGroup(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.l_portType = ""
        """:type: str"""
        self.parent = parent
        """:type: """

    @classmethod
    def parse(cls, e_port, parent):
        pType = None
        portType = e_port.find(unify_ns + "port_type")
        if portType is None:
            raise InvalidXML("No port type given")

        if portType.text == "port-abstract":
            pType = PortAbstractCase.parse(e_port, parent)

        if portType.text == "port-sap":
            pType = PortSapCase.parse(e_port, parent)

        if pType is None:
            raise InvalidXML("Unknown port type")

        pType.l_portType = portType.text
        return pType

    def xml(self, e_port):
        e_portType = ET.SubElement(e_port, unify_ns + "port_type")
        e_portType.text = self.l_portType


class PortAbstractCase(PortTypeGroup):
    def __init__(self, parent):
        PortTypeGroup.__init__(self, parent)
        self.l_capability = ""
        """:type: str"""

    @classmethod
    def parse(cls, e_port, parent):
        abstractCase = cls(parent)
        e_cap = e_port.find("capability")
        if e_cap is not None:
            abstractCase.l_capability = e_cap.text
        return abstractCase

    def xml(self, e_port):
        super(PortAbstractCase, self).xml(e_port)
        e_capability = ET.SubElement(e_port, "capability")
        e_capability.text = self.l_capability


class PortGroup(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.g_idName = None
        """:type: IdNameGroup"""
        self.g_portType = None
        """:type: PortTypeGroup"""

    @classmethod
    def parse(cls, e_port, parent):
        portGrp = cls(parent)
        portGrp.g_idName = IdNameGroup.parse(e_port, portGrp)
        portGrp.g_portType = PortTypeGroup.parse(e_port, portGrp)
        return portGrp

    def xml(self, e_port):
        self.g_idName.xml(e_port)
        self.g_portType.xml(e_port)


class PortSapCase(PortTypeGroup):
    """
    Representing the choice of various types of SAPs.
    Currently contains vx-lan type. Can be extended with other types.
    """

    def __init__(self, parent):
        PortTypeGroup.__init__(self, parent)
        self.l_sapType = ""
        """:type: str"""

    @classmethod
    def parse(cls, e_port, parent):
        sType = None
        sapType = e_port.find(unify_ns + "sap-type")
        if sapType is None:
            raise InvalidXML("No SAP type given")

        if sapType.text == "vx-lan":
            sType = PortSapVxlanCase.parse(e_port, parent)

        if sType is None:
            raise InvalidXML("Unknown SAP type")

        sType.l_sapType = sapType.text
        return sType


class PortSapVxlanCase(PortSapCase):
    """
    Representing the vx-lan type SAP case.
    """

    def __init__(self, parent):
        PortSapCase.__init__(self, parent)
        self.g_portSapVxlan = None
        """:type: PortSapVxlanGroup"""

    @classmethod
    def parse(cls, e_port, parent):
        sapVxlanCase = cls(parent)
        sapVxlanCase.g_portSapVxlan = PortSapVxlanGroup.parse(e_port, sapVxlanCase)
        return sapVxlanCase

    def xml(self, e_port):
        super(PortSapCase, self).xml(e_port)
        e_sapType = ET.SubElement(e_port, "sap-type")
        e_sapType.text = self.l_sapType
        PortSapVxlanGroup.xml(self.g_portSapVxlan, e_port)


class PortSapVxlanGroup(base):
    """
    Representing the internals of the vx-lan type SAP.
    """

    def __init__(self, parent):
        base.__init__(self, parent)
        self.l_vxlan = ""
        """:type: str"""

    @classmethod
    def parse(cls, e_port, parent):
        sapVxlanGrp = cls(parent)
        e_vxlan = e_port.find(unify_ns + "vxlan")
        sapVxlanGrp.l_vxlan = e_vxlan.text
        return sapVxlanGrp

    def xml(self, e_port):
        e_vxlan = ET.SubElement(e_port, "vxlan")
        e_vxlan.text = self.l_vxlan





class LinkResourceGroup(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.l_delay = ""
        """:type: str"""
        self.l_bandwidth = ""
        """:type: str"""

    @classmethod
    def parse(cls, e_resource, parent):
        linkResGrp = cls(parent)

        if e_resource is not None:
            e_delay = e_resource.find(unify_ns + "delay")
            if e_delay is not None:
                linkResGrp.l_delay = e_delay.text

            e_bandwidth = e_resource.find(unify_ns + "bandwidth")
            if e_bandwidth is not None:
                linkResGrp.l_bandwidth = e_bandwidth.text

        return linkResGrp

    def xml(self, e_linkRes):
        if self.l_delay:
            e_delay = ET.SubElement(e_linkRes, "delay")
            e_delay.text = self.l_delay
        if self.l_bandwidth:
            e_bandwidth = ET.SubElement(e_linkRes, "bandwidth")
            e_bandwidth.text = self.l_bandwidth


class LinkResource(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.g_linkResource = None
        """:type: LinkResourceGroup"""

    @classmethod
    def parse(cls, e_resource, parent):
        linkRes = cls(parent)
        linkRes.g_linkResource = LinkResourceGroup.parse(e_resource, linkRes)
        return linkRes

    def xml(self):
        if self.g_linkResource:
            e_linkRes = ET.Element(unify_ns + "resources")
            self.g_linkResource.xml(e_linkRes)
            return e_linkRes
        else:
            return None


class FlowEntry(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.l_port = ""
        """:type: str"""
        self.l_match = ""
        """:type: str"""
        self.l_action = ""
        """:type: str"""
        self.c_resources = None
        """:type: LinkResource"""

    @classmethod
    def parse(cls, e_flowEntry, parent):
        flowEntry = cls(parent)

        if 'operation' in e_flowEntry.attrib:
            if e_flowEntry.attrib['operation'] == 'delete':
                flowEntry.operation = Delete

        e_port = e_flowEntry.find(unify_ns + "port")
        if e_port is not None:
            flowEntry.l_port = e_port.text

        e_match = e_flowEntry.find(unify_ns + "match")
        if e_match is not None:
            flowEntry.l_match = e_match.text

        e_action = e_flowEntry.find(unify_ns + "action")
        if e_action is not None:
            flowEntry.l_action = e_action.text

        e_resources = e_flowEntry.find(unify_ns + "resources")
        if e_resources is not None:
            flowEntry.c_resources = LinkResource.parse(e_resources, flowEntry)

        return flowEntry

    def xml(self):
        e_flowentry = ET.Element("flowentry")

        if self.operation == Delete:
            e_flowentry.attrib['operation'] ='delete'

        e_port = ET.SubElement(e_flowentry, "port")
        e_port.text = self.l_port

        e_match = ET.SubElement(e_flowentry, "match")
        e_match.text = self.l_match

        e_action = ET.SubElement(e_flowentry, "action")
        e_action.text = self.l_action

        if self.c_resources:
            e_resources = self.c_resources.xml()
            if e_resources is not None:
                e_flowentry.append(e_resources)

        return e_flowentry


class FlowTable(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.list_flowentry = []
        """:type: list(FlowEntry)"""

    @classmethod
    def parse(cls, e_node, parent):
        flowTableGrp = cls(parent)

        for e_flowEntry in e_node.findall(unify_ns + "flowentry"):
            flowEntry = FlowEntry.parse(e_flowEntry, flowTableGrp)
            flowTableGrp.list_flowentry.append(flowEntry)

        return flowTableGrp

    def xml(self):
        e_flowtable = ET.Element("flowtable")
        for flowentry in self.list_flowentry:
            e_flowentry = flowentry.xml()
            e_flowtable.append(e_flowentry)

        return e_flowtable


class FlowTableGroup(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.c_flowtable = None
        """:type: FlowTable"""

    @classmethod
    def parse(cls, e_node, parent):
        flowTableGrp = cls(parent)

        e_flowTable = e_node.find(unify_ns + "flowtable")
        if e_flowTable is not None:
            flowTableGrp.c_flowtable = FlowTable.parse(e_flowTable, flowTableGrp)

        return flowTableGrp

    def xml(self, e_node):
        if self.c_flowtable:
            e_flowtable = self.c_flowtable.xml()
            e_node.append(e_flowtable)


class Link(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.g_idName = None
        """:type: IdNameGroup"""
        self.l_src = ""
        """:type: str"""
        self.l_dst = ""
        """:type: str"""
        self.c_resources = None
        """:type: LinkResource"""

    @classmethod
    def parse(cls, e_link, parent):
        link = cls(parent)

        link.g_idName = IdNameGroup.parse(e_link, link)

        e_src = e_link.find(unify_ns + "src")
        if e_src is not None:
            link.l_src = e_src.text
            m = re.match(r'^.*node\[id=(.*?)\].*port\[id=(.*?)\]$', e_src.text)
            if m:
                node_id = m.group(1)
                port_id = m.group(2)
                # ToDo: link.l_src to be a reference to a Port

        e_dst = e_link.find(unify_ns + "dst")
        if e_dst is not None:
            link.l_dst = e_dst.text

        e_resource = e_link.find(unify_ns + "resources")
        if e_resource is not None:
            link.c_resources = LinkResource.parse(e_resource, link)

        return link

    def xml(self):
        e_link = ET.Element("link")
        self.g_idName.xml(e_link)

        e_src = ET.SubElement(e_link, "src")
        e_src.text = self.l_src

        e_dst = ET.SubElement(e_link, "dst")
        e_dst.text = self.l_dst

        if self.c_resources is not None:
            e_resources = self.c_resources.xml()
            if e_resources is not None:
                e_link.append(e_resources)

        return e_link


class Links(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.list_link = []
        """:type: list(Link)"""

    @classmethod
    def parse(cls, e_links, parent):
        links = cls(parent)

        for e_link in e_links.findall(unify_ns + "link"):
            link = Link.parse(e_link, links)
            links.list_link.append(link)

        return links

    def xml(self):
        e_links = ET.Element("links")
        for link in self.list_link:
            e_link = link.xml()
            e_links.append(e_link)

        return e_links


class LinksGroup(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.c_links = None
        """:type: Links"""

    @classmethod
    def parse(cls, e_root, parent):
        linksGrp = cls(parent)

        e_links = e_root.find(unify_ns + "links")
        if e_links is not None:
            linksGrp.c_links = Links.parse(e_links, linksGrp)

        return linksGrp

    def xml(self, e_root):
        if self.c_links:
            e_links = self.c_links.xml()
            e_root.append(e_links)


class Ports(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.list_port = []
        """:type: list(PortGroup)"""

    @classmethod
    def parse(cls, e_ports, parent):
        ports = cls(parent)

        for e_port in e_ports.findall(unify_ns + "port"):
            port = PortGroup.parse(e_port, ports)
            ports.list_port.append(port)

        return ports

    def xml(self):
        e_ports = ET.Element("ports")
        for port in self.list_port:
            e_port = ET.SubElement(e_ports, unify_ns + "port")
            port.xml(e_port)

        return e_ports


class SoftwareResourceGroup(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.l_cpu = ""
        """:type: str"""
        self.l_mem = ""
        """:type: str"""
        self.l_storage = ""
        """:type: str"""

    @classmethod
    def parse(cls, e_resources, parent):
        softRes = cls(parent)
        e_cpu = e_resources.find(unify_ns + "cpu")
        if e_cpu is None:
            raise InvalidXML("No CPU resource given")
        softRes.l_cpu = e_cpu.text

        e_mem = e_resources.find(unify_ns + "mem")
        if e_mem is None:
            raise InvalidXML("No memory resource given")
        softRes.l_mem = e_mem.text

        e_storage = e_resources.find(unify_ns + "storage")
        if e_storage is None:
            raise InvalidXML("No storage resource given")
        softRes.l_storage = e_storage.text

        return softRes

    def xml(self, e_res):
        e_cpu = ET.SubElement(e_res, "cpu")
        e_cpu.text = self.l_cpu

        e_mem = ET.SubElement(e_res, "mem")
        e_mem.text = self.l_mem

        e_storage = ET.SubElement(e_res, "storage")
        e_storage.text = self.l_storage


class NodeResources(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.g_softwareResource = None
        """:type: SoftwareResourceGroup"""

    @classmethod
    def parse(cls, e_resources, parent):
        nodeRes = cls(parent)
        nodeRes.g_softwareResource = SoftwareResourceGroup.parse(e_resources, nodeRes)
        return nodeRes

    def xml(self):
        e_nodeRes = ET.Element("resources")
        self.g_softwareResource.xml(e_nodeRes)
        return e_nodeRes


class NodeGroup(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.g_idNameType = None
        """:type: IdNameTypeGroup"""
        self.c_ports = None
        """:type: Ports"""
        self.g_links = None
        """:type: LinksGroup"""
        self.c_resources = None
        """:type: NodeResources"""

    @classmethod
    def parse(cls, e_node, parent):
        nodeGrp = cls(parent)

        if 'operation' in e_node.attrib:
            if e_node.attrib['operation'] == 'delete':
                nodeGrp.operation = Delete

        nodeGrp.g_idNameType = IdNameTypeGroup.parse(e_node, nodeGrp)

        e_ports = e_node.find(unify_ns + "ports")
        if e_ports is not None:
            nodeGrp.c_ports = Ports.parse(e_ports, nodeGrp)

        nodeGrp.g_links = LinksGroup.parse(e_node, parent)

        e_resources = e_node.find(unify_ns + "resources")
        if e_resources is not None:
            nodeGrp.c_resources = NodeResources.parse(e_resources, nodeGrp)

        return nodeGrp

    def xml(self, e_node):
        self.g_idNameType.xml(e_node)

        if self.c_ports is not None:
            e_ports = self.c_ports.xml()
            e_node.append(e_ports)

        if self.g_links is not None:
            self.g_links.xml(e_node)

        if self.c_resources is not None:
            e_resources = self.c_resources.xml()
            e_node.append(e_resources)


class NFInstances(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.list_node = []
        """:type: list(NodeGroup)"""

    @classmethod
    def parse(cls, e_NFInstances, parent):
        nfInstances = cls(parent)

        for e_node in e_NFInstances:
            nodeGrp = NodeGroup.parse(e_node, nfInstances)
            nfInstances.list_node.append(nodeGrp)

        return nfInstances

    def xml(self):
        e_NFInstances = ET.Element(unify_ns + "NF_instances")
        for node in self.list_node:
            e_node = ET.SubElement(e_NFInstances, unify_ns + "node")
            if node.operation == Delete:
                e_node.attrib['operation'] ='delete'
            node.xml(e_node)

        return e_NFInstances


class SupportedNFs(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.list_node = []
        """:type: list(NodeGroup)"""

    @classmethod
    def parse(cls, e_supportedNFs, parent):
        supNFs = cls(parent)

        for e_node in e_supportedNFs.findall(unify_ns + "node"):
            node = NodeGroup.parse(e_node,supNFs)
            supNFs.list_node.append(node)

        return supNFs

    def xml(self):
        e_sup = ET.Element("supported_NFs")
        for node in self.list_node:
            e_node = ET.Element("node")
            node.xml(e_node)
            e_sup.append(e_node)

        return e_sup


class CapabilitesGroup(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.c_supportedNFs = None
        """:type: SupportedNFs"""

    @classmethod
    def parse(cls, e_capabilities, parent):
        capGroup = cls(parent)
        e_supportedNFs = e_capabilities.find("supported_NFs")
        if e_supportedNFs is not None:
            capGroup.c_supportedNFs = SupportedNFs.parse(e_supportedNFs,capGroup)

        return capGroup

    def xml(self, e_cap):
        e_sup = self.c_supportedNFs.xml()
        e_cap.append(e_sup)


class Capabilities(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.g_capabilities = None
        """:type: CapabilitesGroup"""

    @classmethod
    def parse(cls, e_capabilities, parent):
        capabilities = cls(parent)
        capabilities.g_capabilities = CapabilitesGroup.parse(e_capabilities, capabilities)
        return capabilities

    def xml(self):
        e_capabilities = ET.Element("capabilities")
        self.g_capabilities.xml(e_capabilities)
        return e_capabilities


class InfraNodeGroup(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.g_node = None
        """:type: NodeGroup"""
        self.c_NFInstances = None
        """:type: NFInstances"""
        self.c_capabilities = None
        """:type: Capabilities"""
        self.g_flowtable = None
        """:type: FlowTableGroup"""

    @classmethod
    def parse(cls, e_node, parent):
        infraNodeGroup = cls(parent)

        infraNodeGroup.g_node = NodeGroup.parse(e_node, infraNodeGroup)

        e_NFInstances = e_node.find(unify_ns + "NF_instances")
        if e_NFInstances is not None:
            infraNodeGroup.c_NFInstances = NFInstances.parse(e_NFInstances, infraNodeGroup)

        e_capabilities = e_node.find(unify_ns + "capabilities")
        if e_capabilities is not None:
            infraNodeGroup.c_capabilities = Capabilities.parse(e_capabilities, infraNodeGroup)

        infraNodeGroup.g_flowtable = FlowTableGroup.parse(e_node, infraNodeGroup)

        return infraNodeGroup

    def xml(self, e_node):
        self.g_node.xml(e_node)

        if self.c_NFInstances:
            e_NFInstances = self.c_NFInstances.xml()
            e_node.append(e_NFInstances)

        if self.c_capabilities:
            e_capabilities = self.c_capabilities.xml()
            e_node.append(e_capabilities)

        self.g_flowtable.xml(e_node)


class Nodes(base):
    def __init__(self, parent):
        base.__init__(self, parent)
        self.list_node = []
        """:type: list(InfraNodeGroup)"""

    @classmethod
    def parse(cls, e_nodes, parent):
        nodes = cls(parent)

        for e_node in e_nodes.findall(unify_ns + "node"):
            infraNodeGroup = InfraNodeGroup.parse(e_node, nodes)
            nodes.list_node.append(infraNodeGroup)

        return nodes

    def xml(self):
        e_nodes = ET.Element(unify_ns + "nodes")
        for node in self.list_node:
            e_node = ET.SubElement(e_nodes, unify_ns + "node")
            node.xml(e_node)

        return e_nodes


class Virtualizer(base):
    def __init__(self, parent=None):
        base.__init__(self, parent)
        self.g_idName = None
        """:type: IdNameGroup"""
        self.c_nodes = None
        """:type: Nodes"""
        self.g_links = None
        """:type: LinksGroup"""

    @classmethod
    def parse(cls, file=None, text=None):
        """Parse a Virtualizer (base) from an xml source. Provide either file or text as input.
        :param file: filename containing xml input to be parsed
        :type file: str or unicode
        :param text: text string containing xml input to be parsed
        :type text: str or unicode
        :returns: the Virtualizer instance containing the parsed data
        :rtype: Virtualizer
        """
        if file and text:
            raise InvalidXML("Dual XML input provided to be parsed")
        elif file:
            try:
                tree = ET.parse(file)
            except ET.ParseError as e:
                raise InvalidXML('ParseError: %s' % e.message)
        elif text:
            try:
                tree = ET.ElementTree(ET.fromstring(text))
            except ET.ParseError as e:
                raise InvalidXML('ParseError: %s' % e.message)
        else:
            raise InvalidXML("No XML input provided to be parsed")

        root = tree.getroot()
        if root.tag != unify_ns + "virtualizer":
            raise InvalidXML("Root must be virtualizer")

        virtualizer = cls()
        virtualizer.g_idName = IdNameGroup.parse(root, virtualizer)

        e_nodes = root.find(unify_ns + "nodes")
        if e_nodes is not None:
            virtualizer.c_nodes = Nodes.parse(e_nodes, virtualizer)

        virtualizer.g_links = LinksGroup.parse(root, virtualizer)

        return virtualizer

    def xml(self):
        """Dump a Virtualizer instance to a xml string.
        :returns: the string containing the xml representation of the Virtualizer instance
        :rtype: str
        """

        root = ET.Element("virtualizer")
        if self.g_idName is not None:
            self.g_idName.xml(root)

        if self.c_nodes is not None:
            e_nodes = self.c_nodes.xml()
            root.append(e_nodes)

        if self.g_links is not None:
            self.g_links.xml(root)

        xmlstr = ET.tostring(root, encoding='utf8', method='xml')
        dom = parseString(xmlstr)
        s = dom.toprettyxml()
        return s


def main():
    """Example usage for the Virtualizer class parsing/dumping
    """
    filenames = ['../specification/doc/figs/1-node.xml',
                 '../specification/doc/figs/3-node.xml',
                 '../specification/doc/figs/1-node-with-delay-matrix.xml',
                 '../specification/doc/figs/1-node-simple-request.xml',
                 '../specification/doc/figs/1-node-simple-request-with-virtual-link-requirements.xml',
                 '../specification/doc/figs/1-node-simple-request-with-NF-requirements.xml',
                 '../specification/doc/figs/1-node-simple-request-with-delete.xml',
                 '../specification/doc/figs/link-sharing-request-step1.xml',
                 '../specification/doc/figs/link-sharing-request-step2.xml',
                 '../specification/doc/figs/link-sharing-request-step3.xml']
    n = dict()
    s = dict()
    for filename in filenames:
        print 'Parsing', filename
        n[filename] = Virtualizer.parse(file=filename)
        print 'Dumping', filename
        s[filename] = n[filename].xml()
        # print s[filename]
        outfilename = re.sub(r'\.xml$', r'_out.xml', filename)
        print 'Writing', outfilename
        with open(outfilename, 'w') as outfile:
            outfile.writelines(s[filename])

    t = """<?xml version="1.0" ?>
    <virtualizer>
        <id>UUID001</id>
        <name>Single node simple infrastructure report</name>
        <nodes>
            <node>
                <id>UUID11</id>
                <name>single Bis-Bis node</name>
                <type>BisBis</type>
                <ports>
                    <port>
                        <id>0</id>
                        <name>SAP0 port</name>
                        <port_type>port-sap</port_type>
                        <sap-type>vx-lan</sap-type>
                        <vxlan>...</vxlan>
                    </port>
                </ports>
                <resources>
                    <cpu>20</cpu>
                    <mem>64 GB</mem>
                    <storage>100 TB</storage>
                </resources>
            </node>
        </nodes>
    </virtualizer>"""
    print 'Parsing string'
    a = Virtualizer.parse(text=t)
    print 'Printing string'
    print a.xml()


if __name__ == '__main__':
    main()
