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

# Types of infrastructure nodes
BISBIS = 0


class Flowclass(object):
  """
  Class for storing flowclasses (flowrule without action)
  """

  def __init__ (self, match):
    self.match = match


class Flowrule(Flowclass):
  """
  Class for storing flowrules
  """

  def __init__ (self, match, action):
    super(Flowrule, self).__init__(match)
    self.action = action


class Port(object):
  """
  Class for storing a port of NF or infrastructure node
  """

  def __init__ (self, id, props, flowrules=None):
    self.id = id
    self.props = props
    self.flowrules = flowrules


class ResOfNode(object):
  """
  Class for storing resource information for nodes
  """

  def __init__ (self, cpu, mem, sto, net):
    self.cpu = cpu
    self.mem = mem
    self.sto = sto
    self.net = net


class ResOfEdge(object):
  """
  Class for storing resource information for edges
  """

  def __init__ (self, delay, bandwidth):
    self.delay = delay
    self.bandwidth = bandwidth


class Node(object):
  """
  Class for different types of nodes in the NF-FG
  """

  def __init__ (self, id):
    super(Node, self).__init__()
    self.id = id


class NodeNF(Node):
  """
  Class for NF nodes in the NF-FG
  """

  def __init__ (self, id, functional_type, resources, ports, name=None,
       deployment_type=None, monitoring=None):
    super(NodeNF, self).__init__(id)
    self.name = name
    self.functional_type = functional_type
    self.spec = {'deployment_type': deployment_type, 'resources': resources}
    self.ports = ports
    self.monitoring = monitoring


class NodeSAP(Node):
  """
  Class for SAP nodes in the NF-FG
  """

  def __init__ (self, id, ports, name=None):
    super(NodeSAP, self).__init__(id)
    self.name = name
    self.ports = ports


class NodeInfra(Node):
  """
  Class for infrastructure nodes in the NF-FG
  """

  def __init__ (self, id, resources, ports, name=None, domain=None,
       infra_type=BISBIS):
    super(NodeInfra, self).__init__(id)
    self.name = name
    self.domain = domain
    self.type = infra_type
    self.resources = resources  # ResOfNode
    self.ports = ports


class Edge(object):
  """
  Class for different types of edges in the NF-FG
  """

  def __init__ (self, id, src, dst):
    super(Edge, self).__init__()
    self.id = id
    self.src = src  # (Node, Port) or (node_id, port_id)?
    self.dst = dst  # (Node, Port) or (node_id, port_id)?


class EdgeLink(Edge):
  """
  Class for static and dynamic links in the NF-FG
  """

  def __init__ (self, id, src, dst, resources):
    super(Edge, self).__init__(id, src, dst)
    self.resources = resources  # ResOfEdge


class EdgeSGLink(Edge):
  """
  Class for links of SG
  """

  def __init__ (self, id, src, dst, flowclass):
    super(Edge, self).__init__(id, src, dst)
    self.flowclass = flowclass  # flowrule without action


class EdgeReq(Edge):
  """
  Class for requirements between arbitrary NF modes
  """

  def __init__ (self, id, src, dst, reqs):
    super(Edge, self).__init__(id, src, dst)
    self.reqs = reqs  # ResOfEdge
