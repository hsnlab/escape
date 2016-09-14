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

from MappingAlgorithms import MAP
from UnifyExceptionTypes import *
from escape import CONFIG
from escape.nffg_lib.nffg import NFFG
from escape.service import log as log, LAYER_NAME
from escape.util.mapping import AbstractMappingStrategy, AbstractMapper
from escape.util.misc import call_as_coop_task, VERBOSE
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
    log.info("Invoke mapping algorithm: %s - request: %s resource: %s" %
             (cls.__name__, graph, resource))
    if graph is None:
      log.error("Missing request NFFG! Abort mapping process...")
      return
    if resource is None:
      log.error("Missing resource NFFG! Abort mapping process...")
      return
    try:
      mapper_params = CONFIG.get_mapping_config(layer=LAYER_NAME)
      if 'mode' in mapper_params and mapper_params['mode']:
        mapping_mode = mapper_params['mode']
        log.debug("Setup mapping mode from configuration: %s" % mapping_mode)
      elif graph.mode:
        mapping_mode = graph.mode
        log.debug("Setup mapping mode based on request: %s" % mapping_mode)
      else:
        mapping_mode = None
      mapped_nffg = MAP(request=graph.copy(),
                        network=resource.copy(),
                        mode=mapping_mode,
                        **mapper_params)
      # Set mapped NFFG id for original SG request tracking
      mapped_nffg.id = graph.id
      mapped_nffg.name = graph.name + "-sas-mapped"
    except MappingException as e:
      log.error("Got exception during the mapping process! Cause:\n%s" % e.msg)
      log.warning("Mapping algorithm on %s isaborted!" % graph)
      return
    except BadInputException as e:
      log.error("Mapping algorithm refuse given input! Cause:\n%s" % e.msg)
      log.warning("Mapping algorithm on %s is aborted!" % graph)
      return
    except InternalAlgorithmException as e:
      log.critical(
        "Mapping algorithm fails due to implementation error or conceptual "
        "error! Cause:\n%s" % e.msg)
      log.warning("Mapping algorithm on %s is aborted!" % graph)
      return
    except:
      log.exception("Got unexpected error during mapping process!")
      return
    log.info("Mapping algorithm: %s is finished on SG: %s" %
             (cls.__name__, graph))
    return mapped_nffg


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

  def __init__ (self, strategy=None):
    """
    Init Service mapper.

    :return: None
    """
    super(ServiceGraphMapper, self).__init__(LAYER_NAME, strategy)
    log.debug("Init %s with strategy: %s" % (
      self.__class__.__name__, self.strategy.__name__))

  def _perform_mapping (self, input_graph, resource_view):
    """
    Orchestrate mapping of given service graph on given virtual resource.

    :param input_graph: Service Graph
    :type input_graph: :any:`NFFG`
    :param resource_view: virtual resource view
    :param resource_view: :any:`AbstractVirtualizer`
    :return: Network Function Forwarding Graph
    :rtype: :any:`NFFG`
    """
    if input_graph is None:
      log.error("Missing service request information! Abort mapping process!")
      return None
    log.debug("Request %s to launch orchestration on SG: %s with View: %s" % (
      self.__class__.__name__, input_graph, resource_view))
    # Steps before mapping (optional)
    log.debug("Request resource info from layer virtualizer...")
    virt_resource = resource_view.get_resource_info()
    if virt_resource is None:
      log.error("Missing resource information! Abort mapping process!")
      return None
    # log a warning if resource is empty --> possibly mapping will be failed
    if virt_resource.is_empty():
      log.warning("Resource information is empty!")
    # Log verbose resource view if it is exist
    log.log(VERBOSE, "Service layer resource graph:\n%s" % virt_resource.dump())
    # resource_view.sanity_check(input_graph)
    # Check if the mapping algorithm is enabled
    if not CONFIG.get_mapping_enabled(LAYER_NAME):
      log.warning(
        "Mapping algorithm in Layer: %s is disabled! Skip mapping step and "
        "forward service request to lower layer..." % LAYER_NAME)
      input_graph.status = NFFG.MAP_STATUS_SKIPPED
      log.debug("Mark NFFG status: %s!" % input_graph.status)
      return input_graph
    # Run actual mapping algorithm
    if self._threaded:
      # Schedule a microtask which run mapping algorithm in a Python thread
      log.info(
        "Schedule mapping algorithm: %s in a worker thread" %
        self.strategy.__name__)
      call_as_coop_task(self._start_mapping, graph=input_graph,
                        resource=virt_resource)
      log.info("SG: %s orchestration is finished by %s" % (
        input_graph, self.__class__.__name__))
      # Return with None
      return None
    else:
      mapped_nffg = self.strategy.map(graph=input_graph, resource=virt_resource)
      # Steps after mapping (optional) if the mapping was not threaded
      if mapped_nffg is None:
        log.error("Mapping process is failed! Abort orchestration process.")
      else:
        log.info("SG: %s orchestration is finished by %s successfully!" % (
          input_graph, self.__class__.__name__))
      return mapped_nffg

  def _mapping_finished (self, mapped_nffg):
    """
    Called from a separate thread when the mapping process is finished.

    :param mapped_nffg: generated NF-FG
    :type mapped_nffg: :any:`NFFG`
    :return: None
    """
    # TODO - rethink threaded/non-threaded function call paths to call port
    # mapping functions in a joint way only once
    if mapped_nffg is None:
      log.error("Mapping process is failed! Abort orchestration process.")
      return None
    # Steps after mapping (optional) if the mapping was threaded
    log.debug("Inform SAS layer API that SG mapping has been finished...")
    self.raiseEventNoErrors(SGMappingFinishedEvent, mapped_nffg)
