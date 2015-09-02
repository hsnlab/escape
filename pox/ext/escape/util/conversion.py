# Copyright 2015 Janos Czentye, Raphael Vicente Rosa
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
Contains helper classes for conversion between different NF-FG representations.
"""
import xml.etree.ElementTree as ET
import sys

import nffglib as virt
import virtualizer3 as virt3
from virtualizer3 import Flowentry

try:
  # Import for ESCAPEv2
  from escape.util.nffg import AbstractNFFG, NFFG
except ImportError:
  import os, inspect

  sys.path.insert(0, os.path.join(os.path.abspath(os.path.realpath(
    os.path.abspath(
      os.path.split(inspect.getfile(inspect.currentframe()))[0])) + "/.."),
                                  "pox/ext/escape/util/"))
  # Import for standalone running
  from nffg import AbstractNFFG, NFFG


class XMLBasedNFFGBuilder(AbstractNFFG):
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
  PORT_ABSTRACT = "port-abstract"
  PORT_SAP = "port-sap"

  def __init__ (self):
    """
    Init. Create an empty virtualizer container and the necessary sub-objects.

    :return: None
    """
    super(XMLBasedNFFGBuilder, self).__init__()
    # Init main container: virtualizer
    self.__virtualizer = virt.Virtualizer()
    self.__virtualizer.g_idName = virt.IdNameGroup(self.__virtualizer)
    # Add <id> tag
    XMLBasedNFFGBuilder.__UUID_NUM += 1
    self.__virtualizer.g_idName.l_id = "UUID-ESCAPE-BME-%03d" % \
                                       XMLBasedNFFGBuilder.__UUID_NUM
    # Add <name> tag
    self.__virtualizer.g_idName.l_name = "ESCAPE-BME orchestrator version v2.0"
    # Add <nodes> tag
    self.__virtualizer.c_nodes = virt.Nodes(self.__virtualizer)
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

  @classmethod
  def parse (cls, data):
    """
    Parse the given XML-formatted string and return the constructed Virtualizer.

    :param data: raw text formatted in XML
    :type data: str
    :return: parsed XML object-structure
    :rtype: Virtualizer
    """
    return virt.Virtualizer().parse(text=data)

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
      self.__virtualizer.g_links = virt.LinksGroup(self.__virtualizer)
      self.__virtualizer.g_links.c_links = virt.Links(
        self.__virtualizer.g_links)
    return self.__virtualizer.g_links.c_links.list_link

  ##############################################################################
  # Extended function for bridging over the differences between NFFG repr
  ##############################################################################

  def add_edge (self, src, dst, link):
    pass

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
    node = virt.NodeGroup(parent)
    node.g_idNameType = virt.IdNameTypeGroup(node)
    node.g_idNameType.g_idName = virt.IdNameGroup(node.g_idNameType)
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
    infra = virt.InfraNodeGroup(self.__virtualizer)
    # Add id, name, type as a NodeGroup
    infra.g_node = self.add_node(infra, id=id, name=name,
                                 type=self.DEFAULT_INFRA_TYPE)
    # Add necessary flow table group for InfraNodeGroup
    infra.g_flowtable = virt.FlowTableGroup(infra)
    # Add infra to nodes
    self.nodes.append(infra)
    return infra

  def add_node_port (self, parent, type=PORT_ABSTRACT, id=None, name=None,
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
    :param type: type of the port
    :type type: str
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
    if isinstance(parent, virt.InfraNodeGroup):
      parent = parent.g_node
    # Add ports container if it's not exist
    if parent.c_ports is None:
      parent.c_ports = virt.Ports(parent)
    # Define mandatory attributes
    id = str(len(parent.c_ports.list_port)) if id is None else str(id)
    name = "port" + str(id) if name is None else str(name)
    # Create port
    port = virt.PortGroup(parent.c_ports)
    # Add id, name, type
    port.g_idName = virt.IdNameGroup(port)
    port.g_idName.l_id = id
    port.g_idName.l_name = name
    port.g_portType = virt.PortTypeGroup(port)
    if type == self.PORT_ABSTRACT:
      # Add capabilities sub-object as the additional param
      _type = virt.PortAbstractCase(port.g_portType)
      _type.l_portType = type
      _type.l_capability = str(param)
    elif type == self.PORT_SAP:
      # Add sap-type and vx-lan sub-objects as the additional param
      _type = virt.PortSapVxlanCase(port.g_portType)
      _type.l_portType = type
      if param.startswith("vxlan:"):
        _type.l_sapType = "vx-lan"
        _type.g_portSapVxlan = virt.PortSapVxlanGroup(_type)
        _type.g_portSapVxlan.l_vxlan = param.lstrip("vxlan:")
      else:
        _type.l_sapType = str(param)
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
    if isinstance(parent, virt.InfraNodeGroup):
      parent = parent.g_node
    # Create resources
    if parent.c_resources is None:
      parent.c_resources = virt.NodeResources(parent)
      parent.c_resources.g_softwareResource = virt.SoftwareResourceGroup(
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
      parent.c_resources = virt.LinkResource(parent)
      parent.c_resources.g_linkResource = virt.LinkResourceGroup(
        parent.c_resources)
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
      parent.c_NFInstances = virt.NFInstances(parent)
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
      parent.c_capabilities = virt.Capabilities(parent)
      parent.c_capabilities.g_capabilities = virt.CapabilitesGroup(
        parent.c_capabilities)
      parent.c_capabilities.g_capabilities.c_supportedNFs = virt.SupportedNFs(
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
      parent.g_flowtable.c_flowtable = virt.FlowTable(parent.g_flowtable)
    # Create flowentry
    flowentry = virt.FlowEntry(parent.g_flowtable.c_flowtable)
    # Add port
    # port.parent.parent,parent -> PortGroup.Ports.NodeGroup.InfraNodeGroup
    if isinstance(in_port.parent.parent.parent, virt.InfraNodeGroup):
      _in_port = "../../ports/port[id=%s]" % in_port.g_idName.l_id
    # port.parent.parent,parent -> PortGroup.Ports.NodeGroup.NFInstances
    elif isinstance(in_port.parent.parent.parent, virt.NFInstances):
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
    if isinstance(out_port.parent.parent.parent, virt.InfraNodeGroup):
      _out_port = "output:../../ports/port[id=%s]" % out_port.g_idName.l_id
    # port.parent.parent,parent -> PortGroup.Ports.NodeGroup.NFInstances
    elif isinstance(out_port.parent.parent.parent, virt.NFInstances):
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
      parent.g_links = virt.LinksGroup(parent)
      parent.g_links.c_links = virt.Links(parent.g_links)
    # Define mandatory attributes
    id = str(len(parent.g_links.c_links.list_link)) if id is None else str(id)
    name = str("link" + str(id)) if name is None else str(name)
    # Create link
    link = virt.Link(parent.g_links.c_links)
    # Add id, name
    link.g_idName = virt.IdNameGroup(link)
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
    if not isinstance(src, virt.PortGroup) or not isinstance(dst,
                                                             virt.PortGroup):
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

  def add_nf (self):
    """
    Add a Network Function Node.
    """
    pass

  def add_sap (self):
    pass

  def add_infra (self, id=None, name=None, type=None):
    """
    Add an Infrastructure Node.
    """
    return self.add_infrastructure_node(id, name, type)

  def add_link (self, src, dst):
    pass

  def add_sglink (self, src, dst):
    pass

  def add_req (self, src, dst):
    pass

  def del_node (self, node):
    pass

  def del_edge (self, src, dst):
    pass


class Virtualizer3BasedNFFGBuilder(AbstractNFFG):
  """
  Builder class for construct an NFFG in XML format rely on ETH's nffglib.py.

  .. note::

    Only tailored to the current virtualizer3.py (2015.08.14) and OpenStack
    domain. Should not use for general purposes, major part could be
    unimplemented!
  """
  # Do not modified
  __UUID_NUM = 0
  # Default infrastructure node type
  DEFAULT_INFRA_TYPE = "BisBis"
  DEFAULT_NODE_TYPE = "0"
  # Port types
  PORT_ABSTRACT = "port-abstract"
  PORT_SAP = "port-sap"

  def __init__ (self):
    """
    Init. Create an empty virtualizer container and the necessary sub-objects.

    :return: None
    """
    super(Virtualizer3BasedNFFGBuilder, self).__init__()
    # Init main container: virtualizer
    # self.__virtualizer = Virtualizer()
    # self.__virtualizer.g_idName = IdNameGroup(self.__virtualizer)
    # Add <id> tag

    # self.__virtualizer.g_idName.l_id = "UUID-ESCAPE-BME-%03d" % \
    #                                   XMLBasedNFFGBuilder.__UUID_NUM
    # Add <name> tag
    # self.__virtualizer.g_idName.l_name = "ESCAPE-BME orchestrator version
    # v2.0"
    # Add <nodes> tag
    # self.__virtualizer.c_nodes = Nodes(self.__virtualizer)
    # Add <links> tag
    # self.__virtualizer.g_links = LinksGroup(self.__virtualizer)
    # self.__virtualizer.g_links.c_links = Links(self.__virtualizer.g_links)

    id_ = "UUID-ETH-%03d" % Virtualizer3BasedNFFGBuilder.__UUID_NUM

    self.__virtualizer = virt3.Virtualizer(id=id_,
                                           name="ETH OpenStack-OpenDaylight "
                                                "domain")
    Virtualizer3BasedNFFGBuilder.__UUID_NUM += 1

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
    return self.__virtualizer.__str__()

  def build (self):
    """
    Return the constructed XML object a.k.a. the Virtualizer.

    :return: NFFG
    :rtype: Virtualizer
    """
    return self.__virtualizer

  @classmethod
  def parse (cls, data):
    """
    Parse the given XML-formatted string and return the constructed Virtualizer.

    :param data: raw text formatted in XML
    :type data: str
    :return: parsed XML object-structure
    :rtype: Virtualizer
    """
    try:
      tree = ET.ElementTree(ET.fromstring(data))
      return virt3.Virtualizer().parse(root=tree.getroot())
    except ET.ParseError as e:
      raise RuntimeError('ParseError: %s' % e.message)

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
    return self.__virtualizer.id.data

  @id.setter
  def id (self, id):
    """
    Set the id of NFFG.

    :param id: new id
    :type id: int or str
    :return: None
    """
    self.__virtualizer.id.data = str(id)

  @property
  def name (self):
    """
    Return the name of NFFG.

    :return: name
    :rtype: str
    """
    return self.__virtualizer.name.data

  @name.setter
  def name (self, name):
    """
    Set the name of NFFG.

    :param name: new name
    :type name: str
    :return: None
    """
    self.__virtualizer.name.data = str(name)

  @property
  def nodes (self):
    """
    Return the list of nodes.

    :return: nodes
    :rtype: list(InfraNodeGroup) ### RETURN DICT {nodeID:InfraNodeGroup}
    """
    return self.__virtualizer.nodes.node

  @property
  def links (self):
    """
    Return the list of links. If links is not exist, create the empty container
    on the fly.

    :return: links
    :rtype: list(Links) ### RETURN DICT {(src,dst):Link}
    """
    return self.__virtualizer.links.link

  ##############################################################################
  # Extended function for bridging over the differences between NFFG repr
  ##############################################################################

  def add_edge (self, src, dst, link):
    pass

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
    id = str(
      len(self.__virtualizer.nodes.node.getKeys())) if id is None else str(id)
    name = str("node" + str(id)) if name is None else str(name)

    node = virt3.Node(parent=parent, id=id, name=name, type=type)
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
    id = "UUID-%02d" % len(
      self.__virtualizer.nodes.node.getKeys()) if id is None else str(id)
    name = str(type + str(id)) if name is None else str(name)

    infranode = virt3.Infra_node(id=id, name=name, type=type)
    self.__virtualizer.nodes.add(infranode)

    return infranode

  def add_node_port (self, parent, type=PORT_ABSTRACT, id=None, name=None,
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
    :param type: type of the port
    :type type: str
    :param id: port ID (optional)
    :type id: str
    :param name: port name (optional)
    :type name: str (optional)
    :param param: additional parameters: abstract: capability; sap: sap-type
    :type param: str
    :return: port object
    :rtype: PortGroup
    """
    # Define mandatory attributes
    id = str(len(parent.ports.port.getKeys())) if id is None else str(id)
    name = "port" + str(id) if name is None else str(name)

    # Create port
    port = virt3.Port(parent=parent, id=id, name=name, port_type=type,
                      capability=str(param), sap=str(param))

    parentPath = parent.getPath()
    if isinstance(parent, virt3.Infra_node):
      self.__virtualizer.nodes[parent.id.data].ports.add(port)
    elif "NF_instances" in parentPath:
      infraParent = parent.getParent().getParent()
      self.__virtualizer.nodes[infraParent.id.data].NF_instances.node[
        parent.id.data].ports.add(port)
    elif "supported_NFs" in parentPath:
      infraParent = parent.getParent().getParent().getParent()
      self.__virtualizer.nodes[infraParent.id.data].capabilities.supported_NFs[
        parent.id.data].ports.add(port)
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
    resources = virt3.NodeResources(parent=parent, cpu=str(cpu), mem=str(mem),
                                    storage=str(storage))
    self.__virtualizer.nodes[parent.id.data].resources = resources
    return resources

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
    resources = virt3.LinkResources(parent=parent, delay=delay,
                                    bandwidth=bandwidth)
    self.__virtualizer.links[parent.id.data].resources = resources
    return resources

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
    nf_instance = virt3.Node(parent=parent, id=id, name=name, type=type)
    self.__virtualizer.nodes[parent.id.data].NF_instances.node.add(nf_instance)
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
    supported_nf = virt3.Node(parent=parent, id=id, name=name, type=type)
    self.__virtualizer.nodes[
      parent.id.data].capabilities.supported_NFs.node.add(supported_nf)
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
    _in_port = in_port.getPath()
    _out_port = out_port.getPath()

    flowentry = virt3.Flowentry(parent=parent, port=_in_port, match=str(match),
                                action=action, out=_out_port)
    flowentry_resource = virt3.FlowentryResources(parent=flowentry, delay=delay,
                                                  bandwidth=bandwidth)
    flowentry.resources = flowentry_resource

    parentPath = parent.getPath()
    if isinstance(parent, virt3.Infra_node):
      self.__virtualizer.nodes[parent.id.data].flowtable.add(flowentry)
    elif "NF_instances" in parentPath:
      infraParent = parent.getParent().getParent()
      self.__virtualizer.nodes[infraParent.id.data].NF_instances.node[
        parent.id.data].flowtable.add(flowentry)
    elif "supported_NFs" in parentPath:
      infraParent = parent.getParent().getParent().getParent()
      self.__virtualizer.nodes[infraParent.id.data].capabilities.supported_NFs[
        parent.id.data].flowtable.add(flowentry)
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
    # Define mandatory attributes
    id = str(len(parent.links.link.getKeys())) if id is None else str(id)
    name = str("link" + str(id)) if name is None else str(name)
    # Create link
    link = virt3.Link(parent=parent, id=id, name=name, src=src, dst=dst)
    linkresources = virt3.LinkResources(parent=link, delay=delay,
                                        bandwidth=bandwidth)
    link.resources = linkresources
    self.__virtualizer.links.link.add(link)

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
    if not isinstance(src, virt3.Port) or not isinstance(dst, virt3.Port):
      raise RuntimeError("scr and dst must be a port object (Port)!")
    src_ = self.__virtualizer.getRelPath(src)
    dst_ = self.__virtualizer.getRelPath(dst)

    return self.__add_connection(self.__virtualizer, src_, dst_, **kwargs)

  ##############################################################################
  # General functions to add NFFG elements easily
  ##############################################################################

  def add_nf (self):
    """
    Add a Network Function Node.
    """
    pass

  def add_sap (self):
    pass

  def add_infra (self, id=None, name=None, type=None):
    """
    Add an Infrastructure Node.
    """
    return self.add_infrastructure_node(id, name, type)

  def add_link (self, src, dst):
    pass

  def add_sglink (self, src, dst):
    pass

  def add_req (self, src, dst):
    pass

  def del_node (self, node):
    pass

  def del_edge (self, src, dst):
    pass


