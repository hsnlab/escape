#    Filename: virtualizer3.py		 Created: 2015-09-04  21:53:36
#    This file was automatically created by a pyang plugin (PNC) developed at Ericsson Hungary Ltd., 2015
#    Authors: Robert Szabo, Balazs Miriszlai, Akos Recse, Raphael Vicente Rosa
#    Credits: Robert Szabo, Raphael Vicente Rosa, David Jocha, Janos Elek, Balazs Miriszlai, Akos Recse
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
        
#    Yang file info:
#    Namespace: urn:unify:virtualizer
#    Prefix: virtualizer
#    Organization: ETH
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
#    Revision: 2015-07-20
#    Description: Virtualizer's revised (simplified) data model

__copyright__ = "Copyright Ericsson Hungary Ltd., 2015"


from baseclasses import *


# YANG construct: grouping id-name
class GroupingId_name(Yang):
    def __init__(self, tag, parent=None, id=None, name=None):
        super(GroupingId_name, self).__init__(tag, parent)
        self._sorted_children = ["id", "name"]
        # yang construct: leaf
        self.id = StringLeaf("id", parent=self)
        """:type: StringLeaf"""
        if id is not None:
            self.id.set_value(id)
        # yang construct: leaf
        self.name = StringLeaf("name", parent=self)
        """:type: StringLeaf"""
        if name is not None:
            self.name.set_value(name)

    def _parse(self, parent=None, root=None):
        self.id.parse(root)
        self.name.parse(root)


# YANG construct: grouping id-name-type
class GroupingId_name_type(GroupingId_name):
    def __init__(self, tag, parent=None, id=None, name=None, type=None):
        GroupingId_name.__init__(self, tag, parent, id, name)
        self._sorted_children = ["id", "name", "type"]
        # yang construct: leaf
        self.type = StringLeaf("type", parent=self)
        """:type: StringLeaf"""
        if type is not None:
            self.type.set_value(type)

    def _parse(self, parent=None, root=None):
        GroupingId_name._parse(self, parent, root)
        self.type.parse(root)


# YANG construct: grouping port
class GroupingPort(GroupingId_name):
    def __init__(self, tag, parent=None, id=None, name=None, port_type=None, capability=None, sap=None):
        GroupingId_name.__init__(self, tag, parent, id, name)
        self._sorted_children = ["id", "name", "port_type", "capability", "sap"]
        # yang construct: leaf
        self.port_type = StringLeaf("port_type", parent=self)
        """:type: StringLeaf"""
        if port_type is not None:
            self.port_type.set_value(port_type)
        # yang construct: leaf
        self.capability = StringLeaf("capability", parent=self)
        """:type: StringLeaf"""
        if capability is not None:
            self.capability.set_value(capability)
        # yang construct: leaf
        self.sap = StringLeaf("sap", parent=self)
        """:type: StringLeaf"""
        if sap is not None:
            self.sap.set_value(sap)

    def _parse(self, parent=None, root=None):
        GroupingId_name._parse(self, parent, root)
        self.port_type.parse(root)
        self.capability.parse(root)
        self.sap.parse(root)


# YANG construct: grouping link-resource
class GroupingLink_resource(Yang):
    def __init__(self, tag, parent=None, delay=None, bandwidth=None):
        super(GroupingLink_resource, self).__init__(tag, parent)
        self._sorted_children = ["delay", "bandwidth"]
        # yang construct: leaf
        self.delay = StringLeaf("delay", parent=self)
        """:type: StringLeaf"""
        if delay is not None:
            self.delay.set_value(delay)
        # yang construct: leaf
        self.bandwidth = StringLeaf("bandwidth", parent=self)
        """:type: StringLeaf"""
        if bandwidth is not None:
            self.bandwidth.set_value(bandwidth)

    def _parse(self, parent=None, root=None):
        self.delay.parse(root)
        self.bandwidth.parse(root)


