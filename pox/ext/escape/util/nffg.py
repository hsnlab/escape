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
import os

import json
from pprint import pprint
import getopt, sys
import networkx as nx
from abc import ABCMeta, abstractmethod

class AbstractNFFG(object):
  """
  Abstract class for managing single NF-FG data structure

  The NF-FG data model is described in YANG.  This class provides the
  interfaces with the high level data manipulation functions.
  """

  __metaclass__ = ABCMeta

  def __init__ (self, id, name=None, version='1.0'):
    """
    Init
    """
    super(AbstractNFFG, self).__init__()
    self.id = id
    self.name = name
    self.version = version

    # # from Janos's code
    # # merging should be reconsidered
    # # additional input params: json=None, file=None
    # if json:
    #   self._init_from_json(json)
    # elif file and not file.startswith('/'):
    #   file = os.path.abspath(file)
    #   with open(file, 'r') as f:
    #     self._init_from_json(json.load(f))

  @abstractmethod
  def add_nf(self, node_nf):
    """
    Add a single NF node to the NF-FG
    """
    return

  @abstractmethod
  def add_sap(self, node_sap):
    """
    Add a single SAP node to the NF-FG
    """
    return

  @abstractmethod
  def add_infra(self, node_infra):
    """
    Add a single infrastructure node to the NF-FG
    """
    return

  def add_edge(self, src, dst, params=None):
    """
    Add an edge to the NF-FG

    :param src: source (node, port) of the edge
    :type src: (Node, Port) inherited Node classes: NodeNF, NodeSAP, NodeInfra
    :param dst: destination (node, port) of the edge
    :type dst: (Node, Port) inherited Node classes: NodeNF, NodeSAP, NodeInfra
    :param params: attribute of the edge depending on the type
    :type params: ResOfEdge or Flowrule
    :return: None
    """
    if isinstance(src[0], NodeNF) and isinstance(dst[0], NodeNF):
      # edge between NFs
      if isinstance(params, ResOfEdge):
        # requirements between two arbitrary NFs
        e = EdgeReq(src, dst, params)
        self.add_req(e)
      else:
        # SG link
        e = EdgeSGLink(src, dst, params)
        self.add_sglink(e)
    else:
      # static or dynamic infrastructure link
      e = EdgeLink(src, dst, params)
      self.add_link(e)

  @abstractmethod
  def add_link(self, edge_link):
    """
    Add a static or dynamic infrastructure link to the NF-FG
    """
    return

  @abstractmethod
  def add_sglink(self, edge_sglink):
    """
    Add an SG link to the NF-FG
    """
    return

  @abstractmethod
  def add_req(self, edge_req):
    """
    Add a requirement link to the NF-FG
    """
    return

  @abstractmethod
  def del_node(self, id):
    """
    Delete a single node from the NF-FG
    """
    return

  def _init_from_json (self, json_data):
    """
    Initialize the NFFG object from JSON data

    :param json_data: NF-FG represented in JSON format
    :type json_data: str
    :return: None
    """
    # TODO - implement! This function has already used in layer APIs

  def load_from_file (self, filename):
    with open(filename) as json_file:    
      nffg = json.load(json_file)

    return nffg

  def load_from_file (self, filename):
    with open(filename) as json_file:    
      nffg = json.load(json_file)

    return nffg

  def to_json (self):
    """
    Return a JSON string represent this instance

    :return: JSON formatted string
    :rtype: str
    """


class NFFG(AbstractNFFG, nx.MultiGraph):
  """
  NF-FG implementation based on NetworkX.

  Implement the AbstractNFFG using NetworkX graph representation
  internally.  Implement the high level functions and additionally
  expose NetworkX API.
  """

  def __init__ (self):
    """
    Init
    """
    super(NFFG, self).__init__()
    self.id = None
    # TODO - implement
    self.error = "NotImplemented"

  def add_nf(self, node_nf):
    """
    Add a single NF node to the NF-FG
    """
    pass

  def add_sap(self, node_sap):
    """
    Add a single SAP node to the NF-FG
    """
    pass

  def add_infra(self, node_infra):
    """
    Add a single infrastructure node to the NF-FG
    """
    pass

  def add_link(self, edge_link):
    """
    Add a static or dynamic infrastructure link to the NF-FG
    """
    pass

  def add_sglink(self, edge_sglink):
    """
    Add an SG link to the NF-FG
    """
    pass

  def add_req(self, edge_req):
    """
    Add a requirement link to the NF-FG
    """
    pass

  def del_node(self, id):
    """
    Delete a single node from the NF-FG
    """
    pass


def main (argv = None):
  if argv == None:
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

  nffg = NFFG()
  res = nffg.load_from_file(filename)
  pprint(res)

if __name__ == "__main__":
    main()