def test_xml_based_builder ():
  # builder = NFFGtoXMLBuilder()
  # infra = builder.add_infra()
  # port = builder.add_node_port(infra, NFFGtoXMLBuilder.PORT_ABSTRACT)
  # res = builder.add_node_resource(infra, "10 VCPU", "32 GB", "5 TB")
  # link = builder.add_inter_infra_link(port, port, delay="5ms",
  #                                     bandwidth="10Gbps")
  # nf_inst = builder.add_nf_instance(infra)
  # nf_port = builder.add_node_port(nf_inst,
  # NFFGtoXMLBuilder.PORT_ABSTRACT)
  # sup_nf = builder.add_supported_nf(infra)
  # res_sup = builder.add_node_resource(sup_nf, 10, 10, 10)
  # builder.add_node_port(sup_nf, NFFGtoXMLBuilder.PORT_ABSTRACT)
  # builder.add_flow_entry(infra, port, nf_port,
  #                        action="mod_dl_src=12:34:56:78:90:12", delay="5ms",
  #                        bandwidth="10Gbps")

  # Generate same output as Agent_http.py
  builder = XMLBasedNFFGBuilder()
  builder.id = "UUID-ETH-001"
  builder.name = "ETH OpenStack-OpenDaylight domain"
  infra = builder.add_infra(
    name="single Bis-Bis node representing the whole domain")
  infra_port0 = builder.add_node_port(infra, name="OVS-north external port")
  infra_port1 = builder.add_node_port(infra, name="OVS-south external port")
  builder.add_node_resource(infra, cpu="10 VCPU", mem="32 GB", storage="5 TB")
  nf1 = builder.add_nf_instance(infra, id="NF1", name="example NF")
  nf1port0 = builder.add_node_port(nf1, name="Example NF input port")
  nf1port1 = builder.add_node_port(nf1, name="Example NF output port")
  sup_nf = builder.add_supported_nf(infra, id="nf_a",
                                    name="tcp header compressor")
  builder.add_node_port(sup_nf, name="in", param="...")
  builder.add_node_port(sup_nf, name="out", param="...")
  builder.add_flow_entry(infra, in_port=infra_port0, out_port=nf1port0)
  builder.add_flow_entry(infra, in_port=nf1port1, out_port=infra_port1,
                         action="mod_dl_src=12:34:56:78:90:12")
  print builder


