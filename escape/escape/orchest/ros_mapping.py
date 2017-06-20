# Copyright 2017 Janos Czentye
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
Contains classes which implement :class:`NFFG` mapping functionality.
"""
import cProfile
import pstats
import time

from alg1.MappingAlgorithms import MAP
from alg1.UnifyExceptionTypes import *
from escape.nffg_lib.nffg import NFFG
from escape.orchest import log as log, LAYER_NAME
from escape.util.config import CONFIG
from escape.util.mapping import AbstractMapper, AbstractMappingStrategy
from escape.util.misc import call_as_coop_task, VERBOSE
from escape.util.stat import stats
from pox.lib.revent.revent import Event


class ESCAPEMappingStrategy(AbstractMappingStrategy):
  """
  Implement a strategy to map initial :class:`NFFG` into extended :class:`NFFG`.
  """
  LAYER_NAME = LAYER_NAME

  def __init__ (self):
    """
    Init

    :return: None
    """
    super(ESCAPEMappingStrategy, self).__init__()

  @classmethod
  def call_mapping_algorithm (cls, request, topology, profiling=False,
                              stats_type=stats.TYPE_ORCHESTRATION_MAPPING,
                              stat_level=None, **params):
    """
    Template function to call the main algorithm.
    Provide an easy way to change the algorithm easily in child classes.

    Contains profiling to measure basic performance of the algorithm.

    :param request: request graph
    :type request: :class:`NFFG`
    :param topology: topology graph
    :type topology: :class:`NFFG`
    :param profiling: enables cProfile for mapping which bring big overhead
    :type profiling: bool
    :param params: additional mapping parameters
    :type params: dict
    :return: mapping result
    :rtype: :class:`NFFG`
    """
    log.debug("Call mapping algorithm with parameters: %s" % params)
    stat_level = stat_level if stat_level else cls.__name__
    stats.add_measurement_start_entry(type=stats_type, info=stat_level)
    try:
      if profiling:
        ret = cls.cprofiler_decorator(MAP, request, topology, **params)
      else:
        ret = cls.timer_decorator(MAP, request, topology, **params)
    finally:
      stats.add_measurement_end_entry(type=stats_type, info=stat_level)
    return ret

  @staticmethod
  def cprofiler_decorator (func, *args, **kwargs):
    profiler = cProfile.Profile(builtins=False, subcalls=False)
    try:
      profiler.enable()
      result = func(*args, **kwargs)
    finally:
      profiler.disable()
      profiler.create_stats()
      stat = pstats.Stats(profiler)
      log.info("Mapping algorithm finished with %d function calls "
               "(%d primitive calls) in %.3f seconds!" %
               (stat.total_calls, stat.prim_calls, stat.total_tt))
    return result

  @staticmethod
  def timer_decorator (func, *args, **kwargs):
    start = time.time()
    try:
      result = func(*args, **kwargs)
    finally:
      delta = time.time() - start
      log.info("Mapping algorithm finished in %.3f seconds!" % delta)
    return result

  @classmethod
  def map (cls, graph, resource, pre_state=None):
    """
    Default mapping algorithm of ESCAPEv2.

    :param graph: Network Function forwarding Graph
    :type graph: :class:`NFFG`
    :param resource: global virtual resource info
    :type resource: :class:`NFFG`
    :return: mapped Network Function Forwarding Graph
    :rtype: :class:`NFFG`
    """
    log.info("Invoke mapping algorithm: %s - request: %s resource: %s, "
             "previous state: %s" % (cls.__name__, graph, resource, pre_state))
    if graph is None:
      log.error("Missing request NFFG! Abort mapping process...")
      return
    if resource is None:
      log.error("Missing resource NFFG! Abort mapping process...")
      return
    try:
      # Run pre-mapping step to resolve target-less flowrules
      cls._resolve_external_ports(graph, resource)
      # Copy mapping config
      mapper_params = CONFIG.get_mapping_config(layer=cls.LAYER_NAME).copy()
      if 'mode' in mapper_params and mapper_params['mode']:
        log.debug("Setup mapping mode from configuration: %s" %
                  mapper_params['mode'])
      elif graph.mode:
        mapper_params['mode'] = graph.mode
        log.debug("Setup mapping mode based on request: %s" %
                  mapper_params['mode'])
      if CONFIG.get_trial_and_error(layer=cls.LAYER_NAME):
        log.info("Use 'trail and error' approach for mapping")
        mapper_params['return_mapping_state'] = True
        mapper_params['mapping_state'] = pre_state
      mapping_result = cls.call_mapping_algorithm(request=graph.copy(),
                                                  topology=resource.copy(),
                                                  **mapper_params)
      if isinstance(mapping_result, tuple or list):
        if len(mapping_result) != 2:
          log.error("Mapping result is invalid: %s" % repr(mapping_result))
          mapped_nffg = None
        else:
          mapped_nffg = mapping_result[0]
      else:
        mapped_nffg = mapping_result
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
      return mapping_result
    except MappingException as e:
      log.error(
        "Mapping algorithm unable to map given request! Cause:\n%s" % e.msg)
      log.error("Mapping algorithm on %s is aborted!" % graph)
      return
    except BadInputException as e:
      log.error("Mapping algorithm refuse given input! Cause:\n%s" % e.msg)
      log.error("Mapping algorithm on %s is aborted!" % graph)
      return
    except InternalAlgorithmException as e:
      log.critical(
        "Mapping algorithm fails due to internal error! Cause:\n%s" % e.msg)
      log.error("Mapping algorithm on %s is aborted!" % graph)
      return
    except:
      log.exception("Got unexpected error during mapping process!")

  @classmethod
  def _resolve_external_ports (cls, graph, resource):
    log.debug("Resolving optional external flowrules...")
    for infra in graph.infras:
      for port in infra.ports:
        if port.role != "EXTERNAL":
          continue
        log.debug("Detected external port: %s" % port)
        bb_node_id = port.properties["node"]
        bb_port_id = port.properties["port"]
        try:
          bb_port_id = int(bb_port_id)
        except ValueError:
          pass
        if bb_node_id not in resource:
          log.error("Missing external node: %s from resource!" % bb_node_id)
          continue
        bb_node = resource[bb_node_id]
        if bb_port_id not in bb_node.ports:
          log.error("Missing external port: %s from resource node: %s!"
                    % (bb_port_id, bb_node))
          continue
        bb_port = bb_node.ports[bb_port_id]
        if not bb_port.sap:
          log.error("No SAP tag was found in external port: %s" % bb_port)
          continue
        else:
          log.debug("Detected SAP tag: %s for external port: %s" % (bb_port.sap,
                                                                    bb_port_id))
        # Update SAP tag in request from resource port
        port.sap = bb_port.sap
        log.debug("Updated external SAP tag: %s" % port.sap)
        # Add ext SAP/SAP port/BB port based on external port to resource graph
        res_sap = resource.add_sap(id=port.id)
        res_sap_port = res_sap.add_port(id=port.id)
        res_sap_port.sap = bb_port.sap
        res_sap_port.role = port.role
        res_sap_port.properties.update(port.properties)
        res_port = bb_node.add_port(id=port.id)
        res_port.sap = bb_port.sap
        res_port.role = port.role
        res_port.properties.update(port.properties)
        resource.add_undirected_link(port1=res_port, port2=res_sap_port)
        log.debug("Created external resource SAP: %s" % res_sap)
        # Update SAP port in request as well
        ext_sap = graph[res_sap.id]
        ext_sap_port = ext_sap.ports.container[0]
        ext_sap_port.sap = res_sap_port.sap
        ext_sap_port.role = res_sap_port.role
        ext_sap_port.properties.update(res_sap_port.properties)
        log.debug("Updated external SAP: %s" % ext_sap)


class NFFGMappingFinishedEvent(Event):
  """
  Event for signaling the end of NF-FG mapping.
  """

  def __init__ (self, nffg):
    """
    Init.

    :param nffg: NF-FG need to be installed
    :type nffg: :class:`NFFG`
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

  def __init__ (self, strategy=None, mapping_state=None):
    """
    Init Resource Orchestrator mapper.

    :return: None
    """
    super(ResourceOrchestrationMapper, self).__init__(layer_name=LAYER_NAME,
                                                      strategy=strategy)
    log.debug("Init %s with strategy: %s" % (
      self.__class__.__name__, self.strategy.__name__))
    self.last_mapping_state = mapping_state

  def _perform_mapping (self, input_graph, resource_view, continued=False):
    """
    Orchestrate mapping of given NF-FG on given global resource.

    :param input_graph: Network Function Forwarding Graph
    :type input_graph: :class:`NFFG`
    :param resource_view: global resource view
    :type resource_view: :any:`DomainVirtualizer`
    :return: mapped Network Function Forwarding Graph
    :rtype: :class:`NFFG`
    """
    if input_graph is None:
      log.error("Missing mapping request information! Abort mapping process!")
      return None
    log.debug("Request %s to launch orchestration on NF-FG: %s with View: "
              "%s, continued remap: %s" % (self.__class__.__name__,
                                           input_graph, resource_view,
                                           continued))
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
      state = self.last_mapping_state if continued else None
      mapping_result = self.strategy.map(graph=input_graph,
                                         resource=virt_resource,
                                         pre_state=state)
      if isinstance(mapping_result, tuple or list):
        if len(mapping_result) != 2:
          log.error("Mapping result is invalid: %s" % repr(mapping_result))
          mapped_nffg = None
        else:
          mapped_nffg = mapping_result[0]
          self.last_mapping_state = mapping_result[1]
          log.debug(
            "Cache returned mapping state: %s" % self.last_mapping_state)
      else:
        mapped_nffg = mapping_result
      # Check error result
      if mapped_nffg is None:
        log.error("Mapping process is failed! Abort orchestration process.")
      else:
        # Steps after mapping (optional)
        log.info("NF-FG: %s orchestration is finished by %s successfully!" % (
          input_graph, self.__class__.__name__))
      log.debug("Last mapping state: %s" % self.last_mapping_state)
      return mapped_nffg

  def _mapping_finished (self, mapped_nffg):
    """
    Called from a separate thread when the mapping process is finished.

    :param mapped_nffg: mapped NF-FG
    :type mapped_nffg: :class:`NFFG`
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
