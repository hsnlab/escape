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
Contains classes which implement :any:`NFFG` mapping functionality.
"""
import sys

from MappingAlgorithms import MAP
from UnifyExceptionTypes import MappingException, BadInputException, \
  InternalAlgorithmException
from escape import CONFIG
from escape.util.mapping import AbstractMapper, AbstractMappingStrategy
from escape.orchest import log as log, LAYER_NAME
from escape.util.misc import call_as_coop_task
from pox.lib.revent.revent import Event


class ESCAPEMappingStrategy(AbstractMappingStrategy):
  """
  Implement a strategy to map initial :any:`NFFG` into extended :any:`NFFG`.
  """

  def __init__ (self):
    """
    Init
    """
    super(ESCAPEMappingStrategy, self).__init__()

  @classmethod
  def map (cls, graph, resource):
    """
    Default mapping algorithm of ESCAPEv2.

    :param graph: Network Function forwarding Graph
    :type graph: :any:`NFFG`
    :param resource: global virtual resource info
    :type resource: :any:`NFFG`
    :return: mapped Network Function Forwarding Graph
    :rtype: :any:`NFFG`
    """
    log.debug("Invoke mapping algorithm: %s - request: %s resource: %s" % (
      cls.__name__, graph, resource))
    try:
      mapped_nffg = MAP(request=graph.copy(), network=resource.copy())
      # Set mapped NFFG id for original SG request tracking
      mapped_nffg.id = graph.id
      mapped_nffg.name = graph.name + "-ros-mapped"
    except MappingException as e:
      log.error("Got exception during the mapping process! Cause: %s" % e)
      log.warning("Mapping algorithm on %s aborted!" % graph)
      return
    except BadInputException as e:
      log.error("Mapping algorithm refuse given input! Cause: %s" % e)
      log.warning("Mapping algorithm on %s aborted!" % graph)
      return
    except InternalAlgorithmException as e:
      log.critical(
        "Mapping algorithm fails due to implementation error or conceptual "
        "error! Cause: %s" % e)
      log.warning("Mapping algorithm on %s aborted!" % graph)
      raise
    except:
      log.error("Got unexpected error during mapping process! Cause: %s" %
                sys.exc_info()[0])
      raise
    log.debug(
      "Mapping algorithm: %s is finished on NF-FG: %s" % (cls.__name__, graph))
    return mapped_nffg


class NFFGMappingFinishedEvent(Event):
  """
  Event for signaling the end of NF-FG mapping.
  """

  def __init__ (self, nffg):
    """
    Init.

    :param nffg: NF-FG need to be installed
    :type nffg: :any:`NFFG`
    """
    super(NFFGMappingFinishedEvent, self).__init__()
    self.nffg = nffg


class ResourceOrchestrationMapper(AbstractMapper):
  """
  Helper class for mapping NF-FG on global virtual view.
  """
  # Events raised by this class
  _eventMixin_events = {NFFGMappingFinishedEvent}
  # Default Mapper class as a fallback mapper
  DEFAULT_STRATEGY = ESCAPEMappingStrategy

  def __init__ (self, strategy=None):
    """
    Init Resource Orchestrator mapper.

    :return: None
    """
    super(ResourceOrchestrationMapper, self).__init__(LAYER_NAME, strategy)
    log.debug("Init %s with strategy: %s" % (
      self.__class__.__name__, self.strategy.__name__))

  def orchestrate (self, input_graph, resource_view):
    """
    Orchestrate mapping of given NF-FG on given global resource.

    :param input_graph: Network Function Forwarding Graph
    :type input_graph: :any:`NFFG`
    :param resource_view: global resource view
    :type resource_view: :any:`DomainVirtualizer`
    :return: mapped Network Function Forwarding Graph
    :rtype: :any:`NFFG`
    """
    log.debug("Request %s to launch orchestration on NF-FG: %s with View: "
              "%s" % (self.__class__.__name__, input_graph, resource_view))
    # Steps before mapping (optional)
    # log.debug("Request global resource info...")
    virt_resource = resource_view.get_resource_info()
    # Check if the mapping algorithm is enabled
    if not CONFIG.get_mapping_enabled(LAYER_NAME):
      log.warning(
        "Mapping algorithm in Layer: %s is disabled! Skip mapping step and "
        "return resource info..." % LAYER_NAME)
      # virt_resource.id = input_graph.id
      # return virt_resource
      # Send request forward (probably to Remote ESCAPE)
      return input_graph
    # Run actual mapping algorithm
    if self._threaded:
      # Schedule a microtask which run mapping algorithm in a Python thread
      log.info(
        "Schedule mapping algorithm: %s in a worker thread" %
        self.strategy.__name__)
      call_as_coop_task(self._start_mapping, graph=input_graph,
                        resource=virt_resource)
      log.info("NF-FG: %s orchestration is finished by %s" % (
        input_graph, self.__class__.__name__))
    else:
      mapped_nffg = self.strategy.map(graph=input_graph, resource=virt_resource)
      # Steps after mapping (optional)
      log.info("NF-FG: %s orchestration is finished by %s" % (
        input_graph, self.__class__.__name__))
      return mapped_nffg

  def _mapping_finished (self, nffg):
    """
    Called from a separate thread when the mapping process is finished.

    :param nffg: mapped NF-FG
    :type nffg: :any:`NFFG`
    :return: None
    """
    log.debug("Inform actual layer API that NFFG mapping has been finished...")
    self.raiseEventNoErrors(NFFGMappingFinishedEvent, nffg)
