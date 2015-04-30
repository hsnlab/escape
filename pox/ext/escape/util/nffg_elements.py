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

from pprint import pprint
import getopt, sys

# Types of infrastructure nodes
BISBIS = 0

class Flowrule(object):
  """
  Class for storing flowrules or flowclasses
  """

  def __init__ (self, match, action=None):
    self.match = match
    self.action = action


class Port(object):
  """
  Class for storing a port of NF or infrastructure node
  """

  def __init__ (self, id, props, flowrules=None):
    self.id = id
    self.props = props
    self.flowrules = flowrules


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

  def __init__ (self, id, name=None, functional_type, 
                deployment_type=None, resources, ports, monitoring=None):
    super(NodeInfra, self).__init__(id)
    self.name = name
    self.functional_type = functional_type
    self.spec['deployment_type'] = deployment_type
    self.spec['resources'] = resources
    self.ports = ports
    self.monitoring = monitoring


class NodeSAP(Node):
  """
  Class for SAP nodes in the NF-FG
  """

  def __init__ (self, id, name=None, ports):
    super(NodeInfra, self).__init__(id)
    self.name = name
    self.ports = ports


class NodeInfra(Node):
  """
  Class for infrastructure nodes in the NF-FG
  """

  def __init__ (self, id, name=None, domain=None, infra_type=BISBIS, 
                resources, ports):
    super(NodeInfra, self).__init__(id)
    self.name = name
    self.domain = domain
    self.type = infra_type
    self.resources = resources
    self.ports = ports


class Edge(object):
  """
  Class for different types of edges in the NF-FG
  """

  def __init__ (self, id):
    super(Edge, self).__init__()
    self.id = id


class EdgeLink(Edge):
  """
  Class for static and dynamic links in the NF-FG
  """

  def __init__ (self, id, src, dst, resources):
    super(Edge, self).__init__()
    self.id = id
    self.src = src # (node_id, port_id)
    self.dst = dst # (node_id, port_id)
    self.resources = resources


class EdgeSGLink(Edge):
  """
  Class for links of SG
  """

  def __init__ (self, id, src, dst, flowclass):
    super(Edge, self).__init__()
    self.id = id
    self.src = src # (node_id, port_id)
    self.dst = dst # (node_id, port_id)
    self.flowclass = flowclass # flowrule without action


class EdgeReq(Edge):
  """
  Class for requirements between arbitrary NF modes
  """

  def __init__ (self, id, src, dst, reqs):
    super(Edge, self).__init__()
    self.id = id
    self.src = src # (node_id, port_id)
    self.dst = dst # (node_id, port_id)
    self.reqs = reqs
