#    Filename: virtualizer3.py		 Created: 2015-08-05  15:29:27
#    This file was automatically created by a pyang plugin (PNC) developed at Ericsson Hungary Ltd., 2015
#    Authors: Robert Szabo, Balazs Miriszlai, Akos Recse
#    Credits: Robert Szabo, David Jocha, Janos Elek, Balazs Miriszlai, Akos Recse
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
        
#    Yang file info:
#    Namespace: urn:unify:virtualizer
#    Prefix: virtualizer
#    Organization: ETH
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
#    Revision: 2015-07-20
#    Description: Virtualizer's revised (simplified) data model

__copyright__ = "Copyright Ericsson Hungary Ltd., 2015"

import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
import copy


class Yang(object):
    def __init__(self, parent=None, tag=None):
        self.parent = parent
        self.tag = tag
        self.operation = None


    def getParent(self):
        return self.parent

    def xml(self):
        root = self._et(None, False)
        xmlstr = ET.tostring(root, encoding="utf8", method="xml")
        dom = parseString(xmlstr)
        return dom.toprettyxml()

    def _parse(self, parent, root):
        pass

    def reducer(self, other):
        for k,v in self.__dict__.items():
            if isinstance(v, Yang):
                for k_,v_ in other.__dict__.items():
                    if k == k_ and type(v) == type(v_):
                        if k != "parent" and k!='id':
                                v.reducer(v_)

    def getPath(self):
        if self.getParent() is not None:
            return self.getParent().getPath() + "/" + self.tag
        else:
            return self.tag

    def walkPath(self, path):
        if path == "":
            return self
        p = path.split("/")
        l = p.pop(0)
        if l == "..":
            return self.getParent().walkPath("/".join(p))
        else:
            if (l.find("[") > 0) and (l.find("]")>0):
                attrib = l[0: l.find("[")]
                keystring = l[l.find("[") + 1: l.rfind("]")]
                key = list()
                keyvalues = keystring.split(",")
                for kv in keyvalues:
                    v = kv.split("=")
                    key.append(v[1])
                if len(key) == 1:
                    return getattr(self, attrib)[key[0]].walkPath("/".join(p))
                else:
                    return getattr(self, attrib)[key].walkPath("/".join(p))
            else:
                return getattr(self, l).walkPath("/".join(p))

    def getRelPath(self, target):
        src = self.getPath()
        dst = target.getPath()
        s = src.split("/")
        d = dst.split("/")
        if s[0] != d[0]:
            return dst
        i = 1
        ret = list()
        while s[i] == d[i]:
            i+=1
        for j in range(i, len(s)):
            ret.insert(0,"..")
        for j in range(i, len(d)):
            ret.append(d[j])
        return '/'.join(ret)

    @classmethod
    def parse(cls, parent=None, root=None):
        temp = cls(parent=parent)
        temp._parse(parent, root)
        return temp

    def _et(self, node, inherited=False):
        if self.isInitialized():
            if node is not None:
                node= ET.SubElement(node, self.tag)
            else:
                node= ET.Element(self.tag)

            for k,v in self.__dict__.items():
                if isinstance(v, Yang) and k is not "parent":
                    v._et(node, inherited)
        return node

    def __str__(self):
        return self.xml()

    def containsOperation(self, operation = "delete"):
        if self.operation == operation:
            return True
        for k,v in self.__dict__.items():
            if isinstance(v, Yang) and k is not "parent":
                if v.containsOperation(operation):
                    return True
        return False

    def setOperation(self, operation = "delete"):
        self.operation = operation
        for k,v in self.__dict__.items():
            if isinstance(v, Yang) and k is not "parent":
                v.setOperation(operation)

    def isInitialized(self):
        for k,v in self.__dict__.items():
            if isinstance(v, Yang) and k is not "parent":
                if v.isInitialized():
                    return True
        return False
        
    def __eq__(self, other):
        eq = True
        #Check attributes
        selfAtribs = self.__dict__
        otherAtribs = other.__dict__
        eq = eq and (selfAtribs.keys().sort() == otherAtribs.keys().sort())
        if eq:
            for k in selfAtribs.keys():
                if k is not "parent":
                    for k_ in otherAtribs.keys():
                        if k == k_:
                            eq = eq and (selfAtribs[k] == otherAtribs[k_])
        #Check class attributes
        selfClassAtribs = self.__class__.__dict__
        otherClassAtribs = other.__class__.__dict__
        eq = eq and (selfClassAtribs.keys().sort() == otherClassAtribs.keys().sort())
        if eq:
            for k in selfClassAtribs.keys():
                for k_ in otherClassAtribs.keys():
                    if k == k_ and not callable(selfClassAtribs[k]):
                        eq = eq and (selfClassAtribs[k] == otherClassAtribs[k_])
        return eq

    def merge(self, target):
        for k,v in self.__dict__.items():
            if k is not "parent":
                for k_,v_ in target.__dict__.items():
                    if k == k_:
                        if isinstance(v,Yang):
                            if not v.isInitialized():
                                self.__dict__[k] = v_
                            else:
                                self.__dict__[k].merge(v_)
                    if k_ not in self.__dict__.keys():
                        self.__dict__[k_] = v_