# YANG construct: grouping flowentry
class GroupingFlowentry(GroupingId_name):
    def __init__(self, tag, parent=None, id=None, name=None, priority=None, port=None, match=None, action=None, out=None, resources=None):
        GroupingId_name.__init__(self, tag, parent, id, name)
        self._sorted_children = ["id", "name", "priority", "port", "match", "action", "out", "resources"]
        # yang construct: leaf
        self.priority = StringLeaf("priority", parent=self)
        """:type: StringLeaf"""
        if priority is not None:
            self.priority.set_value(priority)
        # yang construct: leaf
        self.port = Leafref(parent=self, tag="port", value=port)
        """:type: Leafref"""
        self.port.mandatory = True
        """:type: boolean"""
        # yang construct: leaf
        self.match = StringLeaf("match", parent=self)
        """:type: StringLeaf"""
        if match is not None:
            self.match.set_value(match)
        self.match.mandatory = True
        """:type: boolean"""
        # yang construct: leaf
        self.action = StringLeaf("action", parent=self)
        """:type: StringLeaf"""
        if action is not None:
            self.action.set_value(action)
        self.action.mandatory = True
        """:type: boolean"""
        # yang construct: leaf
        self.out = Leafref(parent=self, tag="out", value=out)
        """:type: Leafref"""
        # yang construct: container
        self.resources = None
        """:type: Link_resource"""
        if resources is not None:
            self.resources = resources
        else:
            self.resources = Link_resource(parent=self, tag="resources")

    def _parse(self, parent=None, root=None):
        GroupingId_name._parse(self, parent, root)
        self.priority.parse(root)
        self.port.parse(root)
        self.match.parse(root)
        self.action.parse(root)
        self.out.parse(root)
        e_resources = root.find("resources")
        if e_resources is not None:
            self.resources = Link_resource.parse(self, e_resources)
            for key in e_resources.attrib.keys():
                if key == "operation":
                    self.set_operation(e_resources.attrib[key])
                    self.operation = e_resources.attrib[key]


# YANG construct: grouping flowtable
class GroupingFlowtable(Yang):
    def __init__(self, tag, parent=None, flowtable=None):
        super(GroupingFlowtable, self).__init__(tag, parent)
        self._sorted_children = ["flowtable"]
        # yang construct: container
        self.flowtable = None
        """:type: FlowtableFlowtable"""
        if flowtable is not None:
            self.flowtable = flowtable
        else:
            self.flowtable = FlowtableFlowtable(parent=self, tag="flowtable")

    def _parse(self, parent=None, root=None):
        e_flowtable = root.find("flowtable")
        if e_flowtable is not None:
            self.flowtable = FlowtableFlowtable.parse(self, e_flowtable)
            for key in e_flowtable.attrib.keys():
                if key == "operation":
                    self.set_operation(e_flowtable.attrib[key])
                    self.operation = e_flowtable.attrib[key]


# YANG construct: grouping link
class GroupingLink(GroupingId_name):
    def __init__(self, tag, parent=None, id=None, name=None, src=None, dst=None, resources=None):
        GroupingId_name.__init__(self, tag, parent, id, name)
        self._sorted_children = ["id", "name", "src", "dst", "resources"]
        # yang construct: leaf
        self.src = Leafref(parent=self, tag="src", value=src)
        """:type: Leafref"""
        # yang construct: leaf
        self.dst = Leafref(parent=self, tag="dst", value=dst)
        """:type: Leafref"""
        # yang construct: container
        self.resources = None
        """:type: Link_resource"""
        if resources is not None:
            self.resources = resources
        else:
            self.resources = Link_resource(parent=self, tag="resources")

    def _parse(self, parent=None, root=None):
        GroupingId_name._parse(self, parent, root)
        self.src.parse(root)
        self.dst.parse(root)
        e_resources = root.find("resources")
        if e_resources is not None:
            self.resources = Link_resource.parse(self, e_resources)
            for key in e_resources.attrib.keys():
                if key == "operation":
                    self.set_operation(e_resources.attrib[key])
                    self.operation = e_resources.attrib[key]


