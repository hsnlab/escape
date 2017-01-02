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
import cProfile
import pstats

from MappingAlgorithms import MAP
from UnifyExceptionTypes import *
from escape import CONFIG
from escape.nffg_lib.nffg import NFFG
from escape.orchest import log as log, LAYER_NAME
from escape.util.mapping import AbstractMapper, AbstractMappingStrategy
from escape.util.misc import call_as_coop_task, VERBOSE
from pox.lib.revent.revent import Event


class ESCAPEMappingStrategy(AbstractMappingStrategy):
  """
  Implement a strategy to map initial :any:`NFFG` into extended :any:`NFFG`.
  """
  LAYER_NAME = LAYER_NAME

  def __init__ (self):
    """
    Init

    :return: None
    """
    super(ESCAPEMappingStrategy, self).__init__()

  @classmethod
  def call_mapping_algorithm (cls, request, topology, **params):
    """
    Template function to call the main algorithm.
    Provide an easy way to change the algorithm easily in child classes.

    Contains profiling to measure basic performance of the algorithm.

    :param request: request graph
    :type request: :any:`NFFG`
    :param topology: topology graph
    :type topology: :any:`NFFG`
    :param params: additional mapping parameters
    :type params: dict
    :return: mapping result
    :rtype: :any:`NFFG`
    """
    profile = cProfile.Profile(builtins=False, subcalls=False)
    try:
      profile.enable()
      res = MAP(request=request, network=topology, **params)
    finally:
      profile.disable()
      cls.__process_profile_result(profile=profile)
      profile.create_stats()
    return res

  @classmethod
  def __process_profile_result (cls, profile):
    """
    Process profiling data.

    :param profile: main Profile object
    :type profile: cProfile.Profile
    :return: None
    """
    profile.create_stats()
    stat = pstats.Stats(profile)
    log.info("Mapping algorithm finished with %d function calls "
              "(%d primitive calls) in %.3f seconds!" %
              (stat.total_calls, stat.prim_calls, stat.total_tt))

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
    log.info("Invoke mapping algorithm: %s - request: %s resource: %s" % (
      cls.__name__, graph, resource))
    if graph is None:
      log.error("Missing request NFFG! Abort mapping process...")
      return
    if resource is None:
      log.error("Missing resource NFFG! Abort mapping process...")
      return
    try:
      # Copy mapping config
      mapper_params = CONFIG.get_mapping_config(layer=cls.LAYER_NAME).copy()
      if 'mode' in mapper_params and mapper_params['mode']:
        log.debug("Setup mapping mode from configuration: %s" %
                  mapper_params['mode'])
      elif graph.mode:
        mapper_params['mode'] = graph.mode
        log.debug("Setup mapping mode based on request: %s" %
                  mapper_params['mode'])
      mapped_nffg = cls.call_mapping_algorithm(request=graph.copy(),
                                               topology=resource.copy(),
                                               **mapper_params)
      # Set mapped NFFG id for original SG request tracking
      log.debug("Move request metadata into mapping result...")
      mapped_nffg.id = graph.id
      mapped_nffg.name = "%s-%s-mapped" % (graph.name, cls.LAYER_NAME)
      # Explicitly copy metadata
      mapped_nffg.metadata = graph.metadata.copy()
      # Explicit copy of SAP data
      for sap in graph.saps:
        if sap.id in mapped_nffg:
          mapped_nffg[sap.id].metadata = graph[sap.id].metadata.copy()
      log.info("Mapping algorithm: %s is finished on NF-FG: %s" %
               (cls.__name__, mapped_nffg))
      return mapped_nffg
    except MappingException as e:
      log.error(
        "Mapping algorithm unable to map given request! Cause:\n%s" % e.msg)
      log.warning("Mapping algorithm on %s is aborted!" % graph)
      return
    except BadInputException as e:
      log.error("Mapping algorithm refuse given input! Cause:\n%s" % e.msg)
      log.warning("Mapping algorithm on %s is aborted!" % graph)
      return
    except InternalAlgorithmException as e:
      log.critical(
        "Mapping algorithm fails due to internal error! Cause:\n%s" % e.msg)
      log.warning("Mapping algorithm on %s is aborted!" % graph)
      return
    except:
      log.exception("Got unexpected error during mapping process!")


