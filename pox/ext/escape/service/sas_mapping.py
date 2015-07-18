# Copyright 2015 Janos Czentye <czentye@tmit.bme.hu>
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
Contains classes which implement SG mapping functionality.
"""

from escape.util.mapping import AbstractMappingStrategy, AbstractMapper
from escape.service import log as log, LAYER_NAME
from escape.util.misc import call_as_coop_task
from pox.lib.revent.revent import Event


class DefaultServiceMappingStrategy(AbstractMappingStrategy):
  """
  Mapping class which maps given Service Graph into a single BiS-BiS.
  """

  def __init__ (self):
    """
    Init.
    """
    super(DefaultServiceMappingStrategy, self).__init__()

  @classmethod
  def map (cls, graph, resource):
    """
    Default mapping algorithm which maps given Service Graph on one BiS-BiS.

    :param graph: Service Graph
    :type graph: :any:`NFFG`
    :param resource: virtual resource
    :type resource: :any:`NFFG`
    :return: Network Function Forwarding Graph
    :rtype: :any:`NFFG`
    """
    log.debug(
      "Invoke mapping algorithm: %s on SG(%s)" % (cls.__name__, graph.id))
    # TODO implement
    log.debug(
      "Mapping algorithm: %s is finished on SG(%s)" % (cls.__name__, graph.id))
    # for testing return with graph
    return graph


class SGMappingFinishedEvent(Event):
  """
  Event for signaling the end of SG mapping.
  """

  def __init__ (self, nffg):
    """
    Init.

    :param nffg: NF-FG need to be initiated
    :type nffg: :any:`NFFG`
    """
    super(SGMappingFinishedEvent, self).__init__()
    self.nffg = nffg


class ServiceGraphMapper(AbstractMapper):
  """
  Helper class for mapping Service Graph to NF-FG.
  """
  # Events raised by this class
  _eventMixin_events = {SGMappingFinishedEvent}
  # Default Strategy class as a fallback strategy
  DEFAULT_STRATEGY = DefaultServiceMappingStrategy

  def __init__ (self):
    """
    Init Service mapper.

    :return: None
    """
    super(ServiceGraphMapper, self).__init__(LAYER_NAME)
    log.debug("Init %s with strategy: %s" % (
      self.__class__.__name__, self.strategy.__name__))

  def orchestrate (self, input_graph, resource_view):
    """
    Orchestrate mapping of given service graph on given virtual resource.

    :param input_graph: Service Graph
    :type input_graph: :any:`NFFG`
    :param resource_view: virtual resource view
    :param resource_view: :any:`ESCAPEVirtualizer`
    :return: Network Function Forwarding Graph
    :rtype: :any:`NFFG`
    """
    log.debug("Request %s to launch orchestration on SG(%s)..." % (
      self.__class__.__name__, input_graph.id))
    # Steps before mapping (optional)
    virt_resource = resource_view.get_resource_info()
    resource_view.sanity_check(input_graph)
    # Run actual mapping algorithm
    if self._threaded:
      # Schedule a microtask which run mapping algorithm in a Python thread
      log.info(
        "Schedule mapping algorithm: %s in a worker thread" %
        self.strategy.__name__)
      call_as_coop_task(self._start_mapping, graph=input_graph,
                        resource=virt_resource)
      log.info("SG(%s) orchestration is finished by %s" % (
        input_graph.id, self.__class__.__name__))
    else:
      nffg = self.strategy.map(graph=input_graph, resource=virt_resource)
      # Steps after mapping (optional)
      log.info("SG(%s) orchestration is finished by %s" % (
        input_graph.id, self.__class__.__name__))
      return nffg

  def _mapping_finished (self, nffg):
    """
    Called from a separate thread when the mapping process is finished.

    :param nffg: generated NF-FG
    :type nffg: :any:`NFFG`
    :return: None
    """
    log.debug("Inform SAS layer API that SG mapping has been finished...")
    self.raiseEventNoErrors(SGMappingFinishedEvent, nffg)