class Leaf(Yang):

    def __init__(self, parent=None, tag=None):
        super(Leaf, self).__init__(parent)
        self.tag = tag
        """:type: string"""
        self.data = None
        """:type: ???"""
        self.mandatory = False
        """:type: boolean"""

    def getAsText(self):
        pass

    def setAsText(self, value):
        pass

    def getValue(self):
        pass

    def setValue(self, value):
        pass

    def isInitialized(self):
        if self.data is not None:
            return True
        else:
            return False

    def _et(self, parent, inherited=False):
        if self.isInitialized():
            e_data = ET.SubElement(parent, self.tag)
            e_data.text = self.getAsText()
        return parent

    def clearData(self):
        self.data = None

    def reducer(self, other):
        if not (self == other) or other.containsOperation("delete"):
           pass
        else:
           other.clearData()

    def __eq__(self,other):
        eq = True
        for k,v in self.__dict__.items():
            if k is not "parent":
                eq = eq and (hasattr(other,k)) and (v == other.__dict__[k])
        return eq

class StringLeaf(Leaf):
    def __init__(self, parent=None, tag=None, value=None):
        super(StringLeaf, self).__init__(parent=parent, tag=tag)
        self.data = value
        """:type: string"""

    def parse(self, root):
        e_data = root.find(self.tag)
        if e_data is not None:
            if len(e_data._children)>0:
                for i in e_data.iter():
                    i.tail = None
                e_data.text = None
                self.data = e_data
            else:
                self.data = e_data.text
            root.remove(e_data)
            self.initialized = True

    def _et(self, parent, inherited=False):
        if self.isInitialized():
            if type(self.data) is ET.Element:
                parent.append(self.data)
            else:
                e_data = ET.SubElement(parent, self.tag)
                e_data.text = self.getAsText()
        return parent

    def getAsText(self):
        if type(self.data) == ET:
            return ET.tostring(self.data, encoding="us-ascii", method="text")
        return self.data

    def setAsText(self, value):
        self.data = value
        self.initialized = True

    def getValue(self):
        return self.data

    def setValue(self, value):
        self.data = value
        self.initialized = True

class Leafref(StringLeaf):
    def __init__(self, parent=None, tag=None, value=None):
        super(Leafref, self).__init__(parent=parent, tag=tag)
        self.target = None
        """:type: Yang"""
        if value is None:
            return
        # cannot bind as parent is not registered yet
        if type(value) is str:
            self.data = value
        elif issubclass(type(value), Yang):
            self.target = value
        else:
            raise ValueError("Leafref value is of unknown type.")

    def setValue(self, value):
        if value is None:
            self.data = None
            self.target = None
            return
        if type(value) is str:
            self.data = value
        elif issubclass(type(value), Yang):
            self.target = value
            self.data = self.getRelPath(value)
        else:
            raise ValueError("Leafref value is of unknown type.")

    def isInitialized(self):
        if (self.data is not None) or (self.target is not None):
            return True
        else:
            return False

    def getAsText(self):
        if self.data is not None:
            return self.data
        if self.target is not None:
            return self.getRelPath(self.target)
        else:
            raise ReferenceError("Leafref getAsText() is called but neither data nor target exists.")

    def getTarget(self):
        if self.data is not None:
            return self.walkPath(self.data)

class ListedYang(Yang):
    def __init__(self, parent=None, tag=None):
        super(ListedYang, self).__init__(parent, tag)

    def getParent(self):
        return self.parent.getParent()

    def getKeyValue(self):
        raise NotImplementedError("getKey() abstract method call")

    def getPath(self):
        keysvalue = self.getKeyValue()
        keys = self.getKeys()
        s = ''
        if type (keysvalue) is tuple:
            s = ', '.join('%s=%s' % t for t in zip(keys, keysvalue))
        else:
            s = keys + "=" + keysvalue
        if self.getParent() is not None:
            return self.getParent().getPath() + "/" + self.tag + "[" + s + "]"
        else:
            return self.tag + "[" + s + "]"

