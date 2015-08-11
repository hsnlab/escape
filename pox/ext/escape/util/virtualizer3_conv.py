# Copyright 2015 Janos Czentye
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
from nffg import AbstractNFFG
from virtualizer3 import *


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

  def __init__(self):
    """
    Init. Create an empty virtualizer container and the necessary sub-objects.

    :return: None
    """
    super(XMLBasedNFFGBuilder, self).__init__()
    # Init main container: virtualizer
    #self.__virtualizer = Virtualizer()
    #self.__virtualizer.g_idName = IdNameGroup(self.__virtualizer)
    # Add <id> tag
    
    #self.__virtualizer.g_idName.l_id = "UUID-ESCAPE-BME-%03d" % \
    #                                   XMLBasedNFFGBuilder.__UUID_NUM
    # Add <name> tag
    #self.__virtualizer.g_idName.l_name = "ESCAPE-BME orchestrator version v2.0"
    # Add <nodes> tag
    #self.__virtualizer.c_nodes = Nodes(self.__virtualizer)
    # Add <links> tag
    # self.__virtualizer.g_links = LinksGroup(self.__virtualizer)
    # self.__virtualizer.g_links.c_links = Links(self.__virtualizer.g_links)

    id_="UUID-ETH-%03d" %XMLBasedNFFGBuilder.__UUID_NUM

    self.__virtualizer = Virtualizer(id=id_, name="ETH OpenStack-OpenDaylight domain")
    XMLBasedNFFGBuilder.__UUID_NUM += 1

  ##############################################################################
  # Builder design pattern related functions
  ##############################################################################

  def dump(self):
    """
    Return the constructed NFFG as a string in XML format.

    :return: NFFG in XML format
    :rtype: str
    """
    return self.__virtualizer.xml()

  def __str__(self):
    """
    Dump the constructed NFFG as a pretty string.

    :return: NFFG in XML format
    :rtype: str
    """
    return self.__virtualizer.__str__()

  def build(self):
    """
    Return the constructed XML object a.k.a. the Virtualizer.

    :return: NFFG
    :rtype: Virtualizer
    """
    return self.__virtualizer

  @classmethod
  def parse(cls, data):
    """
    Parse the given XML-formatted string and return the constructed Virtualizer.

    :param data: raw text formatted in XML
    :type data: str
    :return: parsed XML object-structure
    :rtype: Virtualizer
    """
    return Virtualizer().parse(filename=data)

  ##############################################################################
  # Simplifier function to access XML tags easily
  ##############################################################################

  @property
  def id(self):
    """
    Return the id of the NFFG.

    :return: id
    :rtype: str
    """
    return self.__virtualizer.id.data

  @id.setter
  def id(self, id):
    """
    Set the id of NFFG.

    :param id: new id
    :type id: int or str
    :return: None
    """
    self.__virtualizer.id.data = str(id)

  @property
  def name(self):
    """
    Return the name of NFFG.

    :return: name
    :rtype: str
    """
    return self.__virtualizer.name.data

  @name.setter
  def name(self, name):
    """
    Set the name of NFFG.

    :param name: new name
    :type name: str
    :return: None
    """
    self.__virtualizer.name.data = str(name)

  @property
  def nodes(self):
    """
    Return the list of nodes.

    :return: nodes
    :rtype: list(InfraNodeGroup) ### RETURN DICT {nodeID:InfraNodeGroup}
    """
    return self.__virtualizer.nodes.node

  @property
  def links(self):
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

  def add_node(self, parent, id=None, name=None, type=None):
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
    id = str(len(self.__virtualizer.nodes.node.getKeys())) if id is None else str(id)
    name = str("node" + str(id)) if name is None else str(name)

    node = Node(parent=parent,
                id=id,
                name=name,
                type=type)
    return node

  def add_infrastructure_node(self, id=None, name=None, type=None):
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
    id = "UUID-%02d" % len(self.__virtualizer.nodes.node.getKeys()) if id is None else str(id)
    name = str(type + str(id)) if name is None else str(name)
    
    infranode = Infra_node(id=id,
                          name=name,
                          type=type)
    self.__virtualizer.nodes.add(infranode)
    
    return infranode

  def add_node_port(self, parent, type=PORT_ABSTRACT, id=None, name=None,
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
    port = Port(parent=parent,
                id=id, 
                name=name,
                port_type=type, 
                capability=str(param), 
                sap=str(param))
    
    parentPath = parent.getPath()
    if isinstance(parent,Infra_node):
      self.__virtualizer.nodes[parent.id.data].ports.add(port)
    elif "NF_instances" in parentPath:
      infraParent = parent.getParent().getParent()
      self.__virtualizer.nodes[infraParent.id.data].NF_instances.node[parent.id.data].ports.add(port)
    elif "supported_NFs" in parentPath:
      infraParent = parent.getParent().getParent().getParent()
      self.__virtualizer.nodes[infraParent.id.data].capabilities.supported_NFs[parent.id.data].ports.add(port)
    return port

  def add_node_resource(self, parent, cpu=None, mem=None, storage=None):
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
    resources=NodeResources(parent=parent,
                            cpu=str(cpu),
                            mem=str(mem),
                            storage=str(storage))
    self.__virtualizer.nodes[parent.id.data].resources = resources
    return resources

  def add_link_resource(self, parent, delay=None, bandwidth=None):
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
    resources = LinkResources(parent=parent,
                              delay=delay, 
                              bandwidth=bandwidth)
    self.__virtualizer.links[parent.id.data].resources = resources
    return resources

  def add_nf_instance(self, parent, id=None, name=None, type=None):
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
    nf_instance = Node(parent=parent,
                        id=id,
                        name=name,
                        type=type)
    self.__virtualizer.nodes[parent.id.data].NF_instances.node.add(nf_instance)
    return nf_instance

  def add_supported_nf(self, parent, id=None, name=None, type=None):
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
    supported_nf = Node(parent=parent,
                        id=id,
                        name=name,
                        type=type)
    self.__virtualizer.nodes[parent.id.data].capabilities.supported_NFs.node.add(supported_nf)
    return supported_nf

  def add_flow_entry(self, parent, in_port, out_port, match=None, action=None,
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
    _in_port = parent.getRelPath(in_port)
    _out_port = parent.getRelPath(out_port)

    flowentry = Flowentry(parent=parent, 
                          port=_in_port,
                          match=str(match),
                          action=action,
                          out=_out_port)
    flowentry_resource = FlowentryResources(parent=flowentry,
                                            delay=delay,
                                            bandwidth=bandwidth)
    flowentry.resources = flowentry_resource

    parentPath = parent.getPath()
    if isinstance(parent,Infra_node):
      self.__virtualizer.nodes[parent.id.data].flowtable.add(flowentry)
    elif "NF_instances" in parentPath:
      infraParent = parent.getParent().getParent()
      self.__virtualizer.nodes[infraParent.id.data].NF_instances.node[parent.id.data].flowtable.add(flowentry)
    elif "supported_NFs" in parentPath:
      infraParent = parent.getParent().getParent().getParent()
      self.__virtualizer.nodes[infraParent.id.data].capabilities.supported_NFs[parent.id.data].flowtable.add(flowentry)
    return flowentry

  def __add_connection(self, parent, src, dst, id=None, name=None, delay=None,
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
    link = Link(parent=parent,
                id=id,
                name=name,
                src=src,
                dst=dst)
    linkresources = LinkResources(parent=link, delay=delay, bandwidth=bandwidth)
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
    if not isinstance(src, Port) or not isinstance(dst, Port):
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


def test_builder ():
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
  infra = builder.add_infra(name="single Bis-Bis node representing the whole domain")
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


if __name__ == "__main__":
  test_builder()