# YANG construct: grouping links
class GroupingLinks(Yang):
    def __init__(self, tag, parent=None, links=None):
        super(GroupingLinks, self).__init__(tag, parent)
        self._sorted_children = ["links"]
        # yang construct: container
        self.links = None
        """:type: LinksLinks"""
        if links is not None:
            self.links = links
        else:
            self.links = LinksLinks(parent=self, tag="links")

    def _parse(self, parent=None, root=None):
        e_links = root.find("links")
        if e_links is not None:
            self.links = LinksLinks.parse(self, e_links)
            for key in e_links.attrib.keys():
                if key == "operation":
                    self.set_operation(e_links.attrib[key])
                    self.operation = e_links.attrib[key]


# YANG construct: grouping software-resource
class GroupingSoftware_resource(Yang):
    def __init__(self, tag, parent=None, cpu=None, mem=None, storage=None):
        super(GroupingSoftware_resource, self).__init__(tag, parent)
        self._sorted_children = ["cpu", "mem", "storage"]
        # yang construct: leaf
        self.cpu = StringLeaf("cpu", parent=self)
        """:type: StringLeaf"""
        if cpu is not None:
            self.cpu.set_value(cpu)
        self.cpu.mandatory = True
        """:type: boolean"""
        # yang construct: leaf
        self.mem = StringLeaf("mem", parent=self)
        """:type: StringLeaf"""
        if mem is not None:
            self.mem.set_value(mem)
        self.mem.mandatory = True
        """:type: boolean"""
        # yang construct: leaf
        self.storage = StringLeaf("storage", parent=self)
        """:type: StringLeaf"""
        if storage is not None:
            self.storage.set_value(storage)
        self.storage.mandatory = True
        """:type: boolean"""

    def _parse(self, parent=None, root=None):
        self.cpu.parse(root)
        self.mem.parse(root)
        self.storage.parse(root)


# YANG construct: grouping node
class GroupingNode(GroupingId_name_type, GroupingLinks):
    """Any node: infrastructure or NFs"""
    def __init__(self, tag, parent=None, id=None, name=None, type=None, ports=None, links=None, resources=None):
        GroupingId_name_type.__init__(self, tag, parent, id, name, type)
        GroupingLinks.__init__(self, tag, parent, links)
        self._sorted_children = ["id", "name", "type", "ports", "links", "resources"]
        # yang construct: container
        self.ports = None
        """:type: NodePorts"""
        if ports is not None:
            self.ports = ports
        else:
            self.ports = NodePorts(parent=self, tag="ports")
        # yang construct: container
        self.resources = None
        """:type: Software_resource"""
        if resources is not None:
            self.resources = resources
        else:
            self.resources = Software_resource(parent=self, tag="resources")

    def _parse(self, parent=None, root=None):
        GroupingId_name_type._parse(self, parent, root)
        e_ports = root.find("ports")
        if e_ports is not None:
            self.ports = NodePorts.parse(self, e_ports)
            for key in e_ports.attrib.keys():
                if key == "operation":
                    self.set_operation(e_ports.attrib[key])
                    self.operation = e_ports.attrib[key]
        GroupingLinks._parse(self, parent, root)
        e_resources = root.find("resources")
        if e_resources is not None:
            self.resources = Software_resource.parse(self, e_resources)
            for key in e_resources.attrib.keys():
                if key == "operation":
                    self.set_operation(e_resources.attrib[key])
                    self.operation = e_resources.attrib[key]


# YANG construct: grouping nodes
class GroupingNodes(Yang):
    def __init__(self, tag, parent=None):
        super(GroupingNodes, self).__init__(tag, parent)
        self._sorted_children = ["node"]
        # yang construct: list
        self.node = ListYang("node", parent=self)
        """:type: ListYang(Node)"""

    def _parse(self, parent=None, root=None):
        e_node = root.find("node")
        while e_node is not None:
            item = Node.parse(self, e_node)
            for key in e_node.attrib.keys():
                if key == "operation":
                    item.set_operation(e_node.attrib[key])
                    item.operation = e_node.attrib[key]
            key = item.keys()
            self.node[key] = item
            root.remove(e_node)
            e_node = root.find("node")

    def add(self, item):
        return self.node.add(item)

    def remove(self, item):
        return self.node.remove(item)

    def __getitem__(self, key):
        return self.node[key]

    def __iter__(self):
        return self.node.itervalues()