class ListYang(Yang):
    def __init__(self, parent=None, tag=None):
        super(ListYang, self).__init__(parent, tag)
        self._data = dict()

    def getKeys(self):
        return self._data.keys()

    def isInitialized(self):
        if len(self._data) > 0:
            return True
        return False

    def add(self, item):
        if type(item) is tuple or type(item) is list:
            for i in item:
                self.add(i)
        else:
            item.parent = self
            self._data[item.getKeyValue()] = item

    def remove(self, item):
        if type(item) is str or type(item) is int:
            if item in self._data.keys():
                del self._data[item]
        elif type(item) is tuple or type(item) is list:
            for i in item:
                self.delete(i)
        else:
            del self._data[item.getKeyValue()]

    def _et(self, node, inherited=False):
        for key in sorted(self._data):
            self._data[key]._et(node)
        return node

    def __iter__(self):
        return self._data.__iter__()

    def next(self):
        self._data.next()

    def __getitem__(self, key):
        if key in self._data.keys():
            return self._data[key]
        else:
            raise KeyError("key not existing")

    def __setitem__(self, key, value):
        self._data[key] = value
        value.parent = self

    def clearData(self):
        self._data = dict()

    def reducer(self, other):
        for item in other._data.keys():
            if item in self._data.keys():
                if not (self._data[item]== other._data[item]) or other._data[item].containsOperation("delete") :
                    self._data[item].reducer(other._data[item])
                else:
                     del other._data[item]

    def merge(self, target):
        for item in target.getKeys():
            if item not in self.getKeys():
                self.add(target[item])
            else:
                if isinstance(self[item],Yang) \
                and type(self[item]) == type (target[item]):
                    self[item].merge(target[item])

    def __eq__(self, other):
        if self._data == other._data:
            return True
        return False

    def containsOperation(self, operation):
        for key in self._data.keys():
            if self._data[key].containsOperation(operation):
                return True
        return False

    def setOperation(self, operation="delete"):
        super(ListYang, self).setOperation(operation)
        for key in self._data.keys():
            self._data[key].setOperation(operation)
        
#YANG construct: grouping id-name
class GroupingId_name(Yang):
    def __init__(self, parent=None, id=None, name=None):
        super(GroupingId_name, self).__init__(parent)
        #my keyword is: leaf
        self.id = StringLeaf(parent=self, tag="id")
        """:type: StringLeaf"""
        if id is not None:
            self.id.setValue(id)
        #my keyword is: leaf
        self.name = StringLeaf(parent=self, tag="name")
        """:type: StringLeaf"""
        if name is not None:
            self.name.setValue(name)

    def _parse(self, parent=None, root=None):
        self.id.parse(root)
        self.name.parse(root)

#YANG construct: grouping id-name-type
class GroupingId_name_type(GroupingId_name):
    def __init__(self, parent=None, id=None, name=None, type=None):
        GroupingId_name.__init__(self, parent, id, name)
        #my keyword is: leaf
        self.type = StringLeaf(parent=self, tag="type")
        """:type: StringLeaf"""
        if type is not None:
            self.type.setValue(type)

    def _parse(self, parent=None, root=None):
        GroupingId_name._parse(self, parent, root)
        self.type.parse(root)

#YANG construct: grouping port
class GroupingPort(GroupingId_name):
    def __init__(self, parent=None, id=None, name=None, port_type=None, capability=None, sap=None):
        GroupingId_name.__init__(self, parent, id, name)
        #my keyword is: leaf
        self.port_type = StringLeaf(parent=self, tag="port_type")
        """:type: StringLeaf"""
        if port_type is not None:
            self.port_type.setValue(port_type)
        #my keyword is: leaf
        self.capability = StringLeaf(parent=self, tag="capability")
        """:type: StringLeaf"""
        if capability is not None:
            self.capability.setValue(capability)
        #my keyword is: leaf
        self.sap = StringLeaf(parent=self, tag="sap")
        """:type: StringLeaf"""
        if sap is not None:
            self.sap.setValue(sap)

    def _parse(self, parent=None, root=None):
        GroupingId_name._parse(self, parent, root)
        self.port_type.parse(root)
        self.capability.parse(root)
        self.sap.parse(root)

