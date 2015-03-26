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
from escape.orchest.mapping_strategy import ESCAPEMappingStrategy
from escape.orchest import log as log


class AbstractMapper(object):
  """
  Abstract class for graph mapping function

  Contain common functions and initialization
  """

  def __init__ (self, strategy):
    super(AbstractMapper, self).__init__()
    self.strategy = strategy

  def orchestrate (self, input_graph, resource_view):
    """
    Abstract function for wrapping optional steps connected to orchestration
    Implemented function call the mapping algorithm

    :param input_graph: graph representation which need to be mapped
    :type input_graph: NFFG
    :param resource_view: resource information
    :type resource_view: AbstractVirtualizer
    :return: mapped graph
    :rtype: NFFG
    """
    raise NotImplementedError("Derived class must override this function!")


class ResourceOrchestrationMapper(AbstractMapper):
  """
  Helper class for mapping NF-FG on global virtual view
  """

  def __init__ (self, strategy=ESCAPEMappingStrategy):
    super(ResourceOrchestrationMapper, self).__init__(strategy)
    log.debug("Init %s with strategy: %s" % (
      self.__class__.__name__, strategy.__name__))

  def orchestrate (self, input_graph, resource_view):
    """
    Orchestrate mapping of given NF-FG on given global resource

    :param input_graph: Network Function Forwarding Graph
    :type input_graph: NFFG
    :param resource_view: global resource view
    :type resource_view: DomainVirtualizer
    :return: mapped Network Function Forwarding Graph
    :rtype: NFFG
    """
    log.debug("Request %s to lauch orchestration on NF-FG(%s)..." % (
      self.__class__.__name__, input_graph.id))
    # Steps before mapping (optional)
    # Run actual mapping algorithm
    mapped_nffg = self.strategy.map(graph=input_graph,
                                    resource=resource_view.get_resource_info())
    # Steps after mapping (optional)
    log.info("Nf-FG(%s) orchestration is finished by %s" % (
      input_graph.id, self.__class__.__name__))
    return mapped_nffg