class NFFGMappingFinishedEvent(Event):
  """
  Event for signaling the end of NF-FG mapping.
  """

  def __init__ (self, nffg):
    """
    Init.

    :param nffg: NF-FG need to be installed
    :type nffg: :any:`NFFG`
    :return: None
    """
    super(NFFGMappingFinishedEvent, self).__init__()
    self.nffg = nffg


class ResourceOrchestrationMapper(AbstractMapper):
  """
  Helper class for mapping NF-FG on global virtual view.
  """
  # Events raised by this class
  _eventMixin_events = {NFFGMappingFinishedEvent}
  """Events raised by this class"""
  # Default Mapper class as a fallback mapper
  DEFAULT_STRATEGY = ESCAPEMappingStrategy
  """Default Mapper class as a fallback mapper"""

  def __init__ (self, strategy=None):
    """
    Init Resource Orchestrator mapper.

    :return: None
    """
    super(ResourceOrchestrationMapper, self).__init__(layer_name=LAYER_NAME,
                                                      strategy=strategy)
    log.debug("Init %s with strategy: %s" % (
      self.__class__.__name__, self.strategy.__name__))

  def _perform_mapping (self, input_graph, resource_view):
    """
    Orchestrate mapping of given NF-FG on given global resource.

    :param input_graph: Network Function Forwarding Graph
    :type input_graph: :any:`NFFG`
    :param resource_view: global resource view
    :type resource_view: :any:`DomainVirtualizer`
    :return: mapped Network Function Forwarding Graph
    :rtype: :any:`NFFG`
    """
    if input_graph is None:
      log.error("Missing mapping request information! Abort mapping process!")
      return None
    log.debug("Request %s to launch orchestration on NF-FG: %s with View: "
              "%s" % (self.__class__.__name__, input_graph, resource_view))
    # Steps before mapping (optional)
    log.debug("Request global resource info...")
    virt_resource = resource_view.get_resource_info()
    if virt_resource is None:
      log.error("Missing resource information! Abort mapping process!")
      return None
    # log a warning if resource is empty --> possibly mapping will be failed
    if virt_resource.is_empty():
      log.warning("Resource information is empty!")
    # Log verbose resource view if it is exist
    log.log(VERBOSE, "Orchestration Layer resource graph:\n%s" %
            virt_resource.dump())
    # Check if the mapping algorithm is enabled
    if not CONFIG.get_mapping_enabled(LAYER_NAME):
      log.warning("Mapping algorithm in Layer: %s is disabled! "
                  "Skip mapping step and return service request "
                  "to lower layer..." % LAYER_NAME)
      # virt_resource.id = input_graph.id
      # return virt_resource
      # Send request forward (probably to Remote ESCAPE)
      input_graph.status = NFFG.MAP_STATUS_SKIPPED
      log.debug("Mark NFFG status: %s!" % input_graph.status)
      return input_graph
    # Run actual mapping algorithm
    if self._threaded:
      # Schedule a microtask which run mapping algorithm in a Python thread
      log.info("Schedule mapping algorithm: %s in a worker thread" %
               self.strategy.__name__)
      call_as_coop_task(self._start_mapping, graph=input_graph,
                        resource=virt_resource)
      log.info("NF-FG: %s orchestration is finished by %s" % (
        input_graph, self.__class__.__name__))
      # Return with None
      return None
    else:
      mapped_nffg = self.strategy.map(graph=input_graph, resource=virt_resource)
      if mapped_nffg is None:
        log.error("Mapping process is failed! Abort orchestration process.")
      else:
        # Steps after mapping (optional)
        log.info("NF-FG: %s orchestration is finished by %s successfully!" % (
          input_graph, self.__class__.__name__))
      return mapped_nffg

  def _mapping_finished (self, mapped_nffg):
    """
    Called from a separate thread when the mapping process is finished.

    :param mapped_nffg: mapped NF-FG
    :type mapped_nffg: :any:`NFFG`
    :return: None
    """
    # TODO - rethink threaded/non-threaded function call paths to call port
    # mapping functions in a joint way only once
    if mapped_nffg is None:
      log.error("Mapping process is failed! Abort orchestration process.")
      return None
    # Steps after mapping (optional) if the mapping was threaded
    log.debug("Inform actual layer API that NFFG mapping has been finished...")
    self.raiseEventNoErrors(NFFGMappingFinishedEvent, mapped_nffg)