def test_virtualizer3_based_builder ():
  # builder = NFFGtoXMLBuilder()
  # infra = builder.add_infra()
  # port = builder.add_node_port(infra, NFFGtoXMLBuilder.PORT_ABSTRACT)
  # res = builder.add_node_resource(infra, "10 VCPU", "32 GB", "5 TB")
  # link = builder.add_inter_infra_link(port, port, delay="5ms",
  #                                     bandwidth="10Gbps")
  # nf_inst = builder.add_nf_instance(infra)
  # nf_port = builder.add_node_port(nf_inst,
  # NFFGtoXMLBuilder.PORT_ABSTRACT)
  # sup_nf = builder.add_supported_nf(infra)
  # res_sup = builder.add_node_resource(sup_nf, 10, 10, 10)
  # builder.add_node_port(sup_nf, NFFGtoXMLBuilder.PORT_ABSTRACT)
  # builder.add_flow_entry(infra, port, nf_port,
  #                        action="mod_dl_src=12:34:56:78:90:12", delay="5ms",
  #                        bandwidth="10Gbps")

  # Generate same output as Agent_http.py
  builder = Virtualizer3BasedNFFGBuilder()
  infra = builder.add_infra(
    name="single Bis-Bis node representing the whole domain")
  infra_port0 = builder.add_node_port(infra, name="OVS-north external port")
  infra_port1 = builder.add_node_port(infra, name="OVS-south external port")
  builder.add_node_resource(infra, cpu="10 VCPU", mem="32 GB", storage="5 TB")
  nf1 = builder.add_nf_instance(infra, id="NF1", name="example NF")
  nf1port0 = builder.add_node_port(nf1, name="Example NF input port")
  nf1port1 = builder.add_node_port(nf1, name="Example NF output port")
  sup_nf = builder.add_supported_nf(infra, id="nf_a",
                                    name="tcp header compressor")
  builder.add_node_port(sup_nf, name="in", param="...")
  builder.add_node_port(sup_nf, name="out", param="...")
  builder.add_flow_entry(infra, in_port=infra_port0, out_port=nf1port0)
  builder.add_flow_entry(infra, in_port=nf1port1, out_port=infra_port1,
                         action="mod_dl_src=12:34:56:78:90:12")
  return builder.dump()