#YANG construct: grouping link-resource
class GroupingLink_resource(Yang):
    def __init__(self, parent=None, delay=None, bandwidth=None):
        super(GroupingLink_resource, self).__init__(parent)
        #my keyword is: leaf
        self.delay = StringLeaf(parent=self, tag="delay")
        """:type: StringLeaf"""
        if delay is not None:
            self.delay.setValue(delay)
        #my keyword is: leaf
        self.bandwidth = StringLeaf(parent=self, tag="bandwidth")
        """:type: StringLeaf"""
        if bandwidth is not None:
            self.bandwidth.setValue(bandwidth)

    def _parse(self, parent=None, root=None):
        self.delay.parse(root)
        self.bandwidth.parse(root)

#YANG construct: grouping flowentry
class GroupingFlowentry(GroupingId_name):
    def __init__(self, parent=None, id=None, name=None, priority=None, port=None, match=None, action=None, out=None, resources=None):
        GroupingId_name.__init__(self, parent, id, name)
        #my keyword is: leaf
        self.priority = StringLeaf(parent=self, tag="priority")
        """:type: StringLeaf"""
        if priority is not None:
            self.priority.setValue(priority)
        #my keyword is: leaf
        self.port = Leafref(parent=self, tag="port", value=port)
        """:type: Leafref"""
        self.port.mandatory = True
        """:type: boolean"""
        #my keyword is: leaf
        self.match = StringLeaf(parent=self, tag="match")
        """:type: StringLeaf"""
        if match is not None:
            self.match.setValue(match)
        self.match.mandatory = True
        """:type: boolean"""
        #my keyword is: leaf
        self.action = StringLeaf(parent=self, tag="action")
        """:type: StringLeaf"""
        if action is not None:
            self.action.setValue(action)
        self.action.mandatory = True
        """:type: boolean"""
        #my keyword is: leaf
        self.out = Leafref(parent=self, tag="out", value=out)
        """:type: Leafref"""
        #my keyword is: container
        self.resources = None
        """:type: FlowentryResources"""
        if resources is not None:
            self.resources = resources
        else:
            self.resources = FlowentryResources(parent=self)

    def _parse(self, parent=None, root=None):
        GroupingId_name._parse(self, parent, root)
        self.priority.parse(root)
        self.port.parse(root)
        self.match.parse(root)
        self.action.parse(root)
        self.out.parse(root)
        e_resources = root.find("resources")
        if e_resources is not None:
            self.resources= FlowentryResources.parse(self, e_resources)

#YANG construct: grouping flowtable
class GroupingFlowtable(Yang):
    def __init__(self, parent=None, flowtable=None):
        super(GroupingFlowtable, self).__init__(parent)
        #my keyword is: container
        self.flowtable = None
        """:type: FlowtableFlowtable"""
        if flowtable is not None:
            self.flowtable = flowtable
        else:
            self.flowtable = FlowtableFlowtable(parent=self)

    def _parse(self, parent=None, root=None):
        e_flowtable = root.find("flowtable")
        if e_flowtable is not None:
            self.flowtable= FlowtableFlowtable.parse(self, e_flowtable)
            for key in e_flowtable.attrib.keys():
                if key == "operation":
                    self.setOperation(e_flowtable.attrib[key])
                    self.operation = e_flowtable.attrib[key]

#YANG construct: grouping link
class GroupingLink(GroupingId_name):
    def __init__(self, parent=None, id=None, name=None, src=None, dst=None, resources=None):
        GroupingId_name.__init__(self, parent, id, name)
        #my keyword is: leaf
        self.src = Leafref(parent=self, tag="src", value=src)
        """:type: Leafref"""
        #my keyword is: leaf
        self.dst = Leafref(parent=self, tag="dst", value=dst)
        """:type: Leafref"""
        #my keyword is: container
        self.resources = None
        """:type: LinkResources"""
        if resources is not None:
            self.resources = resources
        else:
            self.resources = LinkResources(parent=self)

    def _parse(self, parent=None, root=None):
        GroupingId_name._parse(self, parent, root)
        self.src.parse(root)
        self.dst.parse(root)
        e_resources = root.find("resources")
        if e_resources is not None:
            self.resources= LinkResources.parse(self, e_resources)
            for key in e_resources.attrib.keys():
                if key == "operation":
                    self.setOperation(e_resources.attrib[key])
                    self.operation = e_resources.attrib[key]

