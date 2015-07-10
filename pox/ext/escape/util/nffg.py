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

  def __init__ (self, id, version='1.0'):
    # def __init__ (self, id, name=None, version='1.0'):
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

  def __init__ (self, id=None, name=None, virtualizer=None):
    """
    Init
    """
    super(NFFG, self).__init__(id)

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
  def parse (data, format=None):
    """
    """
    pass

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
    raise NotImplementedError("Not implemented yet!")

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
  # Port types
  PORT_TYPE = enum(ABSTRACT="port-abstract", SAP="port-sap")

  def __init__ (self):
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
    self.__virtualizer.g_links = LinksGroup(self.__virtualizer)
    self.__virtualizer.g_links.c_links = Links(self.__virtualizer.g_links)

  ##############################################################################
  # Builder design pattern related functions
  ##############################################################################

  def dump (self):
    """
    Return the constructed NFFG in XML format.

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
    Return the constructed XML object.

    :return: NFFG
    :rtype: Virtualizer
    """
    return self.__virtualizer

  @staticmethod
  def parse (data):
    """
    Return the parsed XML.

    :param data: raw text
    :type data: str
    :return: parsed XML structure
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
    Return the list of links.

    :return: links
    :rtype: list(Links)
    """
    return self.__virtualizer.g_links.c_links.list_link

  ##############################################################################
  # Extended function for bridging over the differences between NFFG repr
  ##############################################################################

  def add_port (self, parent, type, id=None, name=None):
    """
    Add a port into a Node.

    :param parent: parent node
    :type parent: e.g. Virtualizer, InfraNodeGroup
    :param type: type of the port as ``PORT_TYPE``
    :type type: one of ``PORT_TYPE`` enum
    :param id: port ID (optional)
    :type id: str
    :param name: port name (optional)
    :type name: str (optional)
    :return: port object
    :rtype: PortGroup
    """
    # Add ports container if it's not exist
    if parent.g_node.c_ports is None:
      parent.g_node.c_ports = Ports(parent.g_node)
    # Define mandatory attributes
    id = str(len(parent.g_node.c_ports.list_port)) if id is None else str(id)
    name = "port" + str(id) if name is None else str(name)
    # Create port
    port = PortGroup(parent.g_node.c_ports)
    # Add id, name, type
    port.g_idName = IdNameGroup(port)
    port.g_idName.l_id = id
    port.g_idName.l_name = name
    port.g_portType = PortTypeGroup(port)
    if type == self.PORT_TYPE.ABSTRACT:
      _type = PortAbstractCase(port.g_portType)
      _type.l_portType = type
    elif type == self.PORT_TYPE.SAP:
      _type = PortSapCase(port.g_portType)
      _type.l_portType = type
      # TODO handle vx-lan choice in sap-type
    else:
      raise RuntimeError("Not supported Port type: %s" % type)
    port.g_portType = _type
    # Add port to ports
    parent.g_node.c_ports.list_port.append(port)
    return port

  def __add_connection (self, parent, src, dst, id=None, name=None):
    """
    Add a connection a.k.a a <link> to a Node.

    :param parent: parent node
    :type parent: e.g. Virtualizer, InfraNodeGroup
    :param src: source port
    :type src: PortGroup
    :param dst: destination port
    :type dst: PortGroup
    :param id: link ID (optional)
    :type id: str or int
    :param name: link name (optional)
    :type name: str
    :return: link object
    :rtype:
    """
    if not isinstance(src, PortGroup) or not isinstance(dst, PortGroup):
      raise RuntimeError("scr and dst must be a port object (PortGroup)!")
    # Add links container if it's not exist
    if parent.g_links is None:
      parent.g_links = LinksGroup(parent)
      parent.g_links.c_links = Links(parent.g_links)
    # Define mandatory attributes
    id = str(len(parent.g_links.c_links.list_link)) if id is None else str(id)
    name = str("link" + str(id)) if name is None else str(name)
    # Create link
    link = Link(parent.g_links.c_links)
    # Add id, name src, dst
    link.g_idName = IdNameGroup(link)
    link.g_idName.l_id = id
    link.g_idName.l_name = name
    # Add link to links
    parent.g_links.c_links.list_link.append(link)
    return link

  ##############################################################################
  # General functions to add NFFG elements easily
  ##############################################################################

  def add_infra (self, id=None, name=None, type=None):
    """
    Add an infrastructure node to NFFG (as a BiS-BiS).

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
    id = str(len(self.nodes)) if id is None else str(id)
    name = str(type + str(id)) if name is None else str(name)
    # Create Infrastructure wrapper
    infra = InfraNodeGroup(self.__virtualizer)
    # Add id, name, type
    infra.g_node = NodeGroup(infra)
    infra.g_node.g_idNameType = IdNameTypeGroup(infra.g_node)
    infra.g_node.g_idNameType.g_idName = IdNameGroup(infra.g_node.g_idNameType)
    infra.g_node.g_idNameType.g_idName.l_id = id
    infra.g_node.g_idNameType.g_idName.l_name = name
    infra.g_node.g_idNameType.l_type = type
    # Add necessary flow table group for InfraNodeGroup
    infra.g_flowtable = FlowTableGroup(infra)
    # Add infra to nodes
    self.nodes.append(infra)
    return infra

  def add_edge (self, src, dst, params=None):
    """
    Add an edge link to the NFFG: a link between infrastructure node ports.

    :param src:
    :param dst:
    :param params:
    :return:
    """

  def del_node (self, id):
    pass

  def add_req (self, edge_req):
    pass

  def add_nf (self, node_nf):
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

  builder = NFFGtoXMLBuilder()
  infra = builder.add_infra()
  port = builder.add_port(infra, NFFGtoXMLBuilder.PORT_TYPE.ABSTRACT)
  # builder.add_connection(infra, port, port)
  print builder