def test_topo_un ():
  topo = """
<virtualizer>
    <name>Single node</name>
    <nodes>
        <node>
            <NF_instances>
                <node>
                    <name>DPI NF</name>
                    <ports>
                        <port>
                            <name>NF input port</name>
                            <port_type>port-abstract</port_type>
                            <id>1</id>
                        </port>
                        <port>
                            <name>NF output port</name>
                            <port_type>port-abstract</port_type>
                            <id>2</id>
                        </port>
                    </ports>
                    <type>dpi</type>
                    <id>NF1</id>
                </node>
            </NF_instances>
            <flowtable>
                <flowentry>
                    <port>../../../ports/port[id=1]</port>
                    <priority>100</priority>
                    <action>
                        <vlan>
                            <pop/>
                        </vlan>
                    </action>
                    <id>1</id>
                    <match>
                        <vlan_id>2</vlan_id>
                    </match>
                    <out>../../../NF_instances/node[id=NF1]/ports/port[id=1]
                    </out>
                </flowentry>
                <flowentry>
                    <port>../../../NF_instances/node[id=NF1]/ports/port[id=2]
                    </port>
                    <action>
                        <vlan>
                            <push>3</push>
                        </vlan>
                    </action>
                    <id>2</id>
                    <out>../../../ports/port[id=1]</out>
                </flowentry>
            </flowtable>
            <capabilities>
                <supported_NFs>
                    <node>
                        <name>DPI based on libpcre</name>
                        <ports>
                            <port>
                                <name>VNF port 1</name>
                                <port_type>port-abstract</port_type>
                                <id>1</id>
                            </port>
                            <port>
                                <name>VNF port 2</name>
                                <port_type>port-abstract</port_type>
                                <id>2</id>
                            </port>
                        </ports>
                        <type>dpi</type>
                        <id>NF1</id>
                    </node>
                    <node>
                        <name>iptables based firewall</name>
                        <ports>
                            <port>
                                <name>VNF port 1</name>
                                <port_type>port-abstract</port_type>
                                <id>1</id>
                            </port>
                            <port>
                                <name>VNF port 2</name>
                                <port_type>port-abstract</port_type>
                                <id>2</id>
                            </port>
                        </ports>
                        <type>firewall</type>
                        <id>NF2</id>
                    </node>
                    <node>
                        <name>NAT based on iptables</name>
                        <ports>
                            <port>
                                <name>VNF port 1</name>
                                <port_type>port-abstract</port_type>
                                <id>1</id>
                            </port>
                            <port>
                                <name>VNF port 2</name>
                                <port_type>port-abstract</port_type>
                                <id>2</id>
                            </port>
                        </ports>
                        <type>nat</type>
                        <id>NF3</id>
                    </node>
                    <node>
                        <name>ntop monitor</name>
                        <ports>
                            <port>
                                <name>VNF port 1</name>
                                <port_type>port-abstract</port_type>
                                <id>1</id>
                            </port>
                            <port>
                                <name>VNF port 2</name>
                                <port_type>port-abstract</port_type>
                                <id>2</id>
                            </port>
                        </ports>
                        <type>monitor</type>
                        <id>NF4</id>
                    </node>
                    <node>
                        <name>example VNF with several implementations</name>
                        <ports>
                            <port>
                                <name>VNF port 1</name>
                                <port_type>port-abstract</port_type>
                                <id>1</id>
                            </port>
                            <port>
                                <name>VNF port 2</name>
                                <port_type>port-abstract</port_type>
                                <id>2</id>
                            </port>
                        </ports>
                        <type>example</type>
                        <id>NF5</id>
                    </node>
                </supported_NFs>
            </capabilities>
            <ports>
                <port>
                    <name>OVS-north external port</name>
                    <port_type>port-sap</port_type>
                    <id>1</id>
                    <sap>SAP34</sap>
                </port>
            </ports>
            <type>BisBis</type>
            <id>UUID11</id>
            <resources>
                <mem>32 GB</mem>
                <storage>5 TB</storage>
                <cpu>10 VCPU</cpu>
            </resources>
            <name>Universal Node</name>
        </node>
    </nodes>
    <id>UUID001</id>
</virtualizer>
  """
  return topo


