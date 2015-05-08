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
Contains classes which implement :class:`NFFG <escape.util.nffg.NFFG>`
mapping functionality

:class:`ESCAPEMappingStrategy` implements a default :class:`NFFG
<escape.util.nffg.NFFG>` mapping algorithm of ESCAPEv2

:class:`ResourceOrchestrationMapper` perform the supplementary tasks for
:class:`NFFG <escape.util.nffg.NFFG>` mapping
"""

from escape.util.mapping import AbstractMapper, AbstractMappingStrategy
from escape.orchest import log as log, LAYER_NAME
from escape.util.misc import call_as_coop_task
from pox.lib.revent.revent import Event


class ESCAPEMappingStrategy(AbstractMappingStrategy):
  """
  Implement a strategy to map initial :class:`NFFG <escape.util.nffg.NFFG>`
  into extended :class:`NFFG <escape.util.nffg.NFFG>`
  """

  def __init__ (self):
    """
    Init
    """
    super(ESCAPEMappingStrategy, self).__init__()

  @classmethod
  def map (cls, graph, resource):
    """
    Default mapping algorithm of ESCAPEv2

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


class NFFGMappingFinishedEvent(Event):
  """
  Event for signaling the end of NF-FG mapping
  """

  def __init__ (self, nffg):
    """
    Init

    :param nffg: NF-FG need to be installed
    :type nffg: NFFG
    """
    super(NFFGMappingFinishedEvent, self).__init__()
    self.nffg = nffg


class ResourceOrchestrationMapper(AbstractMapper):
  """
  Helper class for mapping NF-FG on global virtual view
  """
  # Events raised by this class
  _eventMixin_events = {NFFGMappingFinishedEvent}

  def __init__ (self):
    """
    Init Resource Orchestrator mapper

    :return: None
    """
    super(ResourceOrchestrationMapper, self).__init__(LAYER_NAME)
    log.debug("Init %s with strategy: %s" % (
      self.__class__.__name__, self.strategy.__name__))

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
    if self._threaded:
      # Schedule a microtask which run mapping algorithm in a Python thread
      log.info(
        "Schedule mapping algorithm: %s in a worker thread" %
          self.strategy.__name__)
      call_as_coop_task(self._start_mapping, graph=input_graph,
                        resource=virt_resource)
      log.info("NF-FG(%s) orchestration is finished by %s" % (
        input_graph.id, self.__class__.__name__))
    else:
      mapped_nffg = self.strategy.map(graph=input_graph, resource=virt_resource)
      # Steps after mapping (optional)
      log.info("NF-FG(%s) orchestration is finished by %s" % (
        input_graph.id, self.__class__.__name__))
      return mapped_nffg

  def _mapping_finished (self, nffg):
    """
    Called from a separate thread when the mapping process is finished

    :param nffg: mapped NF-FG
    :type nffg: NFFG
    :return: None
    """
    log.debug("Inform actual layer API that NFFG mapping has been finished...")
    self.raiseEventNoErrors(NFFGMappingFinishedEvent, nffg)