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
Abstract class and implementation for basic operations with a single
NF-FG, such as building, parsing, processing NF-FG, helper functions,
etc.
"""
import getopt
from pprint import pprint
import sys
# from escape.util.misc import enum

from nffglib import *


def enum (*sequential, **named):
  """
  Helper function to define enumeration. E.g.:

  .. code-block:: python

    >>> Numbers = enum(ONE=1, TWO=2, THREE='three')
    >>> Numbers = enum('ZERO', 'ONE', 'TWO')
    >>> Numbers.ONE
    1
    >>> Numbers.reversed[2]
    'TWO'

  :param sequential: support automatic enumeration
  :type sequential: list
  :param named: support definition with unique keys
  :type named: dict
  :return: Enum object
  :rtype: dict
  """
  enums = dict(zip(sequential, range(len(sequential))), **named)
  enums['reversed'] = dict((value, key) for key, value in enums.iteritems())
  return type('enum', (), enums)


class AbstractNFFG(object):
  """
  Abstract class for managing single NF-FG data structure.

  The NF-FG data model is described in YANG. This class provides the
  interfaces with the high level data manipulation functions.
  """

  def __init__ (self, id=None, version='1.0'):
    """
    Init
    """
    super(AbstractNFFG, self).__init__()
    self._id = id
    self._version = version

  # NFFG specific functions

  def add_nf (self, node_nf):
    """
    Add a single NF node to the NF-FG.
    """
    raise NotImplementedError("Not implemented yet!")

  def add_sap (self, node_sap):
    """
    Add a single SAP node to the NF-FG.
    """
    raise NotImplementedError("Not implemented yet!")

  def add_infra (self, node_infra):
    """
    Add a single infrastructure node to the NF-FG.
    """
    raise NotImplementedError("Not implemented yet!")

  def add_edge (self, src, dst, params=None):
    """
    Add an edge to the NF-FG.

    :param src: source (node, port) of the edge
    :type src: (Node, Port) inherited Node classes: NodeNF, NodeSAP, NodeInfra
    :param dst: destination (node, port) of the edge
    :type dst: (Node, Port) inherited Node classes: NodeNF, NodeSAP, NodeInfra
    :param params: attribute of the edge depending on the type
    :type params: ResOfEdge or Flowrule
    :return: None
    """
    raise NotImplementedError("Not implemented yet!")

  def add_link (self, edge_link):
    """
    Add a static or dynamic infrastructure link to the NF-FG.
    """
    raise NotImplementedError("Not implemented yet!")

  def add_sglink (self, edge_sglink):
    """
    Add an SG link to the NF-FG.
    """
    raise NotImplementedError("Not implemented yet!")

  def add_req (self, edge_req):
    """
    Add a requirement link to the NF-FG.
    """
    raise NotImplementedError("Not implemented yet!")

  def del_node (self, id):
    """
    Delete a single node from the NF-FG.
    """
    raise NotImplementedError("Not implemented yet!")

  # General functions for create/parse/dump/convert NFFG

  @staticmethod
  def parse (data):
    """
    General function for parsing data as a new :any::`NFFG` object and return
    with its reference.

    :param data: raw data
    :type data: str
    :return: parsed NFFG as an XML object
    :rtype: Virtualizer
    """
    raise NotImplementedError("Not implemented yet!")

  def dump (self):
    """
    General function for dumping :any::`NFFG` according to its format to
    plain text.

    :return: plain text representation
    :rtype: str
    """
    raise NotImplementedError("Not implemented yet!")


class NFFG(AbstractNFFG):
  """
  NF-FG implementation based on ETH nffglib library.

  .. warning::
    Not fully implemented yet!
  """

  def __init__ (self, id=None):
    """
    Init
    """
    super(NFFG, self).__init__(id)

  @property
  def id (self):
    return self._id

  @id.setter
  def id (self, id):
    self._id = id

  # NFFG specific functions

  def add_nf (self, node_nf):
    """
    Add a single NF node to the NF-FG.
    """
    pass

  def add_sap (self, node_sap):
    """
    Add a single SAP node to the NF-FG.
    """
    pass

  def add_infra (self, node_infra):
    """
    Add a single infrastructure node to the NF-FG.
    """
    pass

  def add_link (self, edge_link):
    """
    Add a static or dynamic infrastructure link to the NF-FG.
    """
    pass

  def add_sglink (self, edge_sglink):
    """
    Add an SG link to the NF-FG.
    """
    pass

  def add_req (self, edge_req):
    """
    Add a requirement link to the NF-FG.
    """
    pass

  def del_node (self, id):
    """
    Delete a single node from the NF-FG.
    """
    pass

  def add_edge (self, src, dst, params=None):
    pass

  # General functions for create/parse/dump/convert NFFG

  @staticmethod
  def parse (data, format="JSON"):
    """
    """
    if format.upper() == "JSON":
      return NFFG().init_from_json(data)

  def dump (self):
    """
    """
    pass

  def init_from_json (self, json_data):
    """
    Parse, create and initialize the NFFG object from JSON data.

    :param json_data: NF-FG represented in JSON format
    :type json_data: str
    :return: None
    """
    # TODO - improve
    self.data = json_data
    return self

  def init_from_xml (self, xml_data):
    """
    Parse, create and initialize the NFFG object from XML data.

    :param xml_data: NF-FG represented in XML format
    :type xml_data: str
    :return: None
    """
    raise NotImplementedError("Not implemented yet!")

  def load_from_file (self, filename):
    """
    Load and parse NF-FG definition from file.

    :param filename:
    :return:
    """
    raise NotImplementedError("Not implemented yet!")

  def dump_to_json (self):
    """
    Return a JSON string represent this instance.

    :return: JSON formatted string
    :rtype: str
    """
    raise NotImplementedError("Not implemented yet!")

  # Convenient functions

  def __copy__ (self):
    """
    Magic class for creating a shallow copy of actual class using the
    copy.copy() function of Python standard library. This means that,
    while the instance itself is a new instance, all of its data is referenced.

    :return: shallow copy of this instance
    :rtype: :class:`NFFG`
    """
    raise NotImplementedError("Not implemented yet!")

  def __deepcopy__ (self, memo={}):
    """
    Magic class for creating a deep copy of actual class using the
    copy.deepcopy() function of Python standard library. The object and its
    data are both copied.

    :param memo: is a cache of previously copied objects
    :type memo: dict
    :return: shallow copy of this instance
    :rtype: :class:`NFFG`
    """
    raise NotImplementedError("Not implemented yet!")


class NFFGtoXMLBuilder(AbstractNFFG):
  """
  Builder class for construct an NFFG in XML format rely on ETH's nffglib.py.

  .. warning::

    Only tailored to the current nffglib.py (2015.06.26) and OpenStack domain.
    Should not use for general purposes, major part could be unimplemented!
  """
  # Do not modified
  __UUID_NUM = 0
  # Default infrastructure node type
  DEFAULT_INFRA_TYPE = "BisBis"
  DEFAULT_NODE_TYPE = "0"
  # Port types
  PORT_TYPE = enum(ABSTRACT="port-abstract", SAP="port-sap")

  def __init__ (self):
    """
    Init. Create an empty virtualizer container and the necessary sub-objects.

    :return: None
    """
    super(NFFGtoXMLBuilder, self).__init__(None, "1.0")
    # Init main container: virtualizer
    self.__virtualizer = Virtualizer()
    self.__virtualizer.g_idName = IdNameGroup(self.__virtualizer)
    # Add <id> tag
    NFFGtoXMLBuilder.__UUID_NUM += 1
    self.__virtualizer.g_idName.l_id = "UUID-ESCAPE-BME-%03d" % \
                                       NFFGtoXMLBuilder.__UUID_NUM
    # Add <name> tag
    self.__virtualizer.g_idName.l_name = "ESCAPE-BME orchestrator version v2.0"
    # Add <nodes> tag
    self.__virtualizer.c_nodes = Nodes(self.__virtualizer)
    # Add <links> tag
    # self.__virtualizer.g_links = LinksGroup(self.__virtualizer)
    # self.__virtualizer.g_links.c_links = Links(self.__virtualizer.g_links)

  ##############################################################################
  # Builder design pattern related functions
  ##############################################################################

  def dump (self):
    """
    Return the constructed NFFG as a string in XML format.

    :return: NFFG in XML format
    :rtype: str
    """
    return self.__virtualizer.xml()

  def __str__ (self):
    """
    Dump the constructed NFFG as a pretty string.

    :return: NFFG in XML format
    :rtype: str
    """
    return self.dump()

  def build (self):
    """
    Return the constructed XML object a.k.a. the Virtualizer.

    :return: NFFG
    :rtype: Virtualizer
    """
    return self.__virtualizer

  @staticmethod
  def parse (data):
    """
    Parse the given XML-formatted string and return the constructed Virtualizer.

    :param data: raw text formatted in XML
    :type data: str
    :return: parsed XML object-structure
    :rtype: Virtualizer
    """
    return Virtualizer().parse(text=data)

  ##############################################################################
  # Simplifier function to access XML tags easily
  ##############################################################################

  @property
  def id (self):
    """
    Return the id of the NFFG.

    :return: id
    :rtype: str
    """
    return self.__virtualizer.g_idName.l_id

  @id.setter
  def id (self, id):
    """
    Set the id of NFFG.

    :param id: new id
    :type id: int or str
    :return: None
    """
    self.__virtualizer.g_idName.l_id = str(id)

  @property
  def name (self):
    """
    Return the name of NFFG.

    :return: name
    :rtype: str
    """
    return self.__virtualizer.g_idName.l_name

  @name.setter
  def name (self, name):
    """
    Set the name of NFFG.

    :param name: new name
    :type name: str
    :return: None
    """
    self.__virtualizer.g_idName.l_name = str(name)

  @property
  def nodes (self):
    """
    Return the list of nodes.

    :return: nodes
    :rtype: list(InfraNodeGroup)
    """
    return self.__virtualizer.c_nodes.list_node

  @property
  def links (self):
    """
    Return the list of links. If links is not exist, create the empty container
    on the fly.

    :return: links
    :rtype: list(Links)
    """
    if self.__virtualizer.g_links is None:
      self.__virtualizer.g_links = LinksGroup(self.__virtualizer)
      self.__virtualizer.g_links.c_links = Links(self.__virtualizer.g_links)
    return self.__virtualizer.g_links.c_links.list_link

  ##############################################################################
  # Extended function for bridging over the differences between NFFG repr
  ##############################################################################

  def add_node (self, parent, id=None, name=None, type=None):
    """
    Add an empty node(NodeGroup) to its parent. If the parameters are not
    given, they are generated from default names and the actual container's
    size.

    :param parent: container of the new node
    :type parent: InfraNodeGroup or NodeGroup or NFInstances or SupportedNFs
    :param id: ID of node
    :type id: str or int
    :param name: name (optional)
    :type name: str
    :param type: node type (default: 0)
    :type type: str
    :return: node object
    :rtype: NodeGroup
    """
    # Define mandatory attributes
    type = self.DEFAULT_NODE_TYPE if type is None else str(type)
    id = str(len(self.nodes)) if id is None else str(id)
    name = str("node" + str(id)) if name is None else str(name)
    # Add id, name, type
    node = NodeGroup(parent)
    node.g_idNameType = IdNameTypeGroup(node)
    node.g_idNameType.g_idName = IdNameGroup(node.g_idNameType)
    node.g_idNameType.g_idName.l_id = id
    node.g_idNameType.g_idName.l_name = name
    node.g_idNameType.l_type = type
    return node

  def add_infrastructure_node (self, id=None, name=None, type=None):
    """
    Add an infrastructure node to NFFG (as a BiS-BiS), which is a special
    node directly under the ``Virtualizer`` main container object.

    :param id: ID of infrastructure node
    :type id: str or int
    :param name: name (optional)
    :type name: str
    :param type: node type (default: BisBis)
    :type type: str
    :return: infrastructure node object
    :rtype: InfraNodeGroup
    """
    # Define mandatory attributes
    type = self.DEFAULT_INFRA_TYPE if type is None else str(type)
    id = "UUID-%02d" % len(self.nodes) if id is None else str(id)
    name = str(type + str(id)) if name is None else str(name)
    # Create Infrastructure wrapper
    infra = InfraNodeGroup(self.__virtualizer)
    # Add id, name, type as a NodeGroup
    infra.g_node = self.add_node(infra, id=id, name=name,
                                 type=self.DEFAULT_INFRA_TYPE)
    # Add necessary flow table group for InfraNodeGroup
    infra.g_flowtable = FlowTableGroup(infra)
    # Add infra to nodes
    self.nodes.append(infra)
    return infra

  def add_node_port (self, parent, type=PORT_TYPE.ABSTRACT, id=None, name=None,
       param=None):
    """
    Add a port to a Node. The parent node could be the nodes which can has
    ports i.e. a special infrastructure node, initiated and supported NF
    objects. If the type is a SAP type, the param attribute is read as the
    sap-type. If the param attribute starts with "vxlan:" then the sap-type
    will be set to "vxlan" and the vxlan tag will be set to the number after
    the colon.

    :param parent: parent node
    :type parent: InfraNodeGroup or NodeGroup
    :param type: type of the port as ``PORT_TYPE``
    :type type: one of ``PORT_TYPE`` enum, currently: port-{abstract,sap}
    :param id: port ID (optional)
    :type id: str
    :param name: port name (optional)
    :type name: str (optional)
    :param param: additional parameters: abstract: capability; sap: sap-type
    :type param: str
    :return: port object
    :rtype: PortGroup
    """
    # Set the correct NodeGroup as the parent in case of Infrastructure None
    if isinstance(parent, InfraNodeGroup):
      parent = parent.g_node
    # Add ports container if it's not exist
    if parent.c_ports is None:
      parent.c_ports = Ports(parent)
    # Define mandatory attributes
    id = str(len(parent.c_ports.list_port)) if id is None else str(id)
    name = "port" + str(id) if name is None else str(name)
    # Create port
    port = PortGroup(parent.c_ports)
    # Add id, name, type
    port.g_idName = IdNameGroup(port)
    port.g_idName.l_id = id
    port.g_idName.l_name = name
    port.g_portType = PortTypeGroup(port)
    if type == self.PORT_TYPE.ABSTRACT:
      # Add capabilities sub-object as the additional param
      _type = PortAbstractCase(port.g_portType)
      _type.l_portType = type
      _type.l_capability = str(param)
    elif type == self.PORT_TYPE.SAP:
      # Add sap-type and vx-lan sub-objects as the additional param
      _type = PortSapVxlanCase(port.g_portType)
      _type.l_portType = type
      if param.startswith("vxlan:"):
        _type.l_sapType = "vx-lan"
        _type.g_portSapVxlan = PortSapVxlanGroup(_type)
        _type.g_portSapVxlan.l_vxlan = param.lstrip("vxlan:")
      else:
        _type.l_sapType = str(param)
        # if vxlan is not None:
        #   _type.g_portSapVxlan = PortSapVxlanGroup(_type)
        #   _type.g_portSapVxlan.l_vxlan = str(vxlan)
        #   # TODO handle vx-lan choice in sap-type
    else:
      raise RuntimeError("Not supported Port type: %s" % type)
    port.g_portType = _type
    # Add port to ports
    parent.c_ports.list_port.append(port)
    return port

  def add_node_resource (self, parent, cpu=None, mem=None, storage=None):
    """
    Add software resources to a Node or an infrastructure Node.

    :param parent: parent node
    :type parent: InfraNodeGroup or NodeGroup
    :param cpu: In virtual CPU (vCPU) units
    :type cpu: str
    :param mem: Memory with units, e.g., 1Gbyte
    :type mem: str
    :param storage: Storage with units, e.g., 10Gbyte
    :type storage: str
    :return: resource object
    :rtype: NodeResources
    """
    # If InfraNodeGroup set parent reference correctly
    if isinstance(parent, InfraNodeGroup):
      parent = parent.g_node
    # Create resources
    if parent.c_resources is None:
      parent.c_resources = NodeResources(parent)
      parent.c_resources.g_softwareResource = SoftwareResourceGroup(
        parent.c_resources)
    # Add cpu, mem, storage
    if cpu:
      parent.c_resources.g_softwareResource.l_cpu = str(cpu)
    if mem:
      parent.c_resources.g_softwareResource.l_mem = str(mem)
    if storage:
      parent.c_resources.g_softwareResource.l_storage = str(storage)
    return parent.c_resources

  def add_link_resource (self, parent, delay=None, bandwidth=None):
    """
    Add link resources to a connection.

    :param parent: container of the connection
    :type parent: Flowentry or Link
    :param delay: delay value with unit; e.g. 5ms (optional)
    :type delay: str
    :param bandwidth: bandwidth value with unit; e.g. 10Mbps (optional)
    :type bandwidth: str
    :return: connection resource
    :rtype: LinkResource
    """
    if delay is not None or bandwidth is not None:
      parent.c_resources = LinkResource(parent)
      parent.c_resources.g_linkResource = LinkResourceGroup(parent.c_resources)
      parent.c_resources.g_linkResource.l_delay = delay
      parent.c_resources.g_linkResource.l_bandwidth = bandwidth
    return parent.c_resources

  def add_nf_instance (self, parent, id=None, name=None, type=None):
    """
    Add an NF instance to an Infrastructure Node.

    :param parent: container of the new node
    :type parent: InfraNodeGroup
    :param id: ID of node
    :type id: str or int
    :param name: name (optional)
    :type name: str
    :param type: node type (default: 0)
    :type type: str
    :return: NF instance object
    :rtype: NodeGroup
    """
    # Create NF container
    if parent.c_NFInstances is None:
      parent.c_NFInstances = NFInstances(parent)
    # Create NF instance
    nf_instance = self.add_node(parent.c_NFInstances, id, name, type)
    # Add NF instance to container
    parent.c_NFInstances.list_node.append(nf_instance)
    return nf_instance

  def add_supported_nf (self, parent, id=None, name=None, type=None):
    """
    Add a supported NF to an Infrastructure Node.

    :param parent: container of the new node
    :type parent: InfraNodeGroup
    :param id: ID of node
    :type id: str or int
    :param name: name (optional)
    :type name: str
    :param type: node type (default: 0)
    :type type: str
    :return: supported NF object
    :rtype: NodeGroup
    """
    # Create capabilities container
    if parent.c_capabilities is None:
      parent.c_capabilities = Capabilities(parent)
      parent.c_capabilities.g_capabilities = CapabilitesGroup(
        parent.c_capabilities)
      parent.c_capabilities.g_capabilities.c_supportedNFs = SupportedNFs(
        parent.c_capabilities.g_capabilities)
    # Create supported NF
    supported_nf = self.add_node(
      parent.c_capabilities.g_capabilities.c_supportedNFs, id, name, type)
    # Add supported NF to container
    parent.c_capabilities.g_capabilities.c_supportedNFs.list_node.append(
      supported_nf)
    return supported_nf

  def add_flow_entry (self, parent, in_port, out_port, match=None, action=None,
       delay=None, bandwidth=None):
    """
    Add a flowentry to an Infrastructure Node.

    :param parent: container of the flowtable
    :type parent: InfraNodeGroup
    :param in_port: related in port object
    :type in_port: PortGroup
    :param match: matching rule
    :type match: str
    :param in_port: related out port object
    :type in_port: PortGroup
    :param action: forwarding actions
    :type action: list or tuple or str
    :param delay: delay value with unit; e.g. 5ms (optional)
    :type delay: str
    :param bandwidth: bandwidth value with unit; e.g. 10Mbps (optional)
    :type bandwidth: str
    :return: flowentry
    :rtype: FlowEntry
    """
    # Create flowtables container
    if parent.g_flowtable.c_flowtable is None:
      parent.g_flowtable.c_flowtable = FlowTable(parent.g_flowtable)
    # Create flowentry
    flowentry = FlowEntry(parent.g_flowtable.c_flowtable)
    # Add port
    # port.parent.parent,parent -> PortGroup.Ports.NodeGroup.InfraNodeGroup
    if isinstance(in_port.parent.parent.parent, InfraNodeGroup):
      _in_port = "../../ports/port[id=%s]" % in_port.g_idName.l_id
    # port.parent.parent,parent -> PortGroup.Ports.NodeGroup.NFInstances
    elif isinstance(in_port.parent.parent.parent, NFInstances):
      _in_port = "../../NF_instances/node[id=%s]ports/port[id=%s]" % (
        in_port.parent.parent.g_idNameType.g_idName.l_id, in_port.g_idName.l_id)
    else:
      raise RuntimeError("Not supported in_port ancestor!")
    flowentry.l_port = _in_port
    # Add match
    if match is not None:
      flowentry.l_match = str(match)
    # Add action
    # port.parent.parent,parent -> PortGroup.Ports.NodeGroup.InfraNodeGroup
    if isinstance(out_port.parent.parent.parent, InfraNodeGroup):
      _out_port = "output:../../ports/port[id=%s]" % out_port.g_idName.l_id
    # port.parent.parent,parent -> PortGroup.Ports.NodeGroup.NFInstances
    elif isinstance(out_port.parent.parent.parent, NFInstances):
      _out_port = "output:../../NF_instances/node[id=%s]ports/port[id=%s]" % (
        out_port.parent.parent.g_idNameType.g_idName.l_id,
        out_port.g_idName.l_id)
    else:
      raise RuntimeError("Not supported out_port ancestor!")
    if action is not None:
      tmp_sequence = list()
      tmp_sequence.append(_out_port)
      if isinstance(action, str):
        tmp_sequence.append(action)
      else:
        tmp_sequence.extend(action)
      _out_port = ";".join(tmp_sequence)
    flowentry.l_action = _out_port
    # Add resource
    self.add_link_resource(flowentry, delay=delay, bandwidth=bandwidth)
    # Add flowentry to flowtable
    parent.g_flowtable.c_flowtable.list_flowentry.append(flowentry)
    return flowentry

  def __add_connection (self, parent, src, dst, id=None, name=None, delay=None,
       bandwidth=None):
    """
    Add a connection a.k.a a <link> to the Virtualizer or to a Node.

    :param parent: parent node
    :type parent: Virtualizer or NodeGroup
    :param src: relative path to the source port
    :type src: str
    :param dst: relative path to the destination port
    :type dst: str
    :param id: link ID (optional)
    :type id: str or int
    :param name: link name (optional)
    :type name: str
    :param delay: delay value with unit; e.g. 5ms (optional)
    :type delay: str
    :param bandwidth: bandwidth value with unit; e.g. 10Mbps (optional)
    :type bandwidth: str
    :return: link object
    :rtype: LinksGroup
    """
    # Add links container if it's not exist
    if parent.g_links is None:
      parent.g_links = LinksGroup(parent)
      parent.g_links.c_links = Links(parent.g_links)
    # Define mandatory attributes
    id = str(len(parent.g_links.c_links.list_link)) if id is None else str(id)
    name = str("link" + str(id)) if name is None else str(name)
    # Create link
    link = Link(parent.g_links.c_links)
    # Add id, name
    link.g_idName = IdNameGroup(link)
    link.g_idName.l_id = id
    link.g_idName.l_name = name
    # Add src, dst
    link.l_src = src
    link.l_dst = dst
    # Add resource
    self.add_link_resource(link, delay=delay, bandwidth=bandwidth)
    # Add link to links
    parent.g_links.c_links.list_link.append(link)
    return link

  def add_inter_infra_link (self, src, dst, **kwargs):
    """
    Add link between Infrastructure nodes a.k.a define link in Virtualizer.

    :param src: source port
    :type src: PortGroup
    :param dst: destination port
    :type dst: PortGroup
    :return: link object
    :rtype: LinksGroup
    """
    if not isinstance(src, PortGroup) or not isinstance(dst, PortGroup):
      raise RuntimeError("scr and dst must be a port object (PortGroup)!")
    # Construct source and destination path
    # src.parent.parent -> PortGroup.Ports.NodeGroup
    src = "../../nodes/node[id=%s]/ports/port[id=%s]" % (
      src.parent.parent.g_idNameType.g_idName.l_id, src.g_idName.l_id)
    dst = "../../nodes/node[id=%s]/ports/port[id=%s]" % (
      dst.parent.parent.g_idNameType.g_idName.l_id, dst.g_idName.l_id)
    return self.__add_connection(self.__virtualizer, src, dst, **kwargs)

  ##############################################################################
  # General functions to add NFFG elements easily
  ##############################################################################

  def add_infra (self, id=None, name=None, type=None):
    """
    Add an Infrastructure Node.
    """
    return self.add_infrastructure_node(id, name, type)

  def add_nf (self, node_nf):
    """
    Add a Network Function Node.
    """
    pass

  def add_edge (self, src, dst, params=None):
    """
    Add an edge link to the NFFG: a link between infrastructure node ports.

    :param src:
    :param dst:
    :param params:
    :return:
    """
    pass

  def del_node (self, id):
    pass

  def add_req (self, edge_req):
    pass

  def add_sap (self, node_sap):
    pass

  def add_link (self, edge_link):
    pass

  def add_sglink (self, edge_sglink):
    pass


def main (argv=None):
  if argv is None:
    argv = sys.argv
  # parse command line options
  try:
    opts, args = getopt.getopt(sys.argv[1:], "hi:v", ["help", "input="])
  except getopt.error, msg:
    print msg
    print "for help use --help"
    sys.exit(2)

  for o, a in opts:
    if o in ('-i', '--input'):
      filename = a

  res = NFFG.load_from_json(filename)
  pprint(res)


if __name__ == "__main__":
  # main()
  # builder = NFFGtoXMLBuilder()
  # infra = builder.add_infra()
  # port = builder.add_node_port(infra, NFFGtoXMLBuilder.PORT_TYPE.ABSTRACT)
  # res = builder.add_node_resource(infra, "10 VCPU", "32 GB", "5 TB")
  # link = builder.add_inter_infra_link(port, port, delay="5ms",
  #                                     bandwidth="10Gbps")
  # nf_inst = builder.add_nf_instance(infra)
  # nf_port = builder.add_node_port(nf_inst, NFFGtoXMLBuilder.PORT_TYPE.ABSTRACT)
  # sup_nf = builder.add_supported_nf(infra)
  # res_sup = builder.add_node_resource(sup_nf, 10, 10, 10)
  # builder.add_node_port(sup_nf, NFFGtoXMLBuilder.PORT_TYPE.ABSTRACT)
  # builder.add_flow_entry(infra, port, nf_port,
  #                        action="mod_dl_src=12:34:56:78:90:12", delay="5ms",
  #                        bandwidth="10Gbps")

  # Generate same output as Agent_http.py
  builder = NFFGtoXMLBuilder()
  builder.id = "UUID-ETH-001"
  builder.name = "ETH OpenStack-OpenDaylight domain"
  infra = builder.add_infra(
    name="single Bis-Bis node representing the whole domain")
  iport0 = builder.add_node_port(infra, name="OVS-north external port")
  iport1 = builder.add_node_port(infra, name="OVS-south external port")
  builder.add_node_resource(infra, cpu="10 VCPU", mem="32 GB", storage="5 TB")
  nf1 = builder.add_nf_instance(infra, id="NF1", name="example NF")
  nf1port0 = builder.add_node_port(nf1, name="Example NF input port")
  nf1port1 = builder.add_node_port(nf1, name="Example NF output port")
  sup_nf = builder.add_supported_nf(infra, id="nf_a",
                                    name="tcp header compressor")
  builder.add_node_port(sup_nf, name="in", param="...")
  builder.add_node_port(sup_nf, name="out", param="...")
  builder.add_flow_entry(infra, in_port=iport0, out_port=nf1port0)
  builder.add_flow_entry(infra, in_port=nf1port1, out_port=iport1,
                         action="mod_dl_src=12:34:56:78:90:12")
  print builder
