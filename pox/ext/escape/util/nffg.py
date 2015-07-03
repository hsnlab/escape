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

from nffglib import Virtualizer


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
    self.id = id
    self.version = version
    self.format = None

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
  # Used format
  FORMAT = "XML"

  def __init__ (self, id=42, name=None, virtualizer=None):
    """
    Init
    """
    super(NFFG, self).__init__(id)
    self.id = id
    self.name = name
    if virtualizer is not None:
      self.virtualizer = virtualizer
    else:
      self.virtualizer = Virtualizer()

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
    Parse the NF-FG representation from given data. If the format is given,
    the data will be parsed according to the format.
    Currently the only supported format is a file, where the given data param
    is the file path.

    :param data: NF-FG representation
    :type data: ``format`` (default: XML as str)
    :param format: optional format e.g. file
    :type format: str
    :return: NFFG object
    :rtype: :any::`NFFG`
    """
    if format is None:
      virt = Virtualizer.parse(text=data)
    elif format.upper() == "FILE":
      virt = Virtualizer.parse(file=data)
    else:
      raise RuntimeError("Not supported format!")
    return NFFG(virtualizer=virt)

  def dump (self):
    """
    Return the NF-FG representation as an XML text.

    :return: NF-FG representation as XML
    :rtype: str
    """
    return self.virtualizer.xml()

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
  main()
