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
from escape.orchest import log as log


class AbstractMappingStrategy(object):
  """
  Abstract class for the mapping strategies

  Follow the Strategy design pattern
  """

  def __init__ (self):
    super(AbstractMappingStrategy, self).__init__()

  @classmethod
  def map (cls, graph, resource):
    raise NotImplementedError("Derived class must override this function!")


class ESCAPEMappingStrategy(AbstractMappingStrategy):
  """
  Implement a strategy to map initial NFFG into extNFFG
  """

  def __init__ (self):
    super(ESCAPEMappingStrategy, self).__init__()

  @classmethod
  def map (cls, graph, resource):
    """
    Default mapping algorithm of ESCAPE

    :param graph: Network Function forwarding Graph
    :param resource: global virtual resource
    :return: mapped Network Fuction Forwarding Graph
    """
    log.debug(
      "Invoke mapping algorithm: %s on NF-FG(%s)" % (cls.__name__, graph.id))
    # TODO implement
    log.debug("Mapping algorithm: %s is finished on NF-FG(%s)" % (
      cls.__name__, graph.id))
    # for testing return with graph
    return graph

