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

from nffglib import *


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
    Delete a single node from the NF-FG
    """
    raise NotImplementedError("Not implemented yet!")

  # General functions for create/parse/dump/convert NFFG

  @staticmethod
  def parse (data, format):
    """
    General function for parsing data as a new :any::`NFFG` object and return
    with its reference..

    :param data: raw data
    :type data: ``format``
    :param format: ``data`` format
    :type format: str
    :return: parsed and initiated NFFG object
    :rtype: :any::`AbstractNFFG`
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
  """
  # Do not modified
  __UUID_NUM = 0
  # Default infrastructure node type
  DEFAULT_INFRA_TYPE = "BisBis"

  def __init__ (self):
    super(NFFGtoXMLBuilder, self).__init__(None, "1.0")
    # Init main container: virtualizer
    self.__virtualizer = Virtualizer()
    self.__virtualizer.g_idName = IdNameGroup(self.__virtualizer)
    NFFGtoXMLBuilder.__UUID_NUM += 1
    # Add <id> tag
    self.__virtualizer.g_idName.l_id = "UUID-ESCAPE-BME-%i" % \
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

  @staticmethod
  def parse (data, format):
    pass

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
  # General functions to add NFFG elements easily
  ##############################################################################

  def add_infra (self, id=None, name=None, type=None):
    """
    Add an infrastructure node ot NFFG (as a BiS-BiS).

    :param id:
    :param name:
    :param type:
    :return: None
    """
    # Set mandatory attributes
    type = self.DEFAULT_INFRA_TYPE if type is None else str(type)
    id = str(len(self.nodes) + 1) if id is None else str(id)
    name = type + str(id) if name is None else str(name)
    # Create Infrastructure wrapper
    infra = InfraNodeGroup(self.__virtualizer)
    # Add id, name, type
    infra.g_node = NodeGroup(infra)
    infra.g_node.g_idNameType = IdNameTypeGroup(infra.g_node)
    infra.g_node.g_idNameType.g_idName = IdNameGroup(infra.g_node.g_idNameType)
    infra.g_node.g_idNameType.g_idName.l_id = id
    infra.g_node.g_idNameType.g_idName.l_name = name
    infra.g_node.g_idNameType.l_type = type
    # Add necessary flow table group
    infra.g_flowtable = FlowTableGroup(infra)
    # Add infra to nodes
    self.nodes.append(infra)

  def add_port (self, type, parent, id=None, name=None):
    """
    Add a port into a Node.

    :param type:
    :param parent:
    :param id:
    :param name:
    :return: None
    """

  def del_node (self, id):
    pass

  def add_req (self, edge_req):
    pass

  def add_nf (self, node_nf):
    pass

  def add_sap (self, node_sap):
    pass

  def add_edge (self, src, dst, params=None):
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
  builder.id = 42
  builder.name = "testname"
  builder.add_infra()
  print builder