def test_topo_os ():
  topo = """
<virtualizer>
    <name>ETH OpenStack-OpenDaylight domain with request</name>
    <nodes>
        <node>
            <NF_instances>
                <node>
                    <name>Parental control B.4</name>
                    <ports>
                        <port>
                            <name>in</name>
                            <capability>...</capability>
                            <port_type>port-abstract</port_type>
                            <id>NF1_in</id>
                        </port>
                    </ports>
                    <type>1</type>
                    <id>NF1</id>
                    <resources>
                        <mem>1024</mem>
                    </resources>
                </node>
            </NF_instances>
            <flowtable>
                <flowentry>
                    <port>../../../ports/port[id=0]</port>
                    <action>strip_vlan</action>
                    <id>f1</id>
                    <match>dl_vlan=1</match>
                    <out>
                        ../../../NF_instances/node[id=NF1]/ports/port[id=NF1_in]
                    </out>
                </flowentry>
                <flowentry>
                    <port>
                        ../../../NF_instances/node[id=NF1]/ports/port[id=NF1_in]
                    </port>
                    <action>mod_vlan_vid:2</action>
                    <id>f2</id>
                    <out>../../../ports/port[id=0]</out>
                </flowentry>
            </flowtable>
            <capabilities>
                <supported_NFs>
                    <node>
                        <name>image0</name>
                        <ports>
                            <port>
                                <name>input port</name>
                                <port_type>port-abstract</port_type>
                                <id>0</id>
                            </port>
                        </ports>
                        <type>0</type>
                        <id>NF0</id>
                    </node>
                    <node>
                        <name>image1</name>
                        <ports>
                            <port>
                                <name>input port</name>
                                <port_type>port-abstract</port_type>
                                <id>0</id>
                            </port>
                        </ports>
                        <type>1</type>
                        <id>NF1</id>
                        <resources>
                            <mem>1024</mem>
                        </resources>
                    </node>
                </supported_NFs>
            </capabilities>
            <ports>
                <port>
                    <name>OVS-north external port</name>
                    <port_type>port-sap</port_type>
                    <id>0</id>
                    <sap>SAP24</sap>
                </port>
            </ports>
            <type>BisBis</type>
            <id>UUID-01</id>
            <resources>
                <mem>32 GB</mem>
                <storage>5 TB</storage>
                <cpu>10 VCPU</cpu>
            </resources>
            <name>single Bis-Bis node representing the whole domain</name>
        </node>
    </nodes>
    <id>UUID-ETH-001-req1</id>
</virtualizer>
"""
  return topo


