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
Implements the platform and POX dependent logic for the Resource Orchestration
Sublayer.
"""
import httplib
import pprint

from escape import CONFIG
from escape.nffg_lib.nffg import NFFG, NFFGToolBox
from escape.orchest import LAYER_NAME, log as log  # Orchestration layer logger
from escape.orchest.provisioning import ExtendedMonitoringRESTServer
from escape.orchest.ros_orchestration import ResourceOrchestrator
from escape.util.api import AbstractAPI, RESTServer, RequestStatus
from escape.util.domain import BaseResultEvent
from escape.util.mapping import ProcessorError
from escape.util.misc import schedule_as_coop_task, notify_remote_visualizer, \
  VERBOSE, quit_with_error
from pox.lib.revent.revent import Event
from virtualizer_mappings import Mappings


class InstallNFFGEvent(Event):
  """
  Event for passing mapped :any:`NFFG` to Controller
  Adaptation Sublayer.
  """

  def __init__ (self, mapped_nffg):
    """
    Init

    :param mapped_nffg: NF-FG graph need to be installed
    :type mapped_nffg: NFFG
    :return: None
    """
    super(InstallNFFGEvent, self).__init__()
    self.mapped_nffg = mapped_nffg


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
  def __init__ (self, info):
    super(CollectMonitoringDataEvent, self).__init__()
    self.info = info


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
  dependencies = ('adaptation',)
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
    # Initiate Cf-Or REST-API if needed
    if self._cfor:
      self._initiate_cfor_api()
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
    if self._agent or self._rosapi:
      log.debug("REST-API: %s is shutting down..." % self.ros_api.api_id)
      # self.ros_api.stop()
    if self._cfor:
      log.debug("REST-API: %s is shutting down..." % self.cfor_api.api_id)
      # self.cfor_api.stop()

  def _initiate_ros_api (self):
    """
    Initialize and setup REST API in a different thread.

    If agent_mod is set rewrite the received NFFG domain from REMOTE to
    INTERNAL.

    :return: None
    """
    # set bounded layer name here to avoid circular dependency problem
    handler = CONFIG.get_ros_agent_class()
    handler.bounded_layer = self._core_name
    params = CONFIG.get_ros_agent_params()
    # can override from global config
    if 'prefix' in params:
      handler.static_prefix = params['prefix']
    if 'unify_interface' in params:
      handler.virtualizer_format_enabled = params['unify_interface']
    if 'diff' in params:
      handler.DEFAULT_DIFF = bool(params['diff'])
    address = (params.get('address'), params.get('port'))
    # Virtualizer ID of the Sl-Or interface
    self.ros_api = ExtendedMonitoringRESTServer(handler, *address)
    self.ros_api.api_id = handler.LOGGER_NAME = "Sl-Or"
    # Virtualizer type for Sl-Or API
    self.ros_api.virtualizer_type = CONFIG.get_api_virtualizer(
      layer_name=LAYER_NAME, api_name=self.ros_api.api_id)
    handler.log.info("Init REST-API for %s on %s:%s!" % (
      self.ros_api.api_id, address[0], address[1]))
    self.ros_api.start()
    handler.log.debug(
      "Enforced configuration for %s: virtualizer type: %s, interface: %s, "
      "diff: %s" % (self.ros_api.api_id, self.ros_api.virtualizer_type,
                    "UNIFY" if handler.virtualizer_format_enabled else
                    "Internal-NFFG", handler.DEFAULT_DIFF))
    if self._agent:
      log.info("REST-API is set in AGENT mode")

  def _initiate_cfor_api (self):
    """
    Initialize and setup REST API in a different thread.

    :return: None
    """
    # set bounded layer name here to avoid circular dependency problem
    handler = CONFIG.get_cfor_api_class()
    handler.bounded_layer = self._core_name
    params = CONFIG.get_cfor_agent_params()
    # can override from global config
    if 'prefix' in params:
      handler.static_prefix = params['prefix']
    if 'unify_interface' in params:
      handler.virtualizer_format_enabled = params['unify_interface']
    if 'diff' in params:
      handler.DEFAULT_DIFF = bool(params['diff'])
    address = (params.get('address'), params.get('port'))
    self.cfor_api = RESTServer(handler, *address)
    # Virtualizer ID of the Cf-Or interface
    self.cfor_api.api_id = handler.LOGGER_NAME = "Cf-Or"
    # Virtualizer type for Cf-Or API
    self.cfor_api.virtualizer_type = CONFIG.get_api_virtualizer(
      layer_name=LAYER_NAME, api_name=self.cfor_api.api_id)
    handler.log.info("Init REST-API for %s on %s:%s!" % (
      self.cfor_api.api_id, address[0], address[1]))
    self.cfor_api.start()
    handler.log.debug(
      "Enforced configuration for %s: virtualizer type: %s, interface: %s, "
      "diff: %s" % (self.cfor_api.api_id, self.cfor_api.virtualizer_type,
                    "UNIFY" if handler.virtualizer_format_enabled else
                    "Internal-NFFG", handler.DEFAULT_DIFF))

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
  # Agent API functions starts here
  ##############################################################################

  def __get_slor_resource_view (self):
    """
    Return with the Virtualizer object assigned to the Sl-Or interface.
    """
    virt_mgr = self.orchestrator.virtualizerManager
    return virt_mgr.get_virtual_view(virtualizer_id=self.ros_api.api_id,
                                     type=self.ros_api.virtualizer_type)

  def api_ros_get_config (self):
    """
    Implementation of REST-API RPC: get-config. Return with the global
    resource as an :any:`NFFG` if it has been changed otherwise return with
    False.

    :return: global resource view (DoV)
    :rtype: :any:`NFFG` or False
    """
    log.getChild('[Sl-Or]').debug("Requesting Virtualizer for REST-API")
    slor_virt = self.__get_slor_resource_view()
    if slor_virt is not None:
      # Check if the resource is changed
      if slor_virt.is_changed():
        log.getChild('[Sl-Or]').debug("Generate topo description...")
        res = slor_virt.get_resource_info()
        return res
      elif not self.ros_api.last_response:
        # If the topology has already been queried but not sent back and stored
        log.debug("Last responded topology is missing! "
                  "Requesting cached topology...")
        return slor_virt.get_cached_resource_info()
      else:
        # If resource has not been changed return False
        # This causes to response with the cached topology
        return False

    else:
      log.error("Virtualizer(id=%s) assigned to REST-API is not found!" %
                self.ros_api.api_id)

  def api_ros_edit_config (self, nffg, params):
    """
    Implementation of REST-API RPC: edit-config

    :param nffg: NFFG need to deploy
    :type nffg: :any:`NFFG`
    """
    log.getChild('[Sl-Or]').info("Invoke install_nffg on %s with SG: %s " % (
      self.__class__.__name__, nffg))
    if self._agent:
      # ESCAPE serves as a local orchestrator, probably with infrastructure
      # layer --> rewrite domain
      nffg = self.__update_nffg_domain(nffg_part=nffg)
    # Get resource view of the interface
    res = self.__get_slor_resource_view().get_resource_info()
    # ESCAPE serves as a global or proxy orchestrator
    self.__proceed_instantiation(nffg=nffg, resource_nffg=res)

  @staticmethod
  def __update_nffg_domain (nffg_part, domain_name=None):
    """
    Update domain descriptor of infras: REMOTE -> INTERNAL

    :param nffg_part: NF-FG need to be updated
    :type nffg_part: :any:`NFFG`
    :return: updated NFFG
    :rtype: :any:`NFFG`
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

  def api_ros_status (self, message_id):
    """
    Return the state of a request given by ``message_id``.

    :param message_id: request id
    :type message_id: str or int
    :return: state
    :rtype: str
    """
    status = self.ros_api.request_cache.get_status(id=message_id)
    if status == RequestStatus.SUCCESS:
      return httplib.OK, None
    elif status == RequestStatus.UNKNOWN:
      return httplib.NOT_FOUND, None
    elif status == RequestStatus.ERROR:
      return httplib.INTERNAL_SERVER_ERROR, status
    else:
      # PROCESSING or INITIATED
      return httplib.ACCEPTED, None

  def api_ros_mapping_info (self, service_id):
    """
    Return with collected information of mapping of a given service.

    :param service_id: service request ID
    :type service_id: str
    :return: mapping info
    :rtype: dict
    """
    # Create base response structure
    ret = {"service_id": service_id}
    mapping = self.orchestrator.collect_mapping_info(service_id=service_id)
    ret['mapping'] = mapping
    # Collect NF management data
    log.debug("Collected mapping info:\n%s" % pprint.pformat(ret))
    return ret

  def api_ros_mappings (self, mappings):
    """
    Calculate the mappings of NFs given in the mappings structure.

    :param mappings: requested mappings
    :type mappings: Mappings
    :return: new mappings with extended info
    :rtype: Mappings
    """
    slor_topo = self.__get_slor_resource_view().get_resource_info()
    response = self.orchestrator.collect_mappings(mappings=mappings,
                                                  slor_topo=slor_topo)
    return response

  @schedule_as_coop_task
  def api_ros_info (self, info):
    slor_topo = self.__get_slor_resource_view().get_resource_info()
    splitted = self.orchestrator.filter_info_request(info=info,
                                                     slor_topo=slor_topo)
    log.debug("Propagate info request to adaptation layer...")
    self.raiseEventNoErrors(CollectMonitoringDataEvent, info=splitted)

  ##############################################################################
  # Cf-Or API functions starts here
  ##############################################################################

  def __get_cfor_resource_view (self):
    """
    Return with the Virtualizer object assigned to the Cf-Or interface.

    :return: Virtualizer of Cf-Or interface
    :rtype: :any:`AbstractVirtualizer`
    """
    virt_mgr = self.orchestrator.virtualizerManager
    return virt_mgr.get_virtual_view(virtualizer_id=self.cfor_api.api_id,
                                     type=self.cfor_api.virtualizer_type)

  def api_cfor_get_config (self):
    """
    Implementation of Cf-Or REST-API RPC: get-config.

    :return: dump of a single BiSBiS view based on DoV
    :rtype: str
    """
    log.getChild('[Cf-Or]').debug("Requesting Virtualizer for REST-API...")
    cfor_virt = self.__get_cfor_resource_view()
    if cfor_virt is not None:
      log.getChild('[Cf-Or]').debug("Generate topo description...")
      return cfor_virt.get_resource_info()
    else:
      log.error("Virtualizer(id=%s) assigned to REST-API is not found!" %
                self.cfor_api.api_id)

  def api_cfor_edit_config (self, nffg):
    """
    Implementation of Cf-Or REST-API RPC: edit-config

    :param nffg: NFFG need to deploy
    :type nffg: :any:`NFFG`
    """
    log.getChild('[Cf-Or]').info("Invoke install_nffg on %s with SG: %s " % (
      self.__class__.__name__, nffg))
    # Get resource view of the interface
    res = self.__get_cfor_resource_view().get_resource_info()
    self.__proceed_instantiation(nffg=nffg, resource_nffg=res)

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
    log.getChild('API').info("Received NF-FG: %s from %s layer" % (
      event.nffg, str(event.source._core_name).title()))
    self.__proceed_instantiation(nffg=event.nffg,
                                 resource_nffg=event.resource_nffg)

  @schedule_as_coop_task
  def __proceed_instantiation (self, nffg, resource_nffg):
    """
    Helper function to instantiate the NFFG mapping from different source.

    :param nffg: pre-mapped service request
    :type nffg: :any:`NFFG`
    :return: None
    """
    log.getChild('API').info("Invoke instantiate_nffg on %s with NF-FG: %s " % (
      self.__class__.__name__, nffg.name))
    # Get shown topology view
    if resource_nffg is None:
      log.error("Missing resource for difference calculation!")
      return
    log.debug("Got resource view for difference calculation: %s" %
              resource_nffg)
    if hasattr(self, 'ros_api') and self.ros_api:
      log.getChild('API').debug("Store received NFFG request info...")
      msg_id = self.ros_api.request_cache.cache_request(nffg=nffg)
      if msg_id is not None:
        self.ros_api.request_cache.set_in_progress(id=msg_id)
        log.getChild('API').debug("Request is stored with id: %s" % msg_id)
      else:
        log.getChild('API').debug("No request info detected.")
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
      log.info("No mapping mode was detected!")
    if nffg.status == NFFG.MAP_STATUS_SKIPPED:
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
        return
      else:
        log.debug("Difference calculation resulted empty subNFFGs!")
        log.info("No change has been detected in request! Skip mapping...")
        log.getChild('API').debug("Invoked instantiate_nffg on %s is finished!"
                                  % self.__class__.__name__)
        self.__handle_mapping_result(nffg_id=nffg.id, fail=False)
        return
    else:
      log.debug("Mode: %s detected from config! Skip difference calculation..."
                % mapping_mode)
    try:
      # Initiate request mapping
      mapped_nffg = self.orchestrator.instantiate_nffg(nffg=nffg)
      # Rewrite REMAP mode for backward compatibility
      if mapped_nffg is not None and mapping_mode == NFFG.MODE_REMAP:
        mapped_nffg.mode = mapping_mode
        log.debug("Rewrite mapping mode: %s into mapped NFFG..." %
                  mapped_nffg.mode)
      else:
        log.debug("Skip mapping mode rewriting! Mode remained: %s" %
                  mapping_mode)
      log.getChild('API').debug("Invoked instantiate_nffg on %s is finished!" %
                                self.__class__.__name__)
      # If mapping is not threaded and finished with OK
      if mapped_nffg is not None and not \
         self.orchestrator.mapper.threaded:
        self._proceed_to_install_NFFG(mapped_nffg=mapped_nffg)
      else:
        log.warning("Something went wrong in service request instantiation: "
                    "mapped service request is missing!")
        self.__handle_mapping_result(nffg_id=nffg.id, fail=True)
        self.raiseEventNoErrors(InstantiationFinishedEvent,
                                id=nffg.id,
                                result=InstantiationFinishedEvent.MAPPING_ERROR)
    except ProcessorError as e:
      self.__handle_mapping_result(nffg_id=nffg.id, fail=True)
      self.raiseEventNoErrors(InstantiationFinishedEvent,
                              id=nffg.id,
                              result=InstantiationFinishedEvent.REFUSED_BY_VERIFICATION,
                              error=e)

  def __handle_mapping_result (self, nffg_id, fail):
    if hasattr(self, 'ros_api') and self.ros_api:
      log.getChild('API').debug("Cache request status...")
      req_status = self.ros_api.request_cache.get_request_by_nffg_id(nffg_id)
      if req_status is None:
        log.getChild('API').debug("Request status is missing for NFFG: %s! "
                                  "Skip result processing..." % nffg_id)
        return
      log.getChild('API').debug("Process mapping result...")
      message_id = req_status.message_id
      if message_id is not None:
        if fail:
          self.ros_api.request_cache.set_error_result(id=message_id)
        else:
          self.ros_api.request_cache.set_success_result(id=message_id)
        ret = self.ros_api.invoke_callback(message_id=message_id)
        if ret is None:
          log.getChild('API').debug("No callback was defined!")
        else:
          log.getChild('API').debug(
            "Callback: %s has invoked with return value: %s" % (
              req_status.get_callback(), ret))

  def _proceed_to_install_NFFG (self, mapped_nffg):
    """
    Send mapped :any:`NFFG` to Controller Adaptation Sublayer in an
    implementation-specific way.

    General function which is used from microtask and Python thread also.

    This function contains the last steps before the mapped NFFG will be sent
    to the next layer.

    :param mapped_nffg: mapped NF-FG
    :type mapped_nffg: :any:`NFFG`
    :return: None
    """
    # Non need to rebind req links --> it will be done in Adaptation layer
    # Log verbose mapping result in unified way (threaded/non-threaded)
    log.log(VERBOSE, "Mapping result of Orchestration Layer:\n%s" %
            mapped_nffg.dump())
    # Notify remote visualizer about the mapping result if it's needed
    notify_remote_visualizer(data=mapped_nffg, id=LAYER_NAME)
    # Sending NF-FG to Adaptation layer as an Event
    # Exceptions in event handlers are caught by default in a non-blocking way
    self.raiseEventNoErrors(InstallNFFGEvent, mapped_nffg)
    log.getChild('API').info("Mapped NF-FG: %s has been sent to Adaptation..." %
                             mapped_nffg)

  def _handle_GetVirtResInfoEvent (self, event):
    """
    Generate virtual resource info and send back to SAS.

    :param event: event object contains service layer id
    :type event: :any:`GetVirtResInfoEvent`
    :return: None
    """
    log.getChild('API').debug("Received <Virtual View> request from %s layer" %
                              str(event.source._core_name).title())
    # Currently view is a Virtualizer to keep ESCAPE fast
    # Virtualizer type for Sl-Or API
    virtualizer_type = CONFIG.get_api_virtualizer(layer_name=LAYER_NAME,
                                                  api_name=event.sid)
    v = self.orchestrator.virtualizerManager.get_virtual_view(
      event.sid, type=virtualizer_type)
    if v is None:
      log.getChild('API').error("Missing Virtualizer for id: %s!" % event.sid)
      return
    log.getChild('API').debug("Sending back <Virtual View>: %s..." % v)
    self.raiseEventNoErrors(VirtResInfoEvent, v)

  ##############################################################################
  # UNIFY Or - Ca API functions starts here
  ##############################################################################

  def _handle_MissingGlobalViewEvent (self, event):
    """
    Request Global infrastructure View from CAS (UNIFY Or - CA API).

    Invoked when a :class:`MissingGlobalViewEvent` raised.

    :param event: event object
    :type event: :any:`MissingGlobalViewEvent`
    :return: None
    """
    log.getChild('API').debug(
      "Send DoV request to Adaptation layer...")
    self.raiseEventNoErrors(GetGlobalResInfoEvent)

  def _handle_GlobalResInfoEvent (self, event):
    """
    Save requested Global Infrastructure View as the :class:`DomainVirtualizer`.

    :param event: event object contains resource info
    :type event: :any:`GlobalResInfoEvent`
    :return: None
    """
    log.getChild('API').debug(
      "Received DoV from %s Layer" % str(
        event.source._core_name).title())
    self.orchestrator.virtualizerManager.dov = event.dov

  def _handle_InstallationFinishedEvent (self, event):
    """
    Get information from NFFG installation process.

    :param event: event object info
    :type event: :any:`InstallationFinishedEvent`
    :return: None
    """
    if not InstantiationFinishedEvent.is_error(event.result):
      log.getChild('API').info(
        "NF-FG(%s) instantiation has been finished successfully with result: "
        "%s!" % (event.id, event.result))
    else:
      log.getChild('API').error(
        "NF-FG(%s) instantiation has been finished with error result: %s!" %
        (event.id, event.result))
    self.__handle_mapping_result(nffg_id=event.id,
                                 fail=BaseResultEvent.is_error(event.result))
    self.raiseEventNoErrors(InstantiationFinishedEvent,
                            id=event.id,
                            result=event.result)