#YANG construct: grouping links
class GroupingLinks(Yang):
    def __init__(self, parent=None, links=None):
        super(GroupingLinks, self).__init__(parent)
        #my keyword is: container
        self.links = None
        """:type: LinksLinks"""
        if links is not None:
            self.links = links
        else:
            self.links = LinksLinks(parent=self)

    def _parse(self, parent=None, root=None):
        e_links = root.find("links")
        if e_links is not None:
            self.links= LinksLinks.parse(self, e_links)
            for key in e_links.attrib.keys():
                if key == "operation":
                    self.setOperation(e_links.attrib[key])
                    self.operation = e_links.attrib[key]


#YANG construct: grouping software-resource
class GroupingSoftware_resource(Yang):
    def __init__(self, parent=None, cpu=None, mem=None, storage=None):
        super(GroupingSoftware_resource, self).__init__(parent)
        #my keyword is: leaf
        self.cpu = StringLeaf(parent=self, tag="cpu")
        """:type: StringLeaf"""
        if cpu is not None:
            self.cpu.setValue(cpu)
        self.cpu.mandatory = True
        """:type: boolean"""
        #my keyword is: leaf
        self.mem = StringLeaf(parent=self, tag="mem")
        """:type: StringLeaf"""
        if mem is not None:
            self.mem.setValue(mem)
        self.mem.mandatory = True
        """:type: boolean"""
        #my keyword is: leaf
        self.storage = StringLeaf(parent=self, tag="storage")
        """:type: StringLeaf"""
        if storage is not None:
            self.storage.setValue(storage)
        self.storage.mandatory = True
        """:type: boolean"""

    def _parse(self, parent=None, root=None):
        self.cpu.parse(root)
        self.mem.parse(root)
        self.storage.parse(root)

#YANG construct: grouping node
class GroupingNode(GroupingId_name_type, GroupingLinks):
    """Any node: infrastructure or NFs"""
    def __init__(self, parent=None, id=None, name=None, type=None, ports=None, links=None, resources=None):
        GroupingId_name_type.__init__(self, parent, id, name, type)
        GroupingLinks.__init__(self, parent, links)
        #my keyword is: container
        self.ports = None
        """:type: NodePorts"""
        if ports is not None:
            self.ports = ports
        else:
            self.ports = NodePorts(parent=self)
        #my keyword is: container
        self.resources = None
        """:type: NodeResources"""
        if resources is not None:
            self.resources = resources
        else:
            self.resources = NodeResources(parent=self)

    def _parse(self, parent=None, root=None):
        GroupingId_name_type._parse(self, parent, root)
        GroupingLinks._parse(self, parent, root)
        e_ports = root.find("ports")
        if e_ports is not None:
            self.ports= NodePorts.parse(self, e_ports)
            for key in e_ports.attrib.keys():
                if key == "operation":
                    self.setOperation(e_ports.attrib[key])
                    self.operation = e_ports.attrib[key]
        e_resources = root.find("resources")
        if e_resources is not None:
            self.resources= NodeResources.parse(self, e_resources)
            for key in e_resources.attrib.keys():
                if key == "operation":
                    self.setOperation(e_resources.attrib[key])
                    self.operation = e_resources.attrib[key]

#YANG construct: grouping nodes
class GroupingNodes(Yang):
    def __init__(self, parent=None):
        super(GroupingNodes, self).__init__(parent)
        #my keyword is: list
        self.node = ListYang(parent=self, tag="node")
        """:type: list(Node)"""

    def _parse(self, parent=None, root=None):
        e_node = root.find("node")
        while e_node is not None:
            item = Node.parse(self, e_node)
            for key in e_node.attrib.keys():
                if key == "operation":
                    item.setOperation(e_node.attrib[key])
                    item.operation = e_node.attrib[key]
            key = item.getKeyValue()
            self.node[key] = item
            root.remove(e_node)
            e_node = root.find("node")

    def add(self, item):
        if type(item) is tuple or type(item) is list:
            for i in item:
                self.add(i)
        else:
            self.node[item.getKeyValue()] = item

    def __getitem__(self, key):
        return self.node[key]

    def __iter__(self):
        return self.node._data.itervalues()


    def remove(self, item):
        if type(item) is str or type(item) is int:
            if item in self.node.getKeys():
                self.node.remove(item)
        elif type(item) is tuple or type(item) is list:
            for i in item:
                self.remove(i)
        else:
            self.node.remove(item.getKeyValue())
        