class NFFGConverter(object):
  """
  Convert different representation of NFFG in both ways.
  """

  def __init__ (self, domain):
    self.domain = domain

  def parse_from_Virtualizer3 (self, xml_data):
    """
    Convert Virtualizer3-based XML str --> NFFGModel based NFFG object

    :param xml_data: XML plain data formatted with Virtualizer
    :type: xml_data: str
    :return: created NF-FG
    :rtype: :any:`NFFG`
    """
    try:
      # Parse given str to XML structure
      tree = ET.ElementTree(ET.fromstring(xml_data))
      # Parse Virtualizer structure
      virtualizer = virt3.Virtualizer().parse(root=tree.getroot())
    except ET.ParseError as e:
      raise RuntimeError('ParseError: %s' % e.message)

    # Get NFFG init params
    nffg_id = virtualizer.id.getValue() if virtualizer.id.isInitialized() \
      else "NFFG-%s" % self.domain
    nffg_name = virtualizer.name.getValue() if \
      virtualizer.name.isInitialized() else nffg_id

    # Create NFFG
    nffg = NFFG(id=nffg_id, name=nffg_name)

    # Define default delay,bw <-- Virtualizer does not store/handle delay/bw
    _delay = None  # 0
    _bandwidth = None  # sys.maxint

    # Iterate over virtualizer/nodes --> node = Infra
    for inode in virtualizer.nodes:
      # Node params
      _id = inode.id.getValue()
      _name = inode.name.getValue() if inode.name.isInitialized() else \
        "name-" + _id
      _domain = self.domain
      _type = inode.type.getValue()
      # Node-resources params
      if inode.resources.isInitialized():
        _cpu = inode.resources.cpu.getAsText().split(' ')[0]
        _mem = inode.resources.mem.getAsText().split(' ')[0]
        _storage = inode.resources.storage.getAsText().split(' ')[0]
        try:
          _cpu = int(_cpu)
          _mem = int(_mem)
          _storage = int(_storage)
        except ValueError:
          pass
      else:
        _cpu = sys.maxint
        _mem = sys.maxint
        _storage = sys.maxint

      # Add Infra Node
      infra = nffg.add_infra(id=_id, name=_name, domain=_domain,
                             infra_type=_type, cpu=_cpu, mem=_mem,
                             storage=_storage, delay=_delay,
                             bandwidth=_bandwidth)

      # Add supported types shrinked from the supported NF list
      for sup_nf in inode.capabilities.supported_NFs:
        infra.add_supported_type(sup_nf.type.getValue())

      # Add ports to Infra Node
      for port in inode.ports:
        # If it is a port connected to a SAP
        if port.port_type.getValue() == "port-sap":
          # Use unique SAP tag as the id of the SAP
          if port.sap.isInitialized():
            s_id = port.sap.getValue()
          else:
            s_id = "SAP%s" % len([s for s in nffg.saps])
          try:
            sap_port_id = int(port.id.getValue())
          except ValueError:
            sap_port_id = port.id.getValue()
          s_name = port.name.getValue() if port.name.isInitialized() else \
            "name-" + _ids_id

          # Create SAP and Add port to SAP
          # SAP default port: sap-type port number
          sap_port = nffg.add_sap(id=s_id, name=s_name).add_port(id=sap_port_id)
          # Add port properties as metadata to SAP port
          sap_port.add_property("name:%s" % port.name.getValue())
          sap_port.add_property("port_type:%s" % port.port_type.getValue())
          if port.sap.isInitialized():
            sap_port.add_property("sap:%s" % port.sap.getValue())

          # Create and add the opposite Infra port
          try:
            infra_port_id = int(port.id.getValue())
          except ValueError:
            infra_port_id = port.id.getValue()
          infra_port = infra.add_port(id=infra_port_id)
          # Add port properties as metadata to Infra port too
          infra_port.add_property("name:%s" % port.name.getValue())
          infra_port.add_property("port_type:%s" % port.port_type.getValue())
          if port.sap.isInitialized():
            infra_port.add_property("sap:%s" % port.sap.getValue())

          # Add infra port capabilities
          if port.capability.isInitialized():
            infra_port.add_property(
              "capability:%s" % port.capability.getValue())

          # Add connection between infra - SAP
          # SAP-Infra is static link --> create link for both direction
          nffg.add_undirected_link(port1=sap_port, port2=infra_port,
                                   delay=_delay,
                                   bandwidth=_bandwidth)

        # If it is not SAP port and probably connected to another infra
        elif port.port_type.getValue() == "port-abstract":
          # Add default port
          try:
            infra_port_id = int(port.id.getValue())
          except ValueError:
            infra_port_id = port.id.getValue()

          # Add port properties as metadata to Infra port
          infra_port = infra.add_port(id=infra_port_id)
          infra_port.add_property("name:%s" % port.name.getValue())
          infra_port.add_property("port_type:%s" % port.port_type.getValue())
          if port.capability.isInitialized():
            infra_port.add_property(
              "capability:%s" % port.capability.getValue())
        # FIXME - check if two infra is connected and create undirected link
        else:
          raise RuntimeError(
            "Unsupported port type: %s" % port.port_type.getValue())

      # Create NF instances
      for nf_inst in inode.NF_instances:
        # Get NF params
        nf_id = nf_inst.id.getAsText()
        nf_name = nf_inst.name.getAsText() if nf_inst.name.isInitialized() \
          else nf_id
        nf_ftype = nf_inst.type.getAsText() if nf_inst.type.isInitialized() \
          else None
        nf_dtype = None
        nf_cpu = nf_inst.resources.cpu.getAsText()
        nf_mem = nf_inst.resources.mem.getAsText()
        nf_storage = nf_inst.resources.storage.getAsText()
        try:
          nf_cpu = int(nf_cpu) if nf_cpu is not None else None
          nf_mem = int(nf_mem) if nf_cpu is not None else None
          nf_storage = int(nf_storage) if nf_cpu is not None else None
        except ValueError:
          pass
        nf_cpu = nf_cpu
        nf_mem = nf_mem
        nf_storage = nf_storage

        # Create NodeNF
        nf = nffg.add_nf(id=nf_id, name=nf_name, func_type=nf_ftype,
                         dep_type=nf_dtype, cpu=nf_cpu, mem=nf_mem,
                         storage=nf_storage, delay=_delay,
                         bandwidth=_bandwidth)

        # Create NF ports
        for nf_inst_port in nf_inst.ports:

          # Create and Add port
          nf_port = nf.add_port(id=nf_inst_port.id.getAsText())

          # Add port properties as metadata to NF port
          if nf_inst_port.capability.isInitialized():
            nf_port.add_property(
              "capability:%s" % nf_inst_port.capability.getAsText())
          if nf_inst_port.name.isInitialized():
            nf_port.add_property("name:%s" % nf_inst_port.name.getAsText())
          if nf_inst_port.port_type.isInitialized():
            nf_port.add_property(
              "port_type:%s" % nf_inst_port.port_type.getAsText())

          # Add connection between Infra - NF
          # Get the smallest available port for the Infra Node
          next_port = max(max({p.id for p in infra.ports}) + 1,
                          len(infra.ports))
          # NF-Infra is dynamic link --> create special undirected link
          nffg.add_undirected_link(port1=nf_port,
                                   port2=infra.add_port(id=next_port),
                                   dynamic=True, delay=_delay,
                                   bandwidth=_bandwidth)
          # dynamic=True)
          # TODO - add flowrule parsing
    return nffg, virtualizer

  def dump_to_Virtualizer3 (self, nffg, virtualizer=None):
    """
    Convert NFFGModel based NFFG object --> Virtualizer

    :param nffg: nffg object
    :type: nffg: :any:`NFFG`
    :param virtualizer: use as the base Virtualizer object (optional)
    :type virtualizer: :class:`virtualizer3.Virtualizer`
    :return: created Virtualizer object
    :rtype: :class:`virtualizer3.Virtualizer`
    """
    # Clear unnecessary links
    nffg.clear_links(NFFG.TYPE_LINK_REQUIREMENT)
    nffg.clear_links(NFFG.TYPE_LINK_SG)
    # nffg.clear_links(NFFG.TYPE_LINK_DYNAMIC)
    # If virtualizer is not given create the infras,ports,SAPs first then
    # insert the initiated NFs and flowrules, supported NFs skipped!
    if virtualizer is None:
      # Create Virtualizer with basic params -virtualizer/{id,name}
      virtualizer = virt3.Virtualizer(id=str(nffg.id), name=str(nffg.name))
      # Add bare Infra node entities
      for infra in nffg.infras:
        # Create infra node with basic params - nodes/node/{id,name,type}
        infra_node = virt3.Infra_node(id=str(infra.id), name=str(infra.name),
                                      type=str(infra.infra_type))
        # Add resources nodes/node/resources
        cpu = str(infra.resources.cpu) if infra.resources.cpu else None
        mem = str(infra.resources.mem) if infra.resources.mem else None
        storage = str(
          infra.resources.storage) if infra.resources.storage else None
        resources = virt3.NodeResources(cpu=cpu, mem=mem, storage=storage,
                                        parent=infra_node)
        infra_node.resources = resources
        # Add Infra node - nodes/node
        virtualizer.nodes.add(infra_node)
      # Add SAPS as special ports to infras
      for sap in nffg.saps:
        # Get SAP -> Infra node edges
        sap_infra_links = [(u, v, l) for u, v, l in
                           nffg.network.out_edges_iter((sap.id,), data=True) if
                           l.dst.node.type == NFFG.TYPE_INFRA]
        # Iterate over out edges
        for u, v, link in sap_infra_links:
          # FIXME - SAP port not added to SDN-SW infra
          # Create the sap-port - ports/port/{}
          s_id = str(link.dst.id)
          capability = None
          sap_t = None
          name = None
          # Iter over SAP's actual port properties
          for property in link.src.properties:
            if str(property).startswith("capability"):
              capability = property.split(':')[1]
            elif str(property).startswith("name"):
              name = property.split(':')[1]
            elif str(property).startswith("sap"):
              sap_t = property.split(':')[1]
          sap_port = virt3.Port(id=s_id, name=name, port_type="port-sap",
                                capability=capability, sap=sap_t)
          # Add sap-port to the Infra node
          virtualizer.nodes[v].ports.add(sap_port)
      # Add Nfs to the Infra node
      for infra in nffg.infras:
        # for nf in nffg.running_nfs(infra.id):
        for nf_link in {link for u, v, link in
                        nffg.network.out_edges_iter((infra.id,), data=True) if
                        link.dst.node.type == NFFG.TYPE_NF}:
          nf = nf_link.dst.node
          try:
            nf_inst = virtualizer.nodes[infra.id].NF_instances[nf.id]
          except KeyError:
            # Create resource to NF - NF_instances/node/resources
            cpu = str(nf.resources.cpu) if nf.resources.cpu else None
            mem = str(nf.resources.mem) if nf.resources.mem else None
            storage = str(
              nf.resources.storage) if nf.resources.storage else None
            res = virt3.NodeResources(cpu=cpu, mem=mem, storage=storage)
            # Create NF with resources - NF_instances/node
            nf_inst = virt3.Node(id=str(nf.id),
                                 name=str(nf.name) if nf.name else None,
                                 type=str(
                                   nf.functional_type) if nf.functional_type
                                 else None, resources=res)
            # Add NF to the Infra node
            virtualizer.nodes[infra.id].NF_instances.add(nf_inst)
          # Get port name
          port_name = "port" + str(nf_link.dst.id)
          for property in nf_link.dst.properties:
            if property.startswith('name'):
              port_name = property.split(':')[1]
              break
          # Create Port object
          nf_port = virt3.Port(id=str(nf_link.dst.id), name=str(port_name),
                               port_type="port-abstract")
          # Add port to NF
          nf_inst.ports.add(nf_port)
      # TODO - add static links???
      # FIXME - this is a little bit of hack
      # FIXME - SAP ports created again -> override good sap port
      # for infra in nffg.infras:
      #   for port in infra.ports:
      #     # bigger than 65535 --> virtual port which is an object id, not phy
      #     if len(str(port.id)) > 5:
      #       continue
      #     # if the port not exist in the virtualizer
      #     if str(port.id) not in virtualizer.nodes[
      #       infra.id].ports.port.getKeys():
      #       port_name = "port" + str(port.id)
      #       for property in port.properties:
      #         if property.startswith('name'):
      #           port_name = property.split(':')[1]
      #         break
      #       virtualizer.nodes[infra.id].ports.add(
      #         virt3.Port(id=str(port.id), name=port_name,
      #                    port_type="port-abstract"), )
      #       # print virtualizer
      # TODO - add flowrule
      # Add flowrules
      cntr = 0
      for infra in nffg.infras:
        for port in infra.ports:
          for flowrule in port.flowrules:
            # print flowrule
            # Get id
            f_id = str(cntr)
            cntr += 1
            # Get priority
            priority = str('100')
            # Get in port
            fr = flowrule.match.split(";")
            if fr[0].split('=')[0] != "in_port":
              raise RuntimeError(
                "Wrong flowrule format: missing in in_port from match")
            in_port = str(port.id)
            # in_port = fr[0].split('=')[1]
            try:
              # Flowrule in_port is a phy port in Infra Node
              in_port = virtualizer.nodes[infra.id].ports[in_port]
            except KeyError:
              # in_port is a dynamic port --> search for connected NF's port
              from pprint import pprint
              pprint(nffg.network.__dict__)
              # in_port, p_nf = [(str(l.dst.id), l.dst.node.id) for u, v, l in
              #                  nffg.network.out_edges_iter((infra.id,),
              #                                              data=True) if
              #                  str(l.src.id) == str(in_port)][0]
              print virtualizer
              for u, v, l in nffg.network.edges(data=True):
                print u, v, l
                if l.src.id == port.id:
                  print l.dst.id

              # in_port, p_nf = [(str(l.dst.id), l.dst.node.id) for u, v, l in
              #                  nffg.network.out_edges_iter((infra.id,),
              #                                              data=True) if
              #                  str(l.src.id) == str(in_port)][0]

              in_port = virtualizer.nodes[infra.id].NF_instances[p_nf].ports[
                in_port]
            # Get match
            match = None
            if len(fr) > 1:
              if fr[1].split('=')[0] == "TAG":
                vlan = int(fr[1].split('=')[1].split('-')[-1])
                if self.domain == NFFG.DOMAIN_OS:
                  match = r"dl_vlan=%s" % format(vlan, '#06x')
                elif self.domain == NFFG.DOMAIN_UN:
                  match = u"<vlan_id>%s<vlan_id>" % vlan
              elif fr[1].split('=')[0] == "UNTAG":
                if self.domain == NFFG.DOMAIN_OS:
                  match = r"strip_vlan"
                elif self.domain == NFFG.DOMAIN_UN:
                  match = u"<vlan><pop/></vlan>"
            # Get out port
            fr = flowrule.action.split(';')
            if fr[0].split('=')[0] != "output":
              raise RuntimeError(
                "Wrong flowrule format: missing output from action")
            out_port = fr[0].split('=')[1]
            try:
              # Flowrule in_port is a phy port in Infra Node
              out_port = virtualizer.nodes[infra.id].ports[out_port]
            except KeyError:
              # out_port is a dynamic port --> search for connected NF's port
              out_port, p_nf = [(str(l.dst.id), l.dst.node.id) for u, v, l in
                                nffg.network.out_edges_iter((infra.id,),
                                                            data=True) if
                                str(l.src.id) == out_port][0]
              out_port = virtualizer.nodes[infra.id].NF_instances[p_nf].ports[
                out_port]
            # Get action
            action = None
            if len(fr) > 1:
              if fr[1].split('=')[0] == "TAG":
                vlan = int(fr[1].split('=')[1].split('-')[-1])
                if self.domain == NFFG.DOMAIN_OS:
                  action = r"mod_vlan_vid:%s" % format(vlan, '#06x')
                elif self.domain == NFFG.DOMAIN_UN:
                  action = u"<vlan_id>%s<vlan_id>" % vlan
              elif fr[1].split('=')[0] == "UNTAG":
                if self.domain == NFFG.DOMAIN_OS:
                  action = r"strip_vlan"
                elif self.domain == NFFG.DOMAIN_UN:
                  action = u"<vlan><pop/></vlan>"
            # print out_port
            virtualizer.nodes[infra.id].flowtable.add(
              Flowentry(id=f_id, priority=priority, port=in_port, match=match,
                        action=action, out=out_port))
    return virtualizer, nffg

  @staticmethod
  def unescape_output_hack (data):
    return data.replace("&lt;", "<").replace("&gt;", ">")


