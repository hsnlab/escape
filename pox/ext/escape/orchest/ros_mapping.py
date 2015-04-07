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
from escape.util.mapping import AbstractMapper, AbstractMappingStrategy
from escape.orchest import log as log
from escape import CONFIG


class ESCAPEMappingStrategy(AbstractMappingStrategy):
  """
  Implement a strategy to map initial NFFG into extNFFG
  """

  def __init__ (self):
    """
    Init
    """
    super(ESCAPEMappingStrategy, self).__init__()

  @classmethod
  def map (cls, graph, resource):
    """
    Default mapping algorithm of ESCAPE

    :param graph: Network Function forwarding Graph
    :type graph: NFFG
    :param resource: global virtual resource info
    :type resource: NFFG
    :return: mapped Network Function Forwarding Graph
    :rtype: NFFG
    """
    log.debug(
      "Invoke mapping algorithm: %s on NF-FG(%s)" % (cls.__name__, graph.id))
    # TODO - implement algorithm here
    log.debug("Mapping algorithm: %s is finished on NF-FG(%s)" % (
      cls.__name__, graph.id))
    # for testing return with graph
    return graph


class ResourceOrchestrationMapper(AbstractMapper):
  """
  Helper class for mapping NF-FG on global virtual view
  """

  def __init__ (self, strategy=ESCAPEMappingStrategy):
    """
    Init mapper

    :param strategy: mapping strategy
    :type strategy: AbstractMappingStrategy (default ESCAPEMappingStrategy)
    :return: None
    """
    if hasattr(CONFIG['ROS'], 'STRATEGY'):
      if issubclass(CONFIG['ROS']['STATEGY'], AbstractMappingStrategy):
        try:
          strategy = getattr(self.__module__, CONFIG['ROS']['STATEGY'])
        except AttributeError:
          log.warning(
            "Mapping strategy: %s is not found in module: %s, fall back to "
            "%s" % (CONFIG['ROS']['STATEGY'], self.__module__,
                    strategy.__class__.__name__))
      else:
        log.warning(
          "ROS mapping strategy is not subclass of AbstractMappingStrategy, "
          "fall back to %s" % strategy.__class__.__name__)
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
    log.debug("Request %s to launch orchestration on NF-FG(%s)..." % (
      self.__class__.__name__, input_graph.id))
    # Steps before mapping (optional)
    virt_resource = resource_view.get_resource_info()
    # Run actual mapping algorithm
    mapped_nffg = self.strategy.map(graph=input_graph, resource=virt_resource)
    # Steps after mapping (optional)
    log.info("NF-FG(%s) orchestration is finished by %s" % (
      input_graph.id, self.__class__.__name__))
    return mapped_nffg