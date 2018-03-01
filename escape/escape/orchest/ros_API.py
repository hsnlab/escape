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
Implements the platform and POX dependent logic for the Resource Orchestration
Sublayer.
"""
import httplib
import pprint

from escape.adapt.adaptation import InfoRequestFinishedEvent
from escape.api.rest_API import RESTAPIManager
from escape.nffg_lib.nffg import NFFG
from escape.nffg_lib.nffg import NFFGToolBox
from escape.orchest import LAYER_NAME  # Orchestration layer logger
from escape.orchest import log as log
from escape.orchest.ros_orchestration import ResourceOrchestrator
from escape.util.api import AbstractAPI, RequestStatus, \
  RequestScheduler
from escape.util.config import CONFIG
from escape.util.domain import BaseResultEvent
from escape.util.mapping import ProcessorError
from escape.util.misc import VERBOSE, schedule_as_coop_task, quit_with_error
from escape.util.stat import stats
from pox.lib.revent.revent import Event
from virtualizer import Virtualizer
from virtualizer_info import Info
from virtualizer_mappings import Mappings


class InstallNFFGEvent(Event):
  """
  Event for passing mapped :class:`NFFG` to Controller
  Adaptation Sublayer.
  """

  def __init__ (self, mapped_nffg, original_request=None):
    """
    Init

    :param mapped_nffg: NF-FG graph need to be installed
    :type mapped_nffg: :class:`NFFG`
    :return: None
    """
    super(InstallNFFGEvent, self).__init__()
    self.mapped_nffg = mapped_nffg
    self.original_request = original_request
    stats.add_measurement_end_entry(type=stats.TYPE_ORCHESTRATION,
                                    info=LAYER_NAME)


class VirtResInfoEvent(Event):
  """
  Event for sending back requested Virtual view an a specific Virtualizer.
  """

  def __init__ (self, virtualizer):
    """
    Init.

    :param virtualizer: virtual resource info
    :type virtualizer: :any:`AbstractVirtualizer`
    :return: None
    """
    super(VirtResInfoEvent, self).__init__()
    self.virtualizer = virtualizer


class GetGlobalResInfoEvent(Event):
  """
  Event for requesting :class:`DomainVirtualizer` from CAS.
  """
  pass


class CollectMonitoringDataEvent(Event):
  """
  Event for sending Info request to CAS.
  """

  def __init__ (self, info, id):
    """
    Init.

    :param info: Info structure
    :type info: :class:`Virtualizer`
    :param id: unique id
    :type id: str or int
    """
    super(CollectMonitoringDataEvent, self).__init__()
    self.info = info
    self.id = id


class InstantiationFinishedEvent(BaseResultEvent):
  """
  Event for signalling end of mapping process finished with success.
  """

  def __init__ (self, id, result, error=None):
    """
    Init.

    :param id: NFFG id
    :type id: str or int
    :param result: result of the instantiation
    :type result: str
    :param error: optional Error object
    :type error: :any:`exceptions.BaseException`
    """
    super(InstantiationFinishedEvent, self).__init__()
    self.id = id
    self.result = result
    self.error = error


class ResourceOrchestrationAPI(AbstractAPI):
  """
  Entry point for Resource Orchestration Sublayer (ROS).

  Maintain the contact with other UNIFY layers.

  Implement the Sl - Or reference point.
  """
  # Defined specific name for core object i.e. pox.core.<_core_name>
  _core_name = LAYER_NAME
  """Defined specific name for core object"""
  # Events raised by this class
  _eventMixin_events = {InstallNFFGEvent, GetGlobalResInfoEvent,
                        VirtResInfoEvent, InstantiationFinishedEvent,
                        CollectMonitoringDataEvent}
  """Events raised by this class"""
  # Dependencies
  dependencies = ('adaptation', 'REST-API')
  """Layer dependencies"""

  def __init__ (self, standalone=False, **kwargs):
    """
    .. seealso::
      :func:`AbstractAPI.__init__() <escape.util.api.AbstractAPI.__init__>`
    """
    log.info("Starting Resource Orchestration Sublayer...")
    # Mandatory super() call
    self.orchestrator = None
    """:type: ResourceOrchestrator"""
    self.api_mgr = RESTAPIManager(unique_bb_id=False,
                                  unique_nf_id=CONFIG.ensure_unique_vnf_id(),
                                  logger=log)
    self.log = log.getChild('API')
    super(ResourceOrchestrationAPI, self).__init__(standalone, **kwargs)

  def initialize (self):
    """
    .. seealso::
      :func:`AbstractAPI.initialize() <escape.util.api.AbstractAPI.initialize>`
    """
    log.debug("Initializing Resource Orchestration Sublayer...")
    self.orchestrator = ResourceOrchestrator(self)
    if self._nffg_file:
      try:
        service_request = self._read_data_from_file(self._nffg_file)
        service_request = NFFG.parse(service_request)
        dov = self.orchestrator.virtualizerManager.dov
        self.__proceed_instantiation(nffg=service_request,
                                     resource_view=dov.get_resource_info())
      except (ValueError, IOError, TypeError) as e:
        log.error("Can't load service request from file because of: " + str(e))
        quit_with_error(msg=str(e), logger=log)
      else:
        log.info("Graph representation is loaded successfully!")
    # Initiate ROS REST-API if needed
    if self._agent or self._rosapi:
      self._initiate_ros_api()
    log.info("Resource Orchestration Sublayer has been initialized!")
    if self._agent:
      log.warning("In AGENT mode Service Layer is not going to be initialized!")

  def shutdown (self, event):
    """
    .. seealso::
      :func:`AbstractAPI.shutdown() <escape.util.api.AbstractAPI.shutdown>`

    :param event: event object
    """
    log.info("Resource Orchestration Sublayer is going down...")
    self.orchestrator.finalize()

  def _initiate_ros_api (self):
    """
    Initialize and setup REST API in a different thread.

    If agent_mod is set rewrite the received NFFG domain from REMOTE to
    INTERNAL.

    :return: None
    """
    rest_api = self.get_dependent_component('REST-API')
    rest_api.register_component(component=self)
    if self._agent:
      log.info("REST-API is set in AGENT mode")

  ##############################################################################
  # Agent API functions starts here
  ##############################################################################

  def __get_slor_resource_view (self):
    """
    :return: Return with the Virtualizer object assigned to the Sl-Or interface.
    :rtype: :any:`AbstractVirtualizer`
    """
    virt_mgr = self.orchestrator.virtualizerManager
    virtualizer_type = CONFIG.get_api_virtualizer(layer=self._core_name)
    params = CONFIG.get_virtualizer_params(layer=self._core_name)
    log.debug("Acquired Virtualizer type: %s, params: %s" % (virtualizer_type,
                                                             params))
    return virt_mgr.get_virtual_view(virtualizer_id=self._core_name,
                                     type=virtualizer_type,
                                     **params)

  def rest_api_get_config (self):
    """
    Implementation of REST-API RPC: get-config. Return with the global
    resource as an :class:`NFFG` if it has been changed otherwise return with
    False.

    :return: global resource view (DoV)
    :rtype: :class:`NFFG` or False
    """
    self.log.debug("Requesting Virtualizer for %s" % self._core_name)
    slor_virt = self.__get_slor_resource_view()
    if slor_virt is not None:
      # Check the topology is initialized
      if slor_virt.revision is None:
        self.log.debug("DoV has not initialized yet! "
                       "Force to get default topology...")
      else:
        # Check if the resource is changed
        if self.api_mgr.topology_revision == slor_virt.revision:
          # If resource has not been changed return False
          # This causes to response with the cached topology
          self.log.debug("Global resource has not changed (revision: %s)! "
                         % slor_virt.revision)
          log.debug("Send topology from cache...")
          if self.api_mgr.last_response is None:
            log.error("Cached topology is missing!")
            return
          else:
            return self.api_mgr.last_response
        else:
          self.log.debug("Response cache is outdated (new revision: %s)!"
                         % slor_virt.revision)
      # Get topo view as NFFG
      res = slor_virt.get_resource_info()
      self.api_mgr.topology_revision = slor_virt.revision
      self.log.debug("Updated revision number: %s"
                     % self.api_mgr.topology_revision)
      if CONFIG.get_rest_api_config(self._core_name)['unify_interface']:
        self.log.info("Convert internal NFFG to Virtualizer...")
        res = self.api_mgr.converter.dump_to_Virtualizer(nffg=res)
      log.debug("Cache acquired topology...")
      self.api_mgr.last_response = res
      return res
    else:
      log.error("Virtualizer assigned to %s is not found!" % self._core_name)

  # noinspection PyUnusedLocal
  def rest_api_edit_config (self, id, data, params=None):
    """
    Implementation of REST-API RPC: edit-config

    :param params: original request params
    :type params: dict
    :return: None
    """
    self.log.info("Invoke preprocessing on %s with SG: %s "
                  % (self.__class__.__name__, id))
    if self._agent:
      # ESCAPE serves as a local orchestrator, probably with infrastructure
      # layer --> rewrite domain
      nffg = self.__update_nffg_domain(nffg_part=data)
    # Get resource view of the interface
    res = self.__get_slor_resource_view().get_resource_info()
    if CONFIG.get_rest_api_config(self._core_name)['unify_interface']:
      self.log.debug("Virtualizer format enabled! Start conversion step...")
      if CONFIG.get_rest_api_config(self._core_name)['diff']:
        self.log.debug("Diff format enabled! Start patching step...")
        if self.api_mgr.last_response is None:
          self.log.info("Missing cached Virtualizer! Acquiring topology now...")
          self.rest_api_get_config()
        stats.add_measurement_start_entry(type=stats.TYPE_PROCESSING,
                                          info="RECREATE-FULL-REQUEST")
        self.log.info("Patching cached topology with received diff...")
        full_req = self.api_mgr.last_response.yang_copy()
        full_req.patch(source=data)
        stats.add_measurement_end_entry(type=stats.TYPE_PROCESSING,
                                        info="RECREATE-FULL-REQUEST")
      else:
        full_req = data
      self.log.info("Converting full request data...")
      stats.add_measurement_start_entry(type=stats.TYPE_CONVERSION,
                                        info="VIRTUALIZER-->NFFG")
      nffg = self.api_mgr.converter.parse_from_Virtualizer(vdata=full_req)
      stats.add_measurement_end_entry(type=stats.TYPE_CONVERSION,
                                      info="VIRTUALIZER-->NFFG")
    else:
      nffg = data
    self.log.debug("Set NFFG id: %s" % id)
    if nffg.service_id is None:
      nffg.service_id = nffg.id
    nffg.id = id
    if params:
      nffg.add_metadata(name="params", value=params)
    self.log.info("Proceeding request: %s to instantiation..." % id)
    # ESCAPE serves as a global or proxy orchestrator
    self.__proceed_instantiation(nffg=nffg, resource_nffg=res)
    self.log.info("Preprocessing on %s ended!" % self.__class__.__name__)

  @staticmethod
  def __update_nffg_domain (nffg_part, domain_name=None):
    """
    Update domain descriptor of infras: REMOTE -> INTERNAL

    :param nffg_part: NF-FG need to be updated
    :type nffg_part: :class:`NFFG`
    :return: updated NFFG
    :rtype: :class:`NFFG`
    """
    rewritten = []
    if domain_name is None:
      local_mgr = CONFIG.get_internal_manager()
      if local_mgr is None:
        log.error("No local Manager has been initiated! "
                  "Skip domain rewriting!")
      elif len(local_mgr) > 1:
        log.warning("Multiple local Manager has been initiated: %s! "
                    "Arbitrarily use the first..." % local_mgr)
      domain_name = local_mgr.pop()
    log.debug("Rewrite received NFFG domain to %s..." % domain_name)
    for infra in nffg_part.infras:
      infra.domain = domain_name
      rewritten.append(infra.id)
    log.debug("Rewritten infrastructure nodes: %s" % rewritten)
    return nffg_part

  def rest_api_status (self, message_id):
    """
    Return the state of a request given by ``message_id``.

    :param message_id: request id
    :type message_id: str or int
    :return: state
    :rtype: str
    """
    status = self.api_mgr.request_cache.get_status(id=message_id)
    if status == RequestStatus.SUCCESS:
      return httplib.OK, None
    elif status == RequestStatus.UNKNOWN:
      return httplib.NOT_FOUND, None
    elif status == RequestStatus.ERROR:
      return httplib.INTERNAL_SERVER_ERROR, status
    else:
      # PROCESSING or INITIATED
      return httplib.ACCEPTED, None

  def rest_api_mapping_info (self, service_id):
    """
    Return with collected information of mapping of a given service.

    :param service_id: service request ID
    :type service_id: str
    :return: mapping info
    :rtype: dict
    """
    # Create base response structure
    ret = {"service_id": service_id}
    log.debug("Collecting mapping info...")
    mapping = self.orchestrator.collect_mapping_info(service_id=service_id)
    if isinstance(mapping, basestring):
      return ret
    log.debug("Resolving domain URLs...")
    adaptation = self.get_dependent_component("adaptation")
    if adaptation is None:
      log.error("Adaptation Layer is missing!")
    else:
      adaptation.controller_adapter.collect_domain_urls(mapping=mapping)
    ret['mapping'] = mapping
    # Collect NF management data
    log.debug("Collected mapping info:\n%s" % pprint.pformat(ret))
    return ret

  def rest_api_mappings (self, mappings):
    """
    Calculate the mappings of NFs given in the mappings structure.

    :param mappings: requested mappings
    :type mappings: Mappings
    :return: new mappings with extended info
    :rtype: Mappings
    """
    slor_topo = self.__get_slor_resource_view().get_resource_info()
    log.debug("Collecting mapping info...")
    response = self.orchestrator.collect_mappings(mappings=mappings,
                                                  slor_topo=slor_topo)
    log.debug("Resolving domain URLs...")
    adaptation = self.get_dependent_component("adaptation")
    if adaptation is None:
      log.error("Adaptation Layer is missing!")
    else:
      for mapping in response:
        domain = mapping.target.domain.get_value()
        url = adaptation.controller_adapter.get_domain_url(domain=domain)
        if url:
          log.debug("Found URL: %s for domain: %s" % (url, domain))
        else:
          log.error("URL is missing from domain: %s!" % domain)
          url = "N/A"
        mapping.target.domain.set_value("%s@%s" % (domain, url))
    return response

  @schedule_as_coop_task
  def rest_api_info (self, info, id, params):
    """
    Main entry point to process a received Info request.

    :param info: parsed Info structure
    :type info: :class:`Info`
    :param id: unique id
    :type id: str or int
    """
    self.log.debug("Cache 'info' request params with id: %s" % id)
    self.api_mgr.request_cache.cache_request(message_id=id, params=params)
    slor_topo = self.__get_slor_resource_view().get_resource_info()
    splitted = self.orchestrator.filter_info_request(info=info,
                                                     slor_topo=slor_topo)
    log.debug("Propagate info request to adaptation layer...")
    self.raiseEventNoErrors(CollectMonitoringDataEvent, info=splitted, id=id)

  ##############################################################################
  # UNIFY Sl- Or API functions starts here
  ##############################################################################

  def _handle_InstantiateNFFGEvent (self, event):
    """
    Instantiate given NF-FG (UNIFY Sl - Or API).

    :param event: event object contains NF-FG
    :type event: :any:`InstantiateNFFGEvent`
    :return: None
    """
    self.log.info("Received NF-FG: %s from %s layer"
                  % (event.nffg, str(event.source._core_name).title()))
    self.__proceed_instantiation(nffg=event.nffg,
                                 resource_nffg=event.resource_nffg)

  @schedule_as_coop_task
  def __proceed_instantiation (self, nffg, resource_nffg):
    """
    Helper function to instantiate the NFFG mapping from different source.

    :param nffg: pre-mapped service request
    :type nffg: :class:`NFFG`
    :return: None
    """
    self.log.info("Invoke instantiation on %s with NF-FG: %s"
                  % (self.__class__.__name__, nffg.name))
    stats.add_measurement_start_entry(type=stats.TYPE_ORCHESTRATION,
                                      info=LAYER_NAME)
    # Get shown topology view
    if resource_nffg is None:
      log.error("Missing resource for difference calculation!")
      return
    log.debug("Got resource view for difference calculation: %s" %
              resource_nffg)
    self.log.debug("Store received NFFG request info...")
    msg_id = self.api_mgr.request_cache.cache_request_by_nffg(nffg=nffg)
    if msg_id is not None:
      self.api_mgr.request_cache.set_in_progress(id=msg_id)
      self.log.debug("Request is stored with id: %s" % msg_id)
    else:
      self.log.debug("No request info detected.")
    # Check if mapping mode is set globally in CONFIG
    mapper_params = CONFIG.get_mapping_config(layer=LAYER_NAME)
    if 'mode' in mapper_params and mapper_params['mode'] is not None:
      mapping_mode = mapper_params['mode']
      log.info("Detected mapping mode from configuration: %s" % mapping_mode)
    elif nffg.mode is not None:
      mapping_mode = nffg.mode
      log.info("Detected mapping mode from NFFG: %s" % mapping_mode)
    else:
      mapping_mode = None
      log.info("No mapping mode was defined explicitly!")
    if not CONFIG.get_mapping_enabled(layer=LAYER_NAME):
      log.warning("Mapping is disabled! Skip difference calculation...")
    elif nffg.status == NFFG.MAP_STATUS_SKIPPED:
      log.debug("Detected NFFG map status: %s! "
                "Skip difference calculation and "
                "proceed with original request..." % nffg.status)
    elif mapping_mode != NFFG.MODE_REMAP:
      # Calculated ADD-DELETE difference
      log.debug("Calculate ADD - DELETE difference with mapping mode...")
      # Recreate SG-hops for diff calc.
      log.debug("Recreate SG hops for difference calculation...")
      NFFGToolBox.recreate_all_sghops(nffg=nffg)
      NFFGToolBox.recreate_all_sghops(nffg=resource_nffg)
      log.log(VERBOSE, "New NFFG:\n%s" % nffg.dump())
      log.log(VERBOSE, "Resource NFFG:\n%s" % resource_nffg.dump())
      # Calculate difference
      add_nffg, del_nffg = NFFGToolBox.generate_difference_of_nffgs(
        old=resource_nffg, new=nffg, ignore_infras=True)
      log.log(VERBOSE, "Calculated ADD NFFG:\n%s" % add_nffg.dump())
      log.log(VERBOSE, "Calculated DEL NFFG:\n%s" % del_nffg.dump())
      if not add_nffg.is_bare() and del_nffg.is_bare():
        nffg = add_nffg
        log.info("DEL NFFG is bare! Calculated mapping mode: %s" % nffg.mode)
      elif add_nffg.is_bare() and not del_nffg.is_bare():
        nffg = del_nffg
        log.info("ADD NFFG is bare! Calculated mapping mode: %s" % nffg.mode)
      elif not add_nffg.is_bare() and not del_nffg.is_bare():
        log.warning("Both ADD / DEL mode is not supported currently")
        self.__process_mapping_result(nffg_id=nffg.id, fail=True)
        self.raiseEventNoErrors(InstantiationFinishedEvent,
                                id=nffg.id,
                                result=InstantiationFinishedEvent.ABORTED)
        return
      else:
        log.debug("Difference calculation resulted empty subNFFGs!")
        log.info("No change has been detected in request! Skip mapping...")
        self.log.debug("Invoked instantiation on %s is finished!"
                       % self.__class__.__name__)
        self.__process_mapping_result(nffg_id=nffg.id, fail=False)
        return
    else:
      log.debug("Mode: %s detected from config! Skip difference calculation..."
                % mapping_mode)
    try:
      if CONFIG.get_mapping_enabled(layer=LAYER_NAME):
        # Initiate request mapping
        mapped_nffg = self.orchestrator.instantiate_nffg(nffg=nffg)
      else:
        log.warning("Mapping is disabled! Skip instantiation step...")
        mapped_nffg = nffg
        mapped_nffg.status = NFFG.MAP_STATUS_SKIPPED
        log.debug("Mark NFFG status: %s!" % mapped_nffg.status)
      # Rewrite REMAP mode for backward compatibility
      if mapped_nffg is not None and mapping_mode == NFFG.MODE_REMAP:
        mapped_nffg.mode = mapping_mode
        log.debug("Rewrite mapping mode: %s into mapped NFFG..." %
                  mapped_nffg.mode)
      else:
        log.debug("Skip mapping mode rewriting! Mode remained: %s" %
                  mapping_mode)
        self.log.debug("Invoked instantiate_nffg on %s is finished!" %
                       self.__class__.__name__)
      # If mapping is not threaded and finished with OK
      if mapped_nffg is not None and not self.orchestrator.mapper.threaded:
        self._proceed_to_install_NFFG(mapped_nffg=mapped_nffg,
                                      original_request=nffg)
      else:
        log.warning("Something went wrong in service request instantiation: "
                    "mapped service request is missing!")
        self.__process_mapping_result(nffg_id=nffg.id, fail=True)
        self.raiseEventNoErrors(InstantiationFinishedEvent,
                                id=nffg.id,
                                result=InstantiationFinishedEvent.MAPPING_ERROR)
    except ProcessorError as e:
      self.__process_mapping_result(nffg_id=nffg.id, fail=True)
      self.raiseEventNoErrors(InstantiationFinishedEvent,
                              id=nffg.id,
                              result=InstantiationFinishedEvent.REFUSED_BY_VERIFICATION,
                              error=e)

  @schedule_as_coop_task
  def __proceed_trial_and_error (self, original_request_id):
    """
    Perform remapping task after a failed deploy trial.

    :param original_request_id: original request id
    :type original_request_id: str or int
    :return: None
    """
    self.log.info("Invoke trial_and_error for remapping "
                  "with request id: %s" % original_request_id)
    mapped_nffg = self.orchestrator.instantiate_nffg(nffg=None,
                                                     continued_request_id=original_request_id)
    self.log.debug("Invoked trial_and_error on %s is finished!" %
                   self.__class__.__name__)
    nffg = self.orchestrator.nffgManager.get(nffg_id=original_request_id)
    # If mapping is not threaded and finished with OK
    if mapped_nffg is not None and not self.orchestrator.mapper.threaded:
      self._proceed_to_install_NFFG(mapped_nffg=mapped_nffg,
                                    original_request=nffg)
    else:
      log.error("Something went wrong in trial_and_error instantiation: "
                "mapped service request is missing!")
      self.__process_mapping_result(nffg_id=nffg.id, fail=True)
      self.raiseEventNoErrors(InstantiationFinishedEvent,
                              id=nffg.id,
                              result=InstantiationFinishedEvent.MAPPING_ERROR)

  def __process_mapping_result (self, nffg_id, fail):
    """
    Perform common tasks after the mapping alg has run and deploy is performed.

    :param nffg_id: deployed NFFG id
    :type nffg_id: str or int
    :param fail: mark the deploy step was failed
    :type fail: bool
    :return: None
    """
    self.log.debug("Cache request status...")
    req_status = self.api_mgr.request_cache.get_request_by_nffg_id(nffg_id)
    if req_status is None:
      self.log.debug("Request status is missing for NFFG: %s! "
                     "Skip result processing..." % nffg_id)
      return
    self.log.debug("Process mapping result...")
    message_id = req_status.message_id
    if message_id is not None:
      if fail:
        self.api_mgr.request_cache.set_error_result(id=message_id)
      else:
        self.api_mgr.request_cache.set_success_result(id=message_id)
      log.info("Set request status: %s for message: %s"
               % (req_status.status, req_status.message_id))
      ret = self.api_mgr.invoke_callback(message_id=message_id)
      if ret is None:
        self.log.debug("No callback was defined!")
      else:
        self.log.debug("Callback: %s has invoked with return value: %s" % (
          req_status.get_callback(), ret))
    RequestScheduler().set_orchestration_finished(id=nffg_id)

  def _proceed_to_install_NFFG (self, mapped_nffg, original_request=None):
    """
    Send mapped :class:`NFFG` to Controller Adaptation Sublayer in an
    implementation-specific way.

    General function which is used from microtask and Python thread also.

    This function contains the last steps before the mapped NFFG will be sent
    to the next layer.

    :param mapped_nffg: mapped NF-FG
    :type mapped_nffg: :class:`NFFG`
    :return: None
    """
    # Non need to rebind req links --> it will be done in Adaptation layer
    # Log verbose mapping result in unified way (threaded/non-threaded)
    log.log(VERBOSE, "Mapping result of Orchestration Layer:\n%s" %
            mapped_nffg.dump())
    # Sending NF-FG to Adaptation layer as an Event
    # Exceptions in event handlers are caught by default in a non-blocking way
    self.raiseEventNoErrors(InstallNFFGEvent,
                            mapped_nffg=mapped_nffg,
                            original_request=original_request)
    self.log.info("Mapped NF-FG: %s has been sent to Adaptation..." %
                  mapped_nffg)

  def _handle_GetVirtResInfoEvent (self, event):
    """
    Generate virtual resource info and send back to SAS.

    :param event: event object contains service layer id
    :type event: :any:`GetVirtResInfoEvent`
    :return: None
    """
    self.log.debug("Received <Virtual View> request from %s layer" %
                   str(event.source._core_name).title())
    # Currently view is a Virtualizer to keep ESCAPE fast
    # Virtualizer type for Sl-Or API
    virtualizer_type = CONFIG.get_api_virtualizer(layer=LAYER_NAME)
    params = CONFIG.get_virtualizer_params(layer=LAYER_NAME)
    v = self.orchestrator.virtualizerManager.get_virtual_view(
      virtualizer_id=event.sid, type=virtualizer_type, **params)
    if v is None:
      self.log.error("Missing Virtualizer for id: %s!" % event.sid)
      return
    self.log.debug("Sending back <Virtual View>: %s..." % v)
    self.raiseEventNoErrors(VirtResInfoEvent, v)

  def _handle_InfoRequestFinishedEvent (self, event):
    """
    Get information from NFFG installation process.

    :param event: event object info
    :type event: :any:`InstallationFinishedEvent`
    :return: None
    """
    if not InfoRequestFinishedEvent.is_error(event.result):
      self.log.info("Info collection from domains has been "
                    "finished successfully with result: %s!" % event.result)
      self.__process_info_result(status=event.status, fail=False)
    else:
      self.log.info("Info collection from domains has been "
                    "finished with error result: %s!" % event.result)
      self.__process_info_result(status=event.status, fail=True)

  def __process_info_result (self, status, fail):
    """
    Perform common tasks after an Info request was processed and responses were
    collected.

    :param status: deploy status
    :type status: :any:`DomainRequestStatus`
    :param fail: mark the Info step was failed
    :type fail: bool
    :return: None
    """
    self.log.debug("Cache collected 'info' request status...")
    req_status = self.api_mgr.request_cache.get_request(message_id=status.id)
    if req_status is None:
      self.log.debug("Request status is missing: %s! "
                     "Skip result processing..." % status.id)
      return
    self.log.debug("Process collected info result...")
    if fail:
      self.api_mgr.request_cache.set_error_result(id=status.id)
      body = None
    else:
      self.api_mgr.request_cache.set_success_result(id=status.id)
      body = status.data[0]
      body = body.xml() if isinstance(body, Info) else str(body)
    log.info("Set request status: %s for message: %s"
             % (req_status.status, req_status.message_id))
    log.log(VERBOSE, "Collected Info data:\n%s" % body)
    ret = self.api_mgr.invoke_callback(message_id=status.id, body=body)
    if ret is None:
      self.log.debug("No callback was defined!")
    else:
      self.log.info("Callback: %s has invoked with return value: %s" % (
        req_status.get_callback(), ret))
      # TODO - handle remained request-cache -> remove or store for a while??

  def _handle_NFFGMappingFinishedEvent (self, event):
    """
    Handle NFFGMappingFinishedEvent and proceed with  :class:`NFFG
    <escape.util.nffg.NFFG>` installation.

    :param event: event object
    :type event: :any:`NFFGMappingFinishedEvent`
    :return: None
    """
    self._proceed_to_install_NFFG(event.nffg)

  ##############################################################################
  # UNIFY Or - Ca API functions starts here
  ##############################################################################

  # noinspection PyUnusedLocal
  def _handle_MissingGlobalViewEvent (self, event):
    """
    Request Global infrastructure View from CAS (UNIFY Or - CA API).

    Invoked when a :class:`MissingGlobalViewEvent` raised.

    :param event: event object
    :type event: :any:`MissingGlobalViewEvent`
    :return: None
    """
    self.log.debug("Send DoV request to Adaptation layer...")
    self.raiseEventNoErrors(GetGlobalResInfoEvent)

  def _handle_GlobalResInfoEvent (self, event):
    """
    Save requested Global Infrastructure View as the :class:`DomainVirtualizer`.

    :param event: event object contains resource info
    :type event: :any:`GlobalResInfoEvent`
    :return: None
    """
    self.log.debug("Received DoV from %s Layer"
                   % str(event.source._core_name).title())
    self.orchestrator.virtualizerManager.dov = event.dov

  def _handle_InstallationFinishedEvent (self, event):
    """
    Get information from NFFG installation process.

    :param event: event object info
    :type event: :any:`InstallationFinishedEvent`
    :return: None
    """
    if not InstantiationFinishedEvent.is_error(event.result):
      self.log.info("NF-FG(%s) instantiation has been finished successfully "
                    "with result: %s!" % (event.id, event.result))
    else:
      self.log.error("NF-FG(%s) instantiation has been finished with error "
                     "result: %s!" % (event.id, event.result))
      if InstantiationFinishedEvent.is_deploy_error(event.result):
        if CONFIG.get_trial_and_error(layer=LAYER_NAME):
          log.info("TRIAL_AND_ERROR is enabled! Reschedule for mapping...")
          self.__proceed_trial_and_error(original_request_id=event.id)
          return
        else:
          log.debug("TRIAL_AND_ERROR is disabled! Proceeding...")
    if not event.is_pending(event.result):
      self.__process_mapping_result(nffg_id=event.id,
                                    fail=event.is_error(event.result))
    self.raiseEventNoErrors(InstantiationFinishedEvent,
                            id=event.id,
                            result=event.result)