if __name__ == "__main__":
  # test_xml_based_builder()
  # txt = test_virtualizer3_based_builder()
  txt = test_topo_un()
  # txt = test_topo_os()
  # print txt
  # print Virtualizer3BasedNFFGBuilder.parse(txt)
  c = NFFGConverter(domain=NFFG.DOMAIN_OS)
  nffg, vv = c.parse_from_Virtualizer3(xml_data=txt)
  # # UN
  # nffg.network.node['UUID11'].ports[1].add_flowrule(
  #   match="in_port=1;TAG=sap1-comp-42", action="output=2;UNTAG")
  # OS
  # nffg.network.node['UUID-01'].ports[1].add_flowrule(
  #   match="in_port=1;TAG=sap1-comp-42", action="output=0;UNTAG")
  # nffg.network.node['UUID-01'].ports[1].add_flowrule(
  #   match="in_port=1;TAG=sap1-comp-42", action="output=0;UNTAG")
  from pprint import pprint

  pprint(nffg.network.__dict__)
  print nffg.dump()

  # from nffg import gen
  #
  # nffg = gen()
  # print nffg.dump()
  # v = c.dump_to_Virtualizer3(nffg, virtualizer=vv)
  # v, nffg = c.dump_to_Virtualizer3(nffg)
  # out = str(v)
  # out = out.replace("&lt;", "<").replace("&gt;", ">")
  # print out