# YANG construct: grouping infra-node
class GroupingInfra_node(GroupingNode, GroupingFlowtable):
    def __init__(self, tag, parent=None, id=None, name=None, type=None, ports=None, links=None, resources=None, NF_instances=None, capabilities=None, flowtable=None):
        GroupingNode.__init__(self, tag, parent, id, name, type, ports, links, resources)
        GroupingFlowtable.__init__(self, tag, parent, flowtable)
        self._sorted_children = ["id", "name", "type", "ports", "links", "resources", "NF_instances", "capabilities", "flowtable"]
        # yang construct: container
        self.NF_instances = None
        """:type: Nodes"""
        if NF_instances is not None:
            self.NF_instances = NF_instances
        else:
            self.NF_instances = Nodes(parent=self, tag="NF_instances")
        # yang construct: container
        self.capabilities = None
        """:type: Infra_nodeCapabilities"""
        if capabilities is not None:
            self.capabilities = capabilities
        else:
            self.capabilities = Infra_nodeCapabilities(parent=self, tag="capabilities")

    def _parse(self, parent=None, root=None):
        GroupingNode._parse(self, parent, root)
        e_NF_instances = root.find("NF_instances")
        if e_NF_instances is not None:
            self.NF_instances = Nodes.parse(self, e_NF_instances)
            for key in e_NF_instances.attrib.keys():
                if key == "operation":
                    self.set_operation(e_NF_instances.attrib[key])
                    self.operation = e_NF_instances.attrib[key]
        e_capabilities = root.find("capabilities")
        if e_capabilities is not None:
            self.capabilities = Infra_nodeCapabilities.parse(self, e_capabilities)
            for key in e_capabilities.attrib.keys():
                if key == "operation":
                    self.set_operation(e_capabilities.attrib[key])
                    self.operation = e_capabilities.attrib[key]
        GroupingFlowtable._parse(self, parent, root)


# YANG construct: list flowentry
class Flowentry(GroupingFlowentry, ListedYang):
    def __init__(self, tag="flowentry", parent=None, id=None, name=None, priority=None, port=None, match=None, action=None, out=None, resources=None):
        GroupingFlowentry.__init__(self, tag, parent, id, name, priority, port, match, action, out, resources)
        ListedYang.__init__(self, "flowentry", ["id"])
        self._sorted_children = ["id", "name", "priority", "port", "match", "action", "out", "resources"]

    def _parse(self, parent=None, root=None):
        GroupingFlowentry._parse(self, parent, root)


# YANG construct: list link
class Link(GroupingLink, ListedYang):
    def __init__(self, tag="link", parent=None, id=None, name=None, src=None, dst=None, resources=None):
        GroupingLink.__init__(self, tag, parent, id, name, src, dst, resources)
        ListedYang.__init__(self, "link", ["src", "dst"])
        self._sorted_children = ["id", "name", "src", "dst", "resources"]

    def _parse(self, parent=None, root=None):
        GroupingLink._parse(self, parent, root)


# YANG construct: list port
class Port(GroupingPort, ListedYang):
    def __init__(self, tag="port", parent=None, id=None, name=None, port_type=None, capability=None, sap=None):
        GroupingPort.__init__(self, tag, parent, id, name, port_type, capability, sap)
        ListedYang.__init__(self, "port", ["id"])
        self._sorted_children = ["id", "name", "port_type", "capability", "sap"]

    def _parse(self, parent=None, root=None):
        GroupingPort._parse(self, parent, root)


# YANG construct: list node
class Node(GroupingNode, ListedYang):
    def __init__(self, tag="node", parent=None, id=None, name=None, type=None, ports=None, links=None, resources=None):
        GroupingNode.__init__(self, tag, parent, id, name, type, ports, links, resources)
        ListedYang.__init__(self, "node", ["id"])
        self._sorted_children = ["id", "name", "type", "ports", "links", "resources"]

    def _parse(self, parent=None, root=None):
        GroupingNode._parse(self, parent, root)


# YANG construct: list node
class Infra_node(GroupingInfra_node, ListedYang):
    def __init__(self, tag="node", parent=None, id=None, name=None, type=None, ports=None, links=None, resources=None, NF_instances=None, capabilities=None, flowtable=None):
        GroupingInfra_node.__init__(self, tag, parent, id, name, type, ports, links, resources, NF_instances, capabilities, flowtable)
        ListedYang.__init__(self, "node", ["id"])
        self._sorted_children = ["id", "name", "type", "ports", "links", "resources", "NF_instances", "capabilities", "flowtable"]

    def _parse(self, parent=None, root=None):
        GroupingInfra_node._parse(self, parent, root)


# YANG construct: container resources
class Link_resource(GroupingLink_resource):
    def __init__(self, tag="resources", parent=None, delay=None, bandwidth=None):
        GroupingLink_resource.__init__(self, tag, parent, delay, bandwidth)
        self._sorted_children = ["delay", "bandwidth"]

    def _parse(self, parent=None, root=None):
        GroupingLink_resource._parse(self, parent, root)


# YANG construct: container flowtable
class FlowtableFlowtable(Yang):
    def __init__(self, tag="flowtable", parent=None):
        super(FlowtableFlowtable, self).__init__(tag, parent)
        self._sorted_children = ["flowentry"]
        # yang construct: list
        self.flowentry = ListYang("flowentry", parent=self)
        """:type: ListYang(Flowentry)"""

    def _parse(self, parent=None, root=None):
        e_flowentry = root.find("flowentry")
        while e_flowentry is not None:
            item = Flowentry.parse(self, e_flowentry)
            for key in e_flowentry.attrib.keys():
                if key == "operation":
                    item.set_operation(e_flowentry.attrib[key])
                    item.operation = e_flowentry.attrib[key]
            key = item.keys()
            self.flowentry[key] = item
            root.remove(e_flowentry)
            e_flowentry = root.find("flowentry")

    def add(self, item):
        return self.flowentry.add(item)

    def remove(self, item):
        return self.flowentry.remove(item)

    def __getitem__(self, key):
        return self.flowentry[key]

    def __iter__(self):
        return self.flowentry.itervalues()


# YANG construct: container links
class LinksLinks(Yang):
    def __init__(self, tag="links", parent=None):
        super(LinksLinks, self).__init__(tag, parent)
        self._sorted_children = ["link"]
        # yang construct: list
        self.link = ListYang("link", parent=self)
        """:type: ListYang(Link)"""

    def _parse(self, parent=None, root=None):
        e_link = root.find("link")
        while e_link is not None:
            item = Link.parse(self, e_link)
            for key in e_link.attrib.keys():
                if key == "operation":
                    item.set_operation(e_link.attrib[key])
                    item.operation = e_link.attrib[key]
            key = item.keys()
            self.link[key] = item
            root.remove(e_link)
            e_link = root.find("link")

    def add(self, item):
        return self.link.add(item)

    def remove(self, item):
        return self.link.remove(item)

    def __getitem__(self, key):
        return self.link[key]

    def __iter__(self):
        return self.link.itervalues()


# YANG construct: container ports
class NodePorts(Yang):
    def __init__(self, tag="ports", parent=None):
        super(NodePorts, self).__init__(tag, parent)
        self._sorted_children = ["port"]
        # yang construct: list
        self.port = ListYang("port", parent=self)
        """:type: ListYang(Port)"""

    def _parse(self, parent=None, root=None):
        e_port = root.find("port")
        while e_port is not None:
            item = Port.parse(self, e_port)
            for key in e_port.attrib.keys():
                if key == "operation":
                    item.set_operation(e_port.attrib[key])
                    item.operation = e_port.attrib[key]
            key = item.keys()
            self.port[key] = item
            root.remove(e_port)
            e_port = root.find("port")

    def add(self, item):
        return self.port.add(item)

    def remove(self, item):
        return self.port.remove(item)

    def __getitem__(self, key):
        return self.port[key]

    def __iter__(self):
        return self.port.itervalues()


# YANG construct: container resources
class Software_resource(GroupingSoftware_resource):
    def __init__(self, tag="resources", parent=None, cpu=None, mem=None, storage=None):
        GroupingSoftware_resource.__init__(self, tag, parent, cpu, mem, storage)
        self._sorted_children = ["cpu", "mem", "storage"]

    def _parse(self, parent=None, root=None):
        GroupingSoftware_resource._parse(self, parent, root)


# YANG construct: container NF_instances
class Nodes(GroupingNodes):
    def __init__(self, tag="NF_instances", parent=None):
        GroupingNodes.__init__(self, tag, parent)
        self._sorted_children = ["node"]

    def _parse(self, parent=None, root=None):
        GroupingNodes._parse(self, parent, root)


# YANG construct: container capabilities
class Infra_nodeCapabilities(Yang):
    def __init__(self, tag="capabilities", parent=None, NF_instances=None):
        super(Infra_nodeCapabilities, self).__init__(tag, parent)
        self._sorted_children = ["supported_NFs"]
        # yang construct: container
        self.NF_instances = None
        """:type: Nodes"""
        if NF_instances is not None:
            self.NF_instances = NF_instances
        else:
            self.NF_instances = Nodes(parent=self, tag="supported_NFs")

    def _parse(self, parent=None, root=None):
        e_NF_instances = root.find("NF_instances")
        if e_NF_instances is not None:
            self.NF_instances = Nodes.parse(self, e_NF_instances)
            for key in e_NF_instances.attrib.keys():
                if key == "operation":
                    self.set_operation(e_NF_instances.attrib[key])
                    self.operation = e_NF_instances.attrib[key]


# YANG construct: container virtualizer
class Virtualizer(GroupingId_name, GroupingLinks):
    """Container for a single virtualizer"""
    def __init__(self, tag="virtualizer", parent=None, id=None, name=None, nodes=None, links=None):
        GroupingId_name.__init__(self, tag, parent, id, name)
        GroupingLinks.__init__(self, tag, parent, links)
        self._sorted_children = ["id", "name", "nodes", "links"]
        # yang construct: container
        self.nodes = None
        """:type: VirtualizerNodes"""
        if nodes is not None:
            self.nodes = nodes
        else:
            self.nodes = VirtualizerNodes(parent=self, tag="nodes")

    def _parse(self, parent=None, root=None):
        GroupingId_name._parse(self, parent, root)
        e_nodes = root.find("nodes")
        if e_nodes is not None:
            self.nodes = VirtualizerNodes.parse(self, e_nodes)
            for key in e_nodes.attrib.keys():
                if key == "operation":
                    self.set_operation(e_nodes.attrib[key])
                    self.operation = e_nodes.attrib[key]
        GroupingLinks._parse(self, parent, root)


# YANG construct: container nodes
class VirtualizerNodes(Yang):
    def __init__(self, tag="nodes", parent=None):
        super(VirtualizerNodes, self).__init__(tag, parent)
        self._sorted_children = ["node"]
        # yang construct: list
        self.node = ListYang("node", parent=self)
        """:type: ListYang(Infra_node)"""

    def _parse(self, parent=None, root=None):
        e_node = root.find("node")
        while e_node is not None:
            item = Infra_node.parse(self, e_node)
            for key in e_node.attrib.keys():
                if key == "operation":
                    item.set_operation(e_node.attrib[key])
                    item.operation = e_node.attrib[key]
            key = item.keys()
            self.node[key] = item
            root.remove(e_node)
            e_node = root.find("node")

    def add(self, item):
        return self.node.add(item)

    def remove(self, item):
        return self.node.remove(item)

    def __getitem__(self, key):
        return self.node[key]

    def __iter__(self):
        return self.node.itervalues()