#YANG construct: grouping infra-node
class GroupingInfra_node(GroupingNode, GroupingFlowtable):
    def __init__(self, parent=None, id=None, name=None, type=None, ports=None, links=None, resources=None, NF_instances=None, capabilities=None, flowtable=None):
        GroupingNode.__init__(self, parent, id, name, type, ports, links, resources)
        GroupingFlowtable.__init__(self, parent, flowtable)
        #my keyword is: container
        self.NF_instances = None
        """:type: Infra_nodeNf_instances"""
        if NF_instances is not None:
            self.NF_instances = NF_instances
        else:
            self.NF_instances = Infra_nodeNf_instances(parent=self)
        #my keyword is: container
        self.capabilities = None
        """:type: Infra_nodeCapabilities"""
        if capabilities is not None:
            self.capabilities = capabilities
        else:
            self.capabilities = Infra_nodeCapabilities(parent=self)

    def _parse(self, parent=None, root=None):
        GroupingNode._parse(self, parent, root)
        GroupingFlowtable._parse(self, parent, root)
        e_NF_instances = root.find("NF_instances")
        if e_NF_instances is not None:
            self.NF_instances= Infra_nodeNf_instances.parse(self, e_NF_instances)
            for key in e_NF_instances.attrib.keys():
                if key == "operation":
                    self.setOperation(e_NF_instances.attrib[key])
                    self.operation = e_NF_instances.attrib[key]
        e_capabilities = root.find("capabilities")
        if e_capabilities is not None:
            self.capabilities= Infra_nodeCapabilities.parse(self, e_capabilities)
            for key in e_capabilities.attrib.keys():
                if key == "operation":
                    self.setOperation(e_capabilities.attrib[key])
                    self.operation = e_capabilities.attrib[key]

#YANG construct: list flowentry
class Flowentry(GroupingFlowentry, ListedYang):
    def __init__(self, parent=None, id=None, name=None, priority=None, port=None, match=None, action=None, out=None, resources=None):
        GroupingFlowentry.__init__(self, parent, id, name, priority, port, match, action, out, resources)
        self.tag="flowentry"

    def _parse(self, parent=None, root=None):
        GroupingFlowentry._parse(self, parent, root)

    def getKeyValue(self):
        return self.id.getValue()

    def getKeys(self):
        return self.id.tag

#YANG construct: list link
class Link(GroupingLink, ListedYang):
    def __init__(self, parent=None, id=None, name=None, src=None, dst=None, resources=None):
        GroupingLink.__init__(self, parent, id, name, src, dst, resources)
        self.tag="link"

    def _parse(self, parent=None, root=None):
        GroupingLink._parse(self, parent, root)

    def getKeyValue(self):
        keys =[]
        keys.append(self.src.getValue())
        keys.append(self.dst.getValue())
        return tuple(keys)

    def getKeys(self):
        keys =[]
        keys.append(self.src.tag)
        keys.append(self.dst.tag)
        return tuple(keys)

#YANG construct: list port
class Port(GroupingPort, ListedYang):
    def __init__(self, parent=None, id=None, name=None, port_type=None, capability=None, sap=None):
        GroupingPort.__init__(self, parent, id, name, port_type, capability, sap)
        self.tag="port"

    def _parse(self, parent=None, root=None):
        GroupingPort._parse(self, parent, root)

    def getKeyValue(self):
        return self.id.getValue()

    def getKeys(self):
        return self.id.tag

#YANG construct: list node
class Node(GroupingNode, ListedYang):
    def __init__(self, parent=None, id=None, name=None, type=None, ports=None, links=None, resources=None):
        GroupingNode.__init__(self, parent, id, name, type, ports, links, resources)
        self.tag="node"

    def _parse(self, parent=None, root=None):
        GroupingNode._parse(self, parent, root)

    def getKeyValue(self):
        return self.id.getValue()

    def getKeys(self):
        return self.id.tag



#YANG construct: list node
class Infra_node(GroupingInfra_node, ListedYang):
    def __init__(self, parent=None, id=None, name=None, type=None, ports=None, links=None, resources=None, NF_instances=None, capabilities=None, flowtable=None):
        GroupingInfra_node.__init__(self, parent, id, name, type, ports, links, resources, NF_instances, capabilities, flowtable)
        self.tag="node"

    def _parse(self, parent=None, root=None):
        GroupingInfra_node._parse(self, parent, root)

    def getKeyValue(self):
        return self.id.getValue()

    def getKeys(self):
        return self.id.tag


