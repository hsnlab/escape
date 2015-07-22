# Copyright 2015 Balazs Sonkoly, Janos Czentye
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Classes for handling the elements of the NF-FG data structure
"""
import json
import collections
import weakref
from __builtin__ import id as generate


################################################################################
# ---------- BASE classes of NFFG elements -------------------
################################################################################

class Persistable(object):
  """
  Define general persist function for the whole NFFG structure.
  """

  def persist (self):
    """
    Common function to persist the actual element into a plain text format.

    :return: generated object structure fit to JSON
    :rtype: object
    """
    raise NotImplementedError("All NF-FG entity must be persistable!")

  def load (self, data):
    """
    Common function to fill self with data from JSON data.

    :param data: object structure in JSON
    :return: self
    """
    raise NotImplementedError("All NF-FG entity must support load function!")

  @classmethod
  def parse (cls, data, *args, **kwargs):
    """
    Common function to parse the given JSON object structure as the actual NF-FG
    entity type and return a newly created object.

    :param data: raw JSON object structure
    :type data: object
    :return: parsed data as the entity type
    :rtype: :any:`Persistable`
    """
    return cls().load(data, *args, **kwargs)


class Element(Persistable):
  """
  Main base class for NF-FG elements with unique id.

  Contains the common functionality.
  """

  def __init__ (self, id=None, type="ELEMENT"):
    """
    Init.

    :param id: optional identification (generated by default)
    :type id: str or int
    :param type: explicit object type both for nodes and edges
    :type type: str
    :return: None
    """
    super(Element, self).__init__()
    self.id = str(id) if id is not None else str(generate(self))
    self.type = type

  def persist (self):
    # Need to override
    super(Element, self).persist()

  def load (self, data):
    # Need to override
    super(Element, self).load(data)

  def __getitem__ (self, item):
    if hasattr(self, item):
      return getattr(self, item)
    else:
      raise KeyError(
        "%s object has no key: %s" % (self.__class__.__name__, item))

  def __setitem__ (self, key, value):
    if hasattr(self, key):
      return setattr(self, key, value)
    else:
      raise KeyError(
        "%s object has no key: %s" % (self.__class__.__name__, key))


class PortContainer(object):
  """
  Basic container class for ports.

  Implements a Container-like behavior for getting a Port with id:
    cont = PortContainer()
    ...
    cont["port_id"]
  """

  def __init__ (self, container=None):
    self.container = container if container is not None else []

  def __getitem__ (self, id):
    for port in self.container:
      if port.id == str(id):
        return port
    raise KeyError("Port with id: %s is not defined!" % id)

  def __iter__ (self):
    return iter(self.container)

  def __len__ (self):
    return len(self.container)

  def __contains__ (self, item):
    return item in self.container

  def append (self, item):
    return self.container.append(item)

  def remove (self, item):
    return self.container.remove(item)


class Node(Element):
  """
  Base class for different types of nodes in the NF-FG.
  """
  # Node type constants:
  # Infrastructure node --> abstract node represents one or more physical node
  INFRA = "INFRA"
  # SAP nodes --> abstract node represents end point/ports of a service
  SAP = "SAP"
  # Network Function (NF) node --> abstract node represents a virtual function
  NF = "NF"

  def __init__ (self, type, id=None, name=None):
    """
    Init.

    :param type: node type
    :type type: str
    :param id: optional id
    :type id: str or int
    :param name: optional name
    :type name: str
    :return: None
    """
    super(Node, self).__init__(id=id, type=type)
    self.name = name  # optional
    self.ports = PortContainer()  # list of Ports

  def add_port (self, id=None, properties=None):
    """
    Add a port with the given params to the Node.

    :param id: optional id
    :type id: str or int
    :param properties: supported properties of the port (one or more as list)
    :type properties: str or iterable(str)
    :return: newly created and stored Port object
    :rtype: :any:`Port`
    """
    port = Port(self, properties=properties, id=id)
    self.ports.append(port)
    return port

  def del_port (self, id):
    """
    Remove the port with the given id from the Node.

    :param id: port id
    :type id: int or str
    :return: the actual Port is found and removed or not
    :rtype: bool
    """
    for port in self.ports:
      if port.id == id:
        return self.ports.remove(port)
      return True

  def persist (self):
    node = {"id": str(self.id)}
    ports = [port.persist() for port in self.ports]
    if ports:
      node["ports"] = ports
    if self.name is not None:
      node["name"] = str(self.name)
    return node

  def load (self, data):
    self.id = data['id']
    self.name = data.get('name')  # optional
    for port in data.get('ports', ()):
      self.add_port(id=port['id'], properties=port.get('property'))
    return self

  def __repr__ (self):
    return "| ID: %s, Type: %s --> %s |" % (
      self.id, self.type, super(Element, self).__repr__())


class Link(Element):
  """
  Base class for different types of edges in the NF-FG.
  """
  # Edge type constants:
  # Static link --> physical link between saps and infras
  STATIC = "STATIC"
  # Dynamic link --> virtual link between nfs and infras created on demand
  DYNAMIC = "DYNAMIC"
  # SG next hop --> virtual link to describe connection between elements in SG
  SG = "SG"
  # Requirement --> virtual link to define constraints between SG elements
  REQUIREMENT = "REQUIREMENT"

  def __init__ (self, src=None, dst=None, type=None, id=None):
    """
    Init.

    :param src: source port
    :type src: :any:`Port`
    :param dst: destination port
    :type dst: :any:`Port`
    :param type: link type
    :type type: str
    :param id: optional id
    :type id: str or int
    :return: None
    """
    super(Link, self).__init__(id=id, type=type)
    if (src is not None and not isinstance(src, Port)) or (
             dst is not None and not isinstance(dst, Port)):
      raise RuntimeError("Src and dst must be Port objects!")
    # Reference to src Port object
    self.src = src  # mandatory
    # Reference to dst Port object
    self.dst = dst  # mandatory

  def persist (self):
    return {"src_node": str(self.src.node.id), "src_port": str(self.src.id),
            "dst_node": str(self.dst.node.id), "dst_port": str(self.dst.id)}

  def load (self, data, container=None):
    if container is None:
      raise RuntimeError(
        "Container reference is not given for edge endpoint lookup!")
    self.src = container.get_port(data['src_node'], data['src_port'])
    self.dst = container.get_port(data['dst_node'], data['dst_port'])
    if self.src is None or self.dst is None:
      raise RuntimeError("Edge not found with params: %s !" % data)
    return self

  def __repr__ (self):
    return "| ID: %s, Type: %s, src: %s, dst: %s --> %s |" % (
      self.id, self.type, self.src.id, self.dst.id,
      super(Element, self).__repr__())


################################################################################
# ---------- NODE AND LINK RESOURCES, ATTRIBUTES -------------------
################################################################################

class NodeResource(Persistable):
  """
  Class for storing resource information for Nodes.
  """
  # YANG: grouping node_resource

  def __init__ (self, cpu=None, mem=None, storage=None, delay=None,
       bandwidth=None):
    """
    Init.

    :param cpu: CPU resource
    :type cpu: float
    :param mem: memory resource
    :type mem: float
    :param storage: storage resource
    :type storage: float
    :param delay: delay property of the Node
    :type delay: float
    :param bandwidth: bandwidth property of the Node
    :type bandwidth: float
    :return: None
    """
    super(NodeResource, self).__init__()
    # container: compute
    self.cpu = cpu
    self.mem = mem
    # container
    self.storage = storage
    self.delay = delay
    self.bandwidth = bandwidth

  def persist (self):
    res = {}
    if self.cpu is not None:
      res["cpu"] = self.cpu
    if self.mem is not None:
      res["mem"] = self.mem
    if self.storage is not None:
      res["storage"] = self.storage
    if self.delay is not None:
      res["delay"] = self.delay
    if self.bandwidth is not None:
      res["bandwidth"] = self.bandwidth
    return res

  def load (self, data):
    self.storage = data.get('storage')
    self.delay = data.get('delay')
    self.bandwidth = data.get('bandwidth')
    self.cpu = data.get('cpu')
    self.mem = data.get('mem')
    return self

  def __getitem__ (self, item):
    if hasattr(self, item):
      return getattr(self, item)
    else:
      raise KeyError(
        "%s object has no key: %s" % (self.__class__.__name__, item))

  def __setitem__ (self, key, value):
    if hasattr(self, key):
      return setattr(self, key, value)
    else:
      raise KeyError(
        "%s object has no key: %s" % (self.__class__.__name__, key))


class Flowrule(Persistable):
  """
  Class for storing a flowrule.
  """

  def __init__ (self, match="*", action=""):
    """
    Init.

    :param match: matching rule
    :type match: str
    :param action: forwarding action
    :type action: str
    :return: None
    """
    super(Flowrule, self).__init__()
    self.match = match  # mandatory
    self.action = action  # mandatory

  def persist (self):
    return {"match": str(self.match), "action": str(self.action)}

  def load (self, data):
    self.match = data.get('match', "*")
    self.action = data.get('action', "")
    return self


class Port(Element):
  """
  Class for storing a port of an NF.
  """
  # Port type
  TYPE = "PORT"

  def __init__ (self, node, properties=None, id=None):
    """
    Init.

    :param node: container node
    :type node: :any:`Node`
    :param id: optional id
    :type id: str or int
    :param properties: supported properties of the port
    :type properties: str or iterable(str)
    :return: None
    """
    super(Port, self).__init__(id=id, type=self.TYPE)
    if not isinstance(node, Node):
      raise RuntimeError("Port's container node must be derived from Node!")
    # weakref to avoid circular reference
    self.node = weakref.proxy(node)
    if isinstance(properties, (str, unicode)):
      self.properties = [str(properties), ]
    elif isinstance(properties, collections.Iterable):
      self.properties = [str(p) for p in properties]
    elif properties is None:
      self.properties = []
    else:
      raise RuntimeError(
        "Port's properties attribute must be iterable or a string!")

  def add_property (self, property):
    """
    Add a property to the port.

    :param property: property
    :type property: str
    :return: list of properties
    :rtype: list
    """
    self.properties.append(property)
    return self.properties

  def del_property (self, property):
    """
    Remove the property from the Port.

    :param property: property
    :type property: str
    :return: None
    """
    self.properties.remove(property)

  def persist (self):
    port = {"id": str(self.id)}
    property = [property for property in self.properties]
    if property:
      port["property"] = property
    return port

  def load (self, data):
    self.id = str(data['id'])
    for property in data.get('property', ()):
      self.properties.append(property)


class InfraPort(Port):
  """
  Class for storing a port of Infra Node and handles flowrules.
  """

  def __init__ (self, node, properties=None, id=None):
    """
    Init.

    :param node: container node
    :type node: :any:`Node`
    :param id: optional id
    :type id: str or int
    :param properties: supported properties of the port
    :type properties: str or iterable(str)
    :return: None
    """
    super(InfraPort, self).__init__(node=node, id=id, properties=properties)
    self.flowrules = []

  def add_flowrule (self, match, action):
    """
    Add a flowrule with the given params to the port of an Infrastructure Node.

    :param match: matching rule
    :type match: str
    :param action: forwarding action
    :type action: str
    :return: newly created and stored flowrule
    :rtype: :any:`Flowrule`
    """
    flowrule = Flowrule(match=match, action=action)
    self.flowrules.append(flowrule)
    return flowrule

  def del_flowrule (self, match, action):
    """
    Remove the first flowrule with the given parameters from the Port.

    :param match: matching rule
    :type match: str
    :param action: forwarding action
    :type action: str
    :return: the actual FlowRule is found and removed or not
    :rtype: bool
    """
    for f in self.flowrules:
      if f.match == match and f.action == action:
        self.flowrules.remove(f)
        return True

  def persist (self):
    port = super(InfraPort, self).persist()
    flowrules = [f.persist() for f in self.flowrules]
    if flowrules:
      port["flowrules"] = flowrules
    return port

  def load (self, data):
    super(InfraPort, self).load(data)
    for flowrule in data('flowrules', ()):
      self.add_flowrule(match=flowrule.get('match'),
                        action=flowrule.get('action'))


################################################################################
# ------------------------ NF / SAP / INFRASTRUCTURE NODES -------------------
################################################################################

class NodeNF(Node):
  """
  Network Function (NF) nodes in the graph.
  """

  def __init__ (self, id=None, name=None, func_type=None, dep_type=None,
       res=None):
    """
    Init.

    :param func_type: functional type (default: "None")
    :type func_type: str
    :param dep_type: deployment type (default: "None")
    :type dep_type: str
    :param res: optional NF resources
    :type res: :any:`NodeResource`
    :return: None
    """
    super(NodeNF, self).__init__(id=id, type=Node.NF, name=name)
    self.functional_type = func_type  # mandatory
    # container: specification
    self.deployment_type = dep_type
    self.resources = res if res is not None else NodeResource()
    # container

  def persist (self):
    node = super(NodeNF, self).persist()
    if self.functional_type is not None:
      node["functional_type"] = str(self.functional_type)
    specification = {}
    if self.deployment_type is not None:
      specification["deployment_type"] = str(self.deployment_type)
    res = self.resources.persist()
    if res:
      specification["resources"] = res
    if specification:
      node["specification"] = specification
    return node

  def load (self, data):
    super(NodeNF, self).load(data)
    self.functional_type = data.get('functional_type')
    if 'specification' in data:
      self.deployment_type = data['specification'].get('deployment_type')
      if 'resources' in data['specification']:
        self.resources.load(data['specification']['resources'])
    return self


class NodeSAP(Node):
  """
  Class for SAP nodes in the NF-FG.
  """

  def __init__ (self, id=None, name=None):
    super(NodeSAP, self).__init__(id=id, type=Node.SAP, name=name)


class NodeInfra(Node):
  """
  Class for infrastructure nodes in the NF-FG.
  """
  # Default Infrastructure Node type
  DEFAULT_INFRA_TYPE = 0
  # Default domain type
  DEFAULT_INFRA_DOMAIN = None

  def __init__ (self, id=None, name=None, domain=None, infra_type=None,
       res=None):
    """
    Init.

    :param domain: domain of the Infrastructure Node
    :type domain: str
    :param infra_type: type of the Infrastructure Node
    :type infra_type: int or str
    :param res: optional Infra resources
    :type res: :any:`NodeResource`
    :return: None
    """
    super(NodeInfra, self).__init__(id=id, type=Node.INFRA, name=name)
    self.domain = domain if domain is not None else self.DEFAULT_INFRA_DOMAIN
    self.infra_type = infra_type if infra_type is not None else \
      self.DEFAULT_INFRA_TYPE
    self.resources = res if res is not None else NodeResource()

  def add_port (self, id=None, properties=None):
    """
    Add a port with the given params to the Infrastructure Node.

    :param id: optional id
    :type id: str or int
    :param properties: supported properties of the port (one or more as list)
    :type properties: str or iterable(str)
    :return: newly created and stored Port object
    :rtype: :any:`Port`
    """
    port = InfraPort(self, properties=properties, id=id)
    self.ports.append(port)
    return port

  def persist (self):
    node = super(NodeInfra, self).persist()
    if self.domain is not None:
      node["domain"] = str(self.domain)
    node["type"] = str(self.infra_type)
    res = self.resources.persist()
    if res:
      node["resources"] = res
    return node

  def load (self, data):
    self.id = str(data['id'])
    self.name = data.get('name')  # optional
    for port in data.get('ports', ()):
      infra_port = self.add_port(id=port['id'], properties=port.get('property'))
      for flowrule in port.get('flowrules', ()):
        infra_port.flowrules.append(Flowrule.parse(flowrule))
    self.domain = data.get('domain', self.DEFAULT_INFRA_DOMAIN)  # optional
    self.infra_type = data['type']
    if 'resources' in data:
      self.resources.load(data['resources'])
    return self


################################################################################
# ---------- SG REQUIREMENTS / SG NEXT_HOPS / INFRASTRUCTURE LINKS -----------
################################################################################


class EdgeLink(Link):
  """
  Class for static and dynamic links in the NF-FG.

  Represent a static or dynamic link.
  """

  def __init__ (self, src=None, dst=None, type=None, id=None, delay=None,
       bandwidth=None):
    """
    Init.

    :param src: source port
    :type src: :any:`Port`
    :param dst: destination port
    :type dst: :any:`Port`
    :param type: type of the link (default: Link.STATIC)
    :type type: str
    :param id: optional link id
    :type id: str or int
    :param delay: delay resource
    :type delay: float
    :param bandwidth: bandwidth resource
    :type bandwidth: float
    :return: None
    """
    type = type if type is not None else Link.STATIC
    super(EdgeLink, self).__init__(src=src, dst=dst, type=type, id=id)
    self.delay = delay  # optional
    self.bandwidth = bandwidth  # optional

  def persist (self):
    link = super(EdgeLink, self).persist()
    if self.delay is not None:
      link["delay"] = self.delay
    if self.bandwidth is not None:
      link["bandwidth"] = self.bandwidth
    return link

  def load (self, data, container=None):
    super(EdgeLink, self).load(data=data, container=container)
    self.delay = data.get('delay')
    self.bandwidth = data.get('bandwidth')
    return self


class EdgeSGLink(Link):
  """
  Class for links of SG.

  Represent an edge between SG elements.
  """

  def __init__ (self, src=None, dst=None, id=None, flowclass=None):
    """
    Init.

    :param src: source port
    :type src: :any:`Port`
    :param dst: destination port
    :type dst: :any:`Port`
    :param id: optional id
    :type id: str or int
    :param flowclass: flowclass of SG next hop link a.k.a a match
    :type flowclass: str
    :return: None
    """
    super(EdgeSGLink, self).__init__(src=src, dst=dst, type=Link.SG, id=id)
    self.flowclass = flowclass  # flowrule without action

  def persist (self):
    link = super(EdgeSGLink, self).persist()
    if self.flowclass is not None:
      link["flowclass"] = str(self.flowclass)
    return link

  def load (self, data, container=None):
    super(EdgeSGLink, self).load(data=data, container=container)
    self.flowclass = data.get('flowclass')
    return self


class EdgeReq(Link):
  """
  Class for constraint of networking parameters between SG elements.

  Class for requirements between arbitrary NF modes.
  """

  def __init__ (self, src=None, dst=None, id=None, delay=None, bandwidth=None):
    """
    Init.

    :param src: source port
    :type src: :any:`Port`
    :param dst: destination port
    :type dst: :any:`Port`
    :param id: optional id
    :type id: str or int
    :param delay: delay resource
    :type delay: float
    :param bandwidth: bandwidth resource
    :type bandwidth: float
    :return: None
    """
    super(EdgeReq, self).__init__(src=src, dst=dst, type=Link.REQUIREMENT,
                                  id=id)
    self.delay = delay  # optional
    self.bandwidth = bandwidth  # optional

  def persist (self):
    link = super(EdgeReq, self).persist()
    if self.delay is not None:
      link["delay"] = self.delay
    if self.bandwidth is not None:
      link["bandwidth"] = self.bandwidth
    return link

  def load (self, data, container=None):
    super(EdgeReq, self).load(data=data, container=container)
    self.delay = data.get('delay')
    self.bandwidth = data.get('bandwidth')
    return self


################################################################################
# --------========== MAIN CONTAINER STARTS HERE =========-------------
################################################################################

class NFFGModel(Element):
  """
  Wrapper class for a single NF-FG.

  Network Function Forwarding Graph (NF-FG) data model.
  """
  # Default version
  VERSION = "1.0"
  # Namespace
  NAMESPACE = "http://csikor.tmit.bme.hu/netconf/unify/nffg"
  # prefix
  PREFIX = "nffg"
  # Organization
  ORGANIZATION = "BME-TMIT"
  # Description
  DESCRIPTION = "Network Function Forwarding Graph (NF-FG) data model"
  # Container type
  TYPE = "NFFG"

  def __init__ (self, id=None, name=None, version=None):
    """
    Init

    :param id: optional NF-FG identifier (generated by default)
    :type id: str or int
    :param name: optional NF-FG name
    :type name: str
    :param version: optional version (default: 1.0)
    :type version: str
    :return: None
    """
    super(NFFGModel, self).__init__(id=id, type=self.TYPE)
    self.name = name
    self.version = str(version) if version is not None else self.VERSION
    self.node_nfs = []
    self.node_saps = []
    self.node_infras = []
    self.edge_links = []
    self.edge_sg_nexthops = []
    self.edge_reqs = []

  @property
  def nodes (self):
    """
    Return all the node in the Container as a list.

    :return: nodes
    :rtype: list
    """
    # shallow copy
    nodes = self.node_nfs[:]
    nodes.extend(self.node_saps)
    nodes.extend(self.node_infras)
    return nodes

  @property
  def edges (self):
    """
    Return all the edges in the Container as a list.

    :return: edges
    :rtype: list
    """
    # shallow copy
    edges = self.edge_links[:]
    edges.extend(self.edge_reqs)
    edges.extend(self.edge_sg_nexthops)
    return edges

  def get_port (self, node_id, port_id):
    """
    Return the Port reference according to the given Node and Port ids.

    :param node_id: node id
    :type node_id: str
    :param port_id: port id
    :type port_id: str
    :return: port object
    :rtype: :any:`Port`
    """
    for node in self.nodes:
      if node.id == node_id:
        for port in node.ports:
          if port.id == port_id:
            return port
    return None

  def add_nf (self, **kwargs):
    """
    Create and store a NF Node with the given parameters.

    :return: the created NF
    :rtype: :any:`NodeNF`
    """
    nf = NodeNF(**kwargs)
    for node in self.node_nfs:
      if node.id == nf.id:
        raise RuntimeError(
          "NodeNF with id: %s already exist in the container!" % node.id)
    self.node_nfs.append(nf)
    return nf

  def del_nf (self, id):
    """
    Remove the NF Node with the given id.

    :param id: NF id
    :param id: str
    :return: the actual Node is found and removed or not
    :rtype: bool
    """
    for node in self.node_nfs:
      if node.id == id:
        self.node_nfs.remove(node)
        return True

  def add_sap (self, **kwargs):
    """
    Create and store a SAP Node with the given parameters.

    :return: the created SAP
    :rtype: :any:`NodeSAP`
    """
    sap = NodeSAP(**kwargs)
    for node in self.node_saps:
      if node.id == sap.id:
        raise RuntimeError(
          "NodeNF with id: %s already exist in the container!" % node.id)
    self.node_saps.append(sap)
    return sap

  def del_sap (self, id):
    """
    Remove the SAP Node with the given id.

    :param id: SAP id
    :param id: str
    :return: the actual Node is found and removed or not
    :rtype: bool
    """
    for node in self.node_saps:
      if node.id == id:
        self.node_saps.remove(node)
        return True

  def add_infra (self, **kwargs):
    """
    Create and store an Infrastructure Node with the given parameters.

    :return: the created Infra
    :rtype: :any:`NodeInfra`
    """
    infra = NodeInfra(**kwargs)
    for node in self.node_infras:
      if node.id == infra.id:
        raise RuntimeError(
          "NodeNF with id: %s already exist in the container!" % node.id)
    self.node_infras.append(infra)
    return infra

  def del_infra (self, id):
    """
    Remove Infrastructure Node with the given id.

    :param id: Infra id
    :param id: str
    :return: the actual Node is found and removed or not
    :rtype: bool
    """
    for node in self.node_infras:
      if node.id == id:
        self.node_infras.remove(node)
        return True

  def add_link (self, src, dst, **kwargs):
    """
    Create and store a Link Edge with the given src and dst nodes.

    :param src: source node
    :type src: :any:`Node`
    :param dst:  destination node
    :type dst: :any:`Node`
    :return: the created edge
    :rtype: :any:`EdgeLink`
    """
    link = EdgeLink(src=src, dst=dst, **kwargs)
    for edge in self.edge_links:
      if edge.src.id == src.id and edge.dst.id == dst.id:
        raise RuntimeError(
          "EdgeLink with src(%s) and dst(%s) endpoints already exist in the "
          "container!" % (src.id, dst.id))
    self.edge_links.append(link)
    return link

  def del_link (self, src, dst):
    """
    Remove Link Edge with given src and dst nodes.

    :param src: source node
    :type src: :any:`Node`
    :param dst:  destination node
    :type dst: :any:`Node`
    :return: the actual Edge is found and removed or not
    :rtype: bool
    """
    for edge in self.edge_links:
      if edge.src.id == src.id and edge.dst.id == dst.id:
        self.edge_links.remove(edge)
        return True

  def add_sg_hop (self, src, dst, **kwargs):
    """
    Create and store an SG next hop Edge with the given src and dst nodes.

    :param src: source node
    :type src: :any:`Node`
    :param dst:  destination node
    :type dst: :any:`Node`
    :return: the created edge
    :rtype: :any:`EdgeSGLink`
    """
    hop = EdgeSGLink(src=src, dst=dst, **kwargs)
    for edge in self.edge_sg_nexthops:
      if edge.src.id == src.id and edge.dst.id == dst.id:
        raise RuntimeError(
          "EdgeSGLink with src(%s) and dst(%s) endpoints already exist in the "
          "container!" % (src.id, dst.id))
    self.edge_sg_nexthops.append(hop)
    return hop

  def del_sg_hop (self, src, dst):
    """
    Remove SG next hop Edge with given src and dst nodes.

    :param src: source node
    :type src: :any:`Node`
    :param dst:  destination node
    :type dst: :any:`Node`
    :return: the actual Edge is found and removed or not
    :rtype: bool
    """
    for edge in self.edge_sg_nexthops:
      if edge.src.id == src.id and edge.dst.id == dst.id:
        self.edge_sg_nexthops.remove(edge)
        return True

  def add_req (self, src, dst, **kwargs):
    """
    Create and store a Requirement Edge with the given src and dst nodes.

    :param src: source node
    :type src: :any:`Node`
    :param dst:  destination node
    :type dst: :any:`Node`
    :return: the created edge
    :rtype: :any:`EdgeReq`
    """
    req = EdgeReq(src=src, dst=dst, **kwargs)
    for edge in self.edge_reqs:
      if edge.src.id == src.id and edge.dst.id == dst.id:
        raise RuntimeError(
          "EdgeReq with src(%s) and dst(%s) endpoints already exist in the "
          "container!" % (src.id, dst.id))
    self.edge_sg_nexthops.append(req)
    return req

  def del_req (self, src, dst):
    """
    Remove Requirement Edge with given src and dst nodes.

    :param src: source node
    :type src: :any:`Node`
    :param dst:  destination node
    :type dst: :any:`Node`
    :return: the actual Edge is found and removed or not
    :rtype: bool
    """
    for edge in self.edge_reqs:
      if edge.src.id == src.id and edge.dst.id == dst.id:
        self.edge_sg_nexthops.remove(edge)
        return True

  def persist (self):
    nffg = {"parameters": {"id": self.id, "version": self.version}}
    if self.name is not None:
      nffg["parameters"]["name"] = str(self.name)
    if self.node_nfs:
      nffg["node_nfs"] = [nf.persist() for nf in self.node_nfs]
    if self.node_saps:
      nffg["node_saps"] = [sap.persist() for sap in self.node_saps]
    if self.node_infras:
      nffg["node_infras"] = [infra.persist() for infra in self.node_infras]
    if self.edge_links:
      nffg["edge_links"] = [link.persist() for link in self.edge_links]
    if self.edge_sg_nexthops:
      nffg["edge_sg_nexthops"] = [sg.persist() for sg in self.edge_sg_nexthops]
    if self.edge_reqs:
      nffg["edge_reqs"] = [req.persist() for req in self.edge_reqs]
    return nffg

  def load (self, raw_data):
    """
    Read the given JSON object structure and try to convert to an NF-FG
    representation as an :any:`NFFGModel`.

    :param raw_data: raw date in JSON
    :type raw_data: str
    :return: the constructed NF-FG representation
    :rtype: :any:`NFFGModel`
    """
    # Converter function to avoid unicode
    def unicode_to_str (input):
      if isinstance(input, dict):
        return {unicode_to_str(key): unicode_to_str(value) for key, value in
                input.iteritems()}
      elif isinstance(input, list):
        return [unicode_to_str(element) for element in input]
      elif isinstance(input, unicode):
        return input.encode('utf-8')
      else:
        return input

    try:
      # Load from plain text
      data = json.loads(raw_data, object_hook=unicode_to_str)
      # Create container
      container = NFFGModel()
      # Fill container fields
      container.id = data['parameters']['id']  # mandatory
      container.name = data['parameters'].get('name')  # can be None
      container.version = data['parameters']['version']  # mandatory
      # Fill Container lists
      for n in data.get('node_nfs', ()):
        container.node_nfs.append(NodeNF.parse(data=n))
      for n in data.get('node_saps', ()):
        container.node_saps.append(NodeSAP.parse(data=n))
      for n in data.get('node_infras', ()):
        container.node_infras.append(NodeInfra.parse(data=n))
      for e in data.get('edge_links', ()):
        container.edge_links.append(EdgeLink.parse(data=e, container=container))
      for e in data.get('edge_sg_nexthops', ()):
        container.edge_sg_nexthops.append(
          EdgeSGLink().parse(data=e, container=container))
      for e in data.get('edge_reqs', ()):
        container.edge_reqs.append(EdgeReq.parse(data=e, container=container))
    except KeyError as e:
      raise RuntimeError("Not a valid NFFGModel format!", e)
    return container

  def dump (self):
    """
    Dump the container in plain text based on JSON structure.

    :return: NF-FG representation as plain text
    :rtype: str
    """
    return json.dumps(self.persist(), indent=2, sort_keys=True)


def test_parse_load ():
  # NF
  nf = NodeNF()
  nf.id = "nf1"
  nf.name = "NetworkFunction1"
  nf.functional_type = "functype1"
  nf.deployment_type = "virtual"
  nf.resources.cpu = "10"
  nf.resources.mem = "1"
  nf.resources.storage = "10"
  nf.resources.bandwidth = "2"
  nf.resources.delay = "2"
  # nf.add_port("port_nf1", "port1", "virtual", "vlan:1025")
  p1 = nf.add_port(id="port_nf1", properties=("port1", "virtual", "vlan:1025"))
  # SAP
  sap = NodeSAP()
  sap.id = "sap1"
  sap.name = "sap1"
  p2 = sap.add_port(id="port_sap")
  # Infra
  infra = NodeInfra()
  infra.id = "infra1"
  infra.name = "BisBis1"
  infra.domain = "virtual"
  infra.resources.cpu = "20"
  infra.resources.mem = "2"
  infra.resources.storage = "20"
  infra.resources.bandwidth = "4"
  # infra.resources.delay = "4"
  p3 = port_infra = infra.add_port(id="port_infra")
  port_infra.add_flowrule("match123", "action456")
  # Edge link
  edge_link = EdgeLink(p2, p3, id="link3")
  edge_link.bandwidth = "100"
  edge_link.delay = "5"
  # Edge SG next hop
  edge_sg = EdgeSGLink(p1, p2, id="link1")
  edge_sg.flowclass = "flowclass1"
  # Edge requirement
  edge_req = EdgeReq(p2, p3)
  edge_req.id = "link2"
  edge_req.bandwidth = "100"
  edge_req.delay = "5"
  # Generate
  nffg = NFFGModel()
  nffg.name = "NFFG1"
  nffg.node_infras.append(infra)
  nffg.node_nfs.append(nf)
  nffg.node_saps.append(sap)
  nffg.edge_links.append(edge_link)
  nffg.edge_sg_nexthops.append(edge_sg)
  nffg.edge_reqs.append(edge_req)
  data = nffg.dump()
  print "\nGenerated NFFG:"
  print data
  nffg2 = NFFGModel.parse(data)
  print "\nParsed NFFG:"
  print nffg2.dump()


def test_networkx_mod ():
  nf = NodeNF()
  print nf["id"]
  nf["id"] = "nf1"
  print nf["id"]


if __name__ == "__main__":
  test_parse_load()
  # test_networkx_mod()
