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
from escape.util.mapping import AbstractMappingStrategy, AbstractMapper
from escape.service import log as log
from escape import CONFIG


class DefaultServiceMappingStrategy(AbstractMappingStrategy):
  """
  Mapping class which maps given Service Graph into a single BiS-BiS
  """

  def __init__ (self):
    """
    Init
    """
    super(DefaultServiceMappingStrategy, self).__init__()

  @classmethod
  def map (cls, graph, resource):
    """
    Default mapping algorithm which maps given Service Graph on one BiS-BiS

    :param graph: Service Graph
    :type graph: NFFG
    :param resource: virtual resource
    :type resource: NFFG
    :return: Network Function Forwarding Graph
    :rtype: NFFG
    """
    log.debug(
      "Invoke mapping algorithm: %s on SG(%s)" % (cls.__name__, graph.id))
    # TODO implement
    log.debug(
      "Mapping algorithm: %s is finished on SG(%s)" % (cls.__name__, graph.id))
    # for testing return with graph
    return graph


class ServiceGraphMapper(AbstractMapper):
  """
  Helper class for mapping Service Graph to NF-FG
  """

  def __init__ (self, strategy=DefaultServiceMappingStrategy):
    """
    Init mapper class

    :param strategy: mapping strategy (default DefaultServiceMappingStrategy)
    :type strategy: AbstractMappingStrategy
    :return: None
    """
    if hasattr(CONFIG['SAS'], 'STRATEGY'):
      if issubclass(CONFIG['SAS']['STATEGY'], AbstractMappingStrategy):
        try:
          strategy = getattr(self.__module__, CONFIG['SAS']['STATEGY'])
        except AttributeError:
          log.warning(
            "Mapping strategy: %s is not found in module: %s, fall back to "
            "%s" % (CONFIG['SAS']['STATEGY'], self.__module__,
                    strategy.__class__.__name__))
      else:
        log.warning(
          "SAS mapping strategy is not subclass of AbstractMappingStrategy, "
          "fall back to %s" % strategy.__class__.__name__)
    super(ServiceGraphMapper, self).__init__(strategy)
    log.debug("Init %s with strategy: %s" % (
      self.__class__.__name__, strategy.__name__))

  def orchestrate (self, input_graph, resource_view):
    """
    Orchestrate mapping of given service graph on given virtual resource

    :param input_graph: Service Graph
    :type input_graph: NFFG
    :param resource_view: virtual resource view
    :param resource_view: ESCAPEVirtualizer
    :return: Network Function Forwarding Graph
    :rtype: NFFG
    """
    log.debug("Request %s to launch orchestration on SG(%s)..." % (
      self.__class__.__name__, input_graph.id))
    # Steps before mapping (optional)
    # Run actual mapping algorithm
    nffg = self.strategy.map(graph=input_graph,
      resource=resource_view.get_resource_info())
    # Steps after mapping (optional)
    log.info("SG(%s) orchestration is finished by %s" % (
      input_graph.id, self.__class__.__name__))
    return nffg