#YANG construct: container resources
class FlowentryResources(GroupingLink_resource):
    def __init__(self, parent=None, delay=None, bandwidth=None):
        GroupingLink_resource.__init__(self, parent, delay, bandwidth)
        self.tag="resources"

    def _parse(self, parent=None, root=None):
        GroupingLink_resource._parse(self, parent, root)


#YANG construct: container flowtable
class FlowtableFlowtable(Yang):
    def __init__(self, parent=None):
        super(FlowtableFlowtable, self).__init__(parent)
        self.tag="flowtable"
        #my keyword is: list
        self.flowentry = ListYang(parent=self, tag="flowentry")
        """:type: list(Flowentry)"""

    def _parse(self, parent=None, root=None):
        e_flowentry = root.find("flowentry")
        while e_flowentry is not None:
            item = Flowentry.parse(self, e_flowentry)
            for key in e_flowentry.attrib.keys():
                if key == "operation":
                    item.setOperation(e_flowentry.attrib[key])
                    item.operation = e_flowentry.attrib[key]
            key = item.getKeyValue()
            self.flowentry[key] = item
            root.remove(e_flowentry)
            e_flowentry = root.find("flowentry")

    def add(self, item):
        if type(item) is tuple or type(item) is list:
            for i in item:
                self.add(i)
        else:
            self.flowentry[item.getKeyValue()] = item

    def __getitem__(self, key):
        return self.flowentry[key]

    def __iter__(self):
        return self.flowentry._data.itervalues()

    def remove(self, item):
        if type(item) is str or type(item) is int:
            if item in self.flowentry.getKeys():
                self.flowentry.remove(item)
        elif type(item) is tuple or type(item) is list:
            for i in item:
                self.remove(i)
        else:
            self.flowentry.remove(item.getKeyValue())
        


#YANG construct: container resources
class LinkResources(GroupingLink_resource):
    def __init__(self, parent=None, delay=None, bandwidth=None):
        GroupingLink_resource.__init__(self, parent, delay, bandwidth)
        self.tag="resources"

    def _parse(self, parent=None, root=None):
        GroupingLink_resource._parse(self, parent, root)

#YANG construct: container links
class LinksLinks(Yang):
    def __init__(self, parent=None):
        super(LinksLinks, self).__init__(parent)
        self.tag="links"
        #my keyword is: list
        self.link = ListYang(parent=self, tag="link")
        """:type: list(Link)"""

    def _parse(self, parent=None, root=None):
        e_link = root.find("link")
        while e_link is not None:
            item = Link.parse(self, e_link)
            for key in e_link.attrib.keys():
                if key == "operation":
                    item.setOperation(e_link.attrib[key])
                    item.operation = e_link.attrib[key]
            key = item.getKeyValue()
            self.link[key] = item
            root.remove(e_link)
            e_link = root.find("link")

    def add(self, item):
        if type(item) is tuple or type(item) is list:
            for i in item:
                self.add(i)
        else:
            self.link[item.getKeyValue()] = item

    def __getitem__(self, key):
        return self.link[key]

    def __iter__(self):
        return self.link._data.itervalues()


    def remove(self, item):
        if type(item) is str or type(item) is int:
            if item in self.link.getKeys():
                self.link.remove(item)
        elif type(item) is tuple or type(item) is list:
            for i in item:
                self.remove(i)
        else:
            self.link.remove(item.getKeyValue())
        


#YANG construct: container ports
class NodePorts(Yang):
    def __init__(self, parent=None):
        super(NodePorts, self).__init__(parent)
        self.tag="ports"
        #my keyword is: list
        self.port = ListYang(parent=self, tag="port")
        """:type: list(Port)"""

    def _parse(self, parent=None, root=None):
        e_port = root.find("port")
        while e_port is not None:
            item = Port.parse(self, e_port)
            for key in e_port.attrib.keys():
                if key == "operation":
                    item.setOperation(e_port.attrib[key])
                    item.operation = e_port.attrib[key]
            key = item.getKeyValue()
            self.port[key] = item
            root.remove(e_port)
            e_port = root.find("port")

    def add(self, item):
        if type(item) is tuple or type(item) is list:
            for i in item:
                self.add(i)
        else:
            self.port[item.getKeyValue()] = item

    def __getitem__(self, key):
        return self.port[key]

    def __iter__(self):
        return self.port._data.itervalues()


    def remove(self, item):
        if type(item) is str or type(item) is int:
            if item in self.port.getKeys():
                self.port.remove(item)
        elif type(item) is tuple or type(item) is list:
            for i in item:
                self.remove(i)
        else:
            self.port.remove(item.getKeyValue())
        


#YANG construct: container resources
class NodeResources(GroupingSoftware_resource):
    def __init__(self, parent=None, cpu=None, mem=None, storage=None):
        GroupingSoftware_resource.__init__(self, parent, cpu, mem, storage)
        self.tag="resources"

    def _parse(self, parent=None, root=None):
        GroupingSoftware_resource._parse(self, parent, root)


#YANG construct: container NF_instances
class Infra_nodeNf_instances(GroupingNodes):
    def __init__(self, parent=None):
        GroupingNodes.__init__(self, parent, )
        self.tag="NF_instances"

    def _parse(self, parent=None, root=None):
        GroupingNodes._parse(self, parent, root)


#YANG construct: container capabilities
class Infra_nodeCapabilities(Yang):
    def __init__(self, parent=None, supported_NFs=None):
        super(Infra_nodeCapabilities, self).__init__(parent)
        self.tag="capabilities"
        #my keyword is: container
        self.supported_NFs = None
        """:type: Infra_nodeCapabilitiesSupported_nfs"""
        if supported_NFs is not None:
            self.supported_NFs = supported_NFs
        else:
            self.supported_NFs = Infra_nodeCapabilitiesSupported_nfs(parent=self)

    def _parse(self, parent=None, root=None):
        e_supported_NFs = root.find("supported_NFs")
        if e_supported_NFs is not None:
            self.supported_NFs= Infra_nodeCapabilitiesSupported_nfs.parse(self, e_supported_NFs)
            for key in e_supported_NFs.attrib.keys():
                if key == "operation":
                    self.setOperation(e_supported_NFs.attrib[key])
                    self.operation = e_supported_NFs.attrib[key]


#YANG construct: container supported_NFs
class Infra_nodeCapabilitiesSupported_nfs(GroupingNodes):
    def __init__(self, parent=None):
        GroupingNodes.__init__(self, parent, )
        self.tag="supported_NFs"

    def _parse(self, parent=None, root=None):
        GroupingNodes._parse(self, parent, root)


#YANG construct: container virtualizer
class Virtualizer(GroupingId_name, GroupingLinks):
    """Container for a single virtualizer"""
    def __init__(self, parent=None, id=None, name=None, nodes=None, links=None):
        GroupingId_name.__init__(self, parent, id, name)
        GroupingLinks.__init__(self, parent, links)
        self.tag="virtualizer"
        #my keyword is: container
        self.nodes = None
        """:type: VirtualizerNodes"""
        if nodes is not None:
            self.nodes = nodes
        else:
            self.nodes = VirtualizerNodes(parent=self)

    def _parse(self, parent=None, root=None):
        GroupingId_name._parse(self, parent, root)
        GroupingLinks._parse(self, parent, root)
        e_nodes = root.find("nodes")
        if e_nodes is not None:
            self.nodes= VirtualizerNodes.parse(self, e_nodes)
            for key in e_nodes.attrib.keys():
                if key == "operation":
                    self.setOperation(e_nodes.attrib[key])
                    self.operation = e_nodes.attrib[key]


#YANG construct: container nodes
class VirtualizerNodes(Yang):
    def __init__(self, parent=None):
        super(VirtualizerNodes, self).__init__(parent)
        self.tag="nodes"
        #my keyword is: list
        self.node = ListYang(parent=self, tag="node")
        """:type: list(Infra_node)"""

    def _parse(self, parent=None, root=None):
        e_node = root.find("node")
        while e_node is not None:
            item = Infra_node.parse(self, e_node)
            for key in e_node.attrib.keys():
                if key == "operation":
                    item.setOperation(e_node.attrib[key])
                    item.operation = e_node.attrib[key]
            key = item.getKeyValue()
            self.node[key] = item
            root.remove(e_node)
            e_node = root.find("node")

    def add(self, item):
        if type(item) is tuple or type(item) is list:
            for i in item:
                self.add(i)
        else:
            self.node[item.getKeyValue()] = item

    def __getitem__(self, key):
        return self.node[key]

    def __iter__(self):
        return self.node._data.itervalues()

    def remove(self, item):
        if type(item) is str or type(item) is int:
            if item in self.node.getKeys():
                self.node.remove(item)
        elif type(item) is tuple or type(item) is list:
            for i in item:
                self.remove(i)
        else:
            self.node.remove(item.getKeyValue())
        


