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
from escape import CONFIG
from escape.nffg_lib.nffg import NFFG
from escape.orchest import LAYER_NAME, log as log  # Orchestration layer logger
from escape.orchest.ros_orchestration import ResourceOrchestrator
from escape.util.api import AbstractAPI, RESTServer, AbstractRequestHandler
from escape.util.conversion import NFFGConverter
from escape.util.misc import schedule_as_coop_task, notify_remote_visualizer, \
  VERBOSE
from pox.lib.revent.revent import Event
from virtualizer import Virtualizer


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
    """
    super(InstallNFFGEvent, self).__init__()
    self.mapped_nffg = mapped_nffg


class VirtResInfoEvent(Event):
  """
  Event for sending back requested Virtual view an a specific Virtualizer.
  """

  def __init__ (self, virtualizer):
    """
    Init

    :param virtualizer: virtual resource info
    :type virtualizer: :any:`AbstractVirtualizer`
    """
    super(VirtResInfoEvent, self).__init__()
    self.virtualizer = virtualizer


class GetGlobalResInfoEvent(Event):
  """
  Event for requesting :class:`DomainVirtualizer` from CAS.
  """
  pass


class InstantiationFinishedEvent(Event):
  """
  Event for signalling end of mapping process finished with success.
  """

  def __init__ (self, id, result, error=None):
    super(InstantiationFinishedEvent, self).__init__()
    self.id = id
    self.result = result
    self.error = error


class ROSAgentRequestHandler(AbstractRequestHandler):
  """
  Request Handler for agent behaviour in Resource Orchestration SubLayer.

  .. warning::
    This class is out of the context of the recoco's co-operative thread
    context! While you don't need to worry much about synchronization between
    recoco tasks, you do need to think about synchronization between recoco task
    and normal threads. Synchronisation is needed to take care manually: use
    relevant helper function of core object: `callLater`/`raiseLater` or use
    `schedule_as_coop_task` decorator defined in util.misc on the called
    function.

  Contains handler functions for REST-API.
  """
  # Bind HTTP verbs to UNIFY's API functions
  request_perm = {
    'GET': ('ping', 'version', 'operations', 'get_config'),
    'POST': ('ping', 'get_config', 'edit_config')
  }
  # Statically defined layer component to which this handler is bounded
  # Need to be set by container class
  bounded_layer = 'orchestration'
  # Set special prefix to imitate OpenStack agent API
  static_prefix = "escape"
  # Logger name
  LOGGER_NAME = "Sl-Or"
  log = log.getChild("[%s]" % LOGGER_NAME)
  # Use Virtualizer format
  virtualizer_format_enabled = False
  # Default communication approach
  DEFAULT_DIFF = False
  # Name mapper to avoid Python naming constraint
  rpc_mapper = {
    'get-config': "get_config",
    'edit-config': "edit_config"
  }
  API_CALL_GET_CONFIG = 'api_ros_get_config'
  API_CALL_EDIT_CONFIG = 'api_ros_edit_config'

  def __init__ (self, request, client_address, server):
    """
    Init.
    """
    AbstractRequestHandler.__init__(self, request, client_address, server)

  def get_config (self):
    """
    Response configuration.

    :return: None
    """
    self.log.info("Call %s function: get-config" % self.LOGGER_NAME)
    # Forward call to main layer class
    config = self._proceed_API_call(self.API_CALL_GET_CONFIG)
    if config is None:
      self.send_error(404, message="Resource info is missing!")
      return
    # Setup OK status for HTTP response
    self.send_response(200)
    # Global resource has not changed -> respond with the cached topo
    if config is False:
      self.log.info(
        "Global resource has not changed! Respond with cached topology...")
      if self.virtualizer_format_enabled:
        data = self.server.last_response.xml()
      else:
        data = self.server.last_response.dump()
    else:
      # Convert required NFFG if needed
      if self.virtualizer_format_enabled:
        self.log.debug("Convert internal NFFG to Virtualizer...")
        converter = NFFGConverter(domain=None, logger=log)
        v_topology = converter.dump_to_Virtualizer(nffg=config)
        # Cache converted data for edit-config patching
        self.log.debug("Cache converted topology...")
        self.server.last_response = v_topology
        # Dump to plain text format
        data = v_topology.xml()
        # Setup HTTP response format
      else:
        self.log.debug("Cache acquired topology...")
        self.server.last_response = config
        data = config.dump()
    if self.virtualizer_format_enabled:
      self.send_header('Content-Type', 'application/xml')
    else:
      self.send_header('Content-Type', 'application/json')
    self.log.log(VERBOSE, "Responded topology for 'get-config':\n%s" % data)
    # Setup length for HTTP response
    self.send_header('Content-Length', len(data))
    self.end_headers()
    self.log.info("Send back topology description...")
    self.wfile.write(data)
    self.log.debug("%s function: get-config ended!" % self.LOGGER_NAME)

  def edit_config (self):
    """
    Receive configuration and initiate orchestration.

    :return: None
    """
    self.log.info("Call %s function: edit-config" % self.LOGGER_NAME)
    # Obtain NFFG from request body
    self.log.debug("Detected response format: %s" %
                   self.headers.get("Content-Type"))
    raw_body = self._get_body()
    # log.getChild("REST-API").debug("Request body:\n%s" % body)
    if raw_body is None or not raw_body:
      log.warning("Received data is empty!")
      self.send_error(400, "Missing body!")
      return
    # Expect XML format --> need to convert first
    if self.virtualizer_format_enabled:
      if self.headers.get("Content-Type") != "application/xml" and \
         not raw_body.startswith("<?xml version="):
        self.log.error("Received data is not in XML format despite of the "
                       "UNIFY interface is enabled!")
        self.send_error(415)
        return
      # Get received Virtualizer
      received_cfg = Virtualizer.parse_from_text(text=raw_body)
      self.log.log(VERBOSE,
                   "Received request for 'edit-config':\n%s" % raw_body)
      # If there was not get-config request so far
      if self.DEFAULT_DIFF:
        if self.server.last_response is None:
          self.log.info("Missing cached Virtualizer! Acquiring topology now...")
          config = self._proceed_API_call(self.API_CALL_GET_CONFIG)
          if config is None:
            self.log.error("Requested resource info is missing!")
            self.send_error(404, message="Resource info is missing!")
            return
          elif config is False:
            self.log.warning("Requested info is unchanged but has not found!")
            self.send_error(404, message="Resource info is missing!")
          else:
            # Convert required NFFG if needed
            if self.virtualizer_format_enabled:
              self.log.debug("Convert internal NFFG to Virtualizer...")
              converter = NFFGConverter(domain=None, logger=log)
              v_topology = converter.dump_to_Virtualizer(nffg=config)
              # Cache converted data for edit-config patching
              self.log.debug("Cache converted topology...")
              self.server.last_response = v_topology
            else:
              self.log.debug("Cache acquired topology...")
              self.server.last_response = config
        # Perform patching
        full_cfg = self.__recreate_full_request(diff=received_cfg)
      else:
        full_cfg = received_cfg
      self.log.log(VERBOSE, "Generated request:\n%s" % full_cfg.xml())
      # Convert response's body to NFFG
      self.log.info("Converting full request data...")
      converter = NFFGConverter(domain="REMOTE", logger=log)
      nffg = converter.parse_from_Virtualizer(vdata=full_cfg)
    else:
      if self.headers.get("Content-Type") != "application/json":
        self.log.error("Received data is not in JSON format despite of the "
                       "UNIFY interface is disabled!")
        self.send_error(415)
        return
      # Initialize NFFG from JSON representation
      self.log.info("Parsing request into internal NFFG format...")
      nffg = NFFG.parse(raw_body)
    self.log.debug("Parsed NFFG install request: %s" % nffg)
    self._proceed_API_call(self.API_CALL_EDIT_CONFIG, nffg)
    self.send_acknowledge()
    self.log.debug("%s function: edit-config ended!" % self.LOGGER_NAME)

  def __recreate_full_request (self, diff):
    """
    Recreate the full domain install request based on previously sent
    topology config and received diff request.

    :return: recreated request
    :rtype: :any:`NFFG`
    """
    self.log.info("Patching cached topology with received diff...")
    full_request = self.server.last_response.full_copy()
    full_request.bind(relative=True)
    # Do not call bind on diff to avoid resolve error in Virtualizer
    # diff.bind(relative=True)
    # Adapt changes on  the local config
    full_request.patch(source=diff)
    # full_request.bind(relative=True)
    # return full_request
    # Perform hack to resolve inconsistency
    return Virtualizer.parse_from_text(full_request.xml())


class CfOrRequestHandler(ROSAgentRequestHandler):
  """
  Request Handler for the Cf-OR interface.

  .. warning::
    This class is out of the context of the recoco's co-operative thread
    context! While you don't need to worry much about synchronization between
    recoco tasks, you do need to think about synchronization between recoco task
    and normal threads. Synchronisation is needed to take care manually: use
    relevant helper function of core object: `callLater`/`raiseLater` or use
    `schedule_as_coop_task` decorator defined in util.misc on the called
    function.

  Contains handler functions for REST-API.
  """
  # Bind HTTP verbs to UNIFY's API functions
  request_perm = {
    'GET': ('ping', 'version', 'operations', 'get_config'),
    'POST': ('ping', 'get_config', 'edit_config')
  }
  # Statically defined layer component to which this handler is bounded
  # Need to be set by container class
  bounded_layer = 'orchestration'
  static_prefix = "cfor"
  # Logger name
  LOGGER_NAME = "Cf-Or"
  log = log.getChild("[%s]" % LOGGER_NAME)
  # Use Virtualizer format
  virtualizer_format_enabled = False
  # Default communication approach
  DEFAULT_DIFF = False
  # Name mapper to avoid Python naming constraint
  rpc_mapper = {
    'get-config': "get_config",
    'edit-config': "edit_config"
  }
  API_CALL_GET_CONFIG = 'api_cfor_get_config'
  API_CALL_EDIT_CONFIG = 'api_cfor_edit_config'

  def __init__ (self, request, client_address, server):
    """
    Init.
    """
    ROSAgentRequestHandler.__init__(self, request, client_address, server)

  def get_config (self):
    """
    Response configuration.
    """
    # self.log.info("Call %s function: get-config" % self.LOGGER_NAME)
    # # Obtain NFFG from request body
    # self.log.debug("Detected response format: %s" %
    #                self.headers.get("Content-Type"))
    # config = self._proceed_API_call('api_cfor_get_config')
    # if config is None:
    #   self.send_error(404, message="Resource info is missing!")
    #   return
    # self.send_response(200)
    # data = config.dump()
    # self.log.log(VERBOSE, "Generated config for 'get-config:\n%s" % data)
    # self.send_header('Content-Type', 'application/json')
    # self.send_header('Content-Length', len(data))
    # self.end_headers()
    # self.log.info("Send back topology description...")
    # self.wfile.write(data)
    # self.log.debug("%s function: get-config ended!" % self.LOGGER_NAME)
    super(CfOrRequestHandler, self).get_config()

  def edit_config (self):
    """
    Receive configuration and initiate orchestration.
    """
    # self.log.info("Call %s function: edit-config" % self.LOGGER_NAME)
    # body = self._get_body()
    # # log.getChild("REST-API").debug("Request body:\n%s" % body)
    # nffg = NFFG.parse(body)  # Initialize NFFG from JSON representation
    # self.log.log(VERBOSE, "Received request for 'edit-config':\n%s" % nffg)
    # self._proceed_API_call('api_cfor_edit_config', nffg)
    # self.send_acknowledge()
    # self.log.debug("%s function: edit-config ended!" % self.LOGGER_NAME)
    super(CfOrRequestHandler, self).edit_config()


class ResourceOrchestrationAPI(AbstractAPI):
  """
  Entry point for Resource Orchestration Sublayer (ROS).

  Maintain the contact with other UNIFY layers.

  Implement the Sl - Or reference point.
  """
  # Define specific name for core object i.e. pox.core.<_core_name>
  _core_name = LAYER_NAME
  # Events raised by this class
  _eventMixin_events = {InstallNFFGEvent, GetGlobalResInfoEvent,
                        VirtResInfoEvent, InstantiationFinishedEvent}
  # Dependencies
  dependencies = ('adaptation',)

  def __init__ (self, standalone=False, **kwargs):
    """
    .. seealso::
      :func:`AbstractAPI.__init__() <escape.util.api.AbstractAPI.__init__>`
    """
    log.info("Starting Resource Orchestration Sublayer...")
    # Mandatory super() call
    self.resource_orchestrator = None
    super(ResourceOrchestrationAPI, self).__init__(standalone, **kwargs)

  def initialize (self):
    """
    .. seealso::
      :func:`AbstractAPI.initialize() <escape.util.api.AbstractAPI.initialize>`
    """
    log.debug("Initializing Resource Orchestration Sublayer...")
    self.resource_orchestrator = ResourceOrchestrator(self)
    if self._nffg_file:
      try:
        service_request = self._read_data_from_file(self._nffg_file)
        service_request = NFFG.parse(service_request)
        self.__proceed_instantiation(nffg=service_request)
      except (ValueError, IOError, TypeError) as e:
        log.error("Can't load service request from file because of: " + str(e))
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
      handler.prefix = params['prefix']
    if 'unify_interface' in params:
      handler.virtualizer_format_enabled = params['unify_interface']
    if 'diff' in params:
      handler.DEFAULT_DIFF = bool(params['diff'])
    address = (params.get('address'), params.get('port'))
    # Virtualizer ID of the Sl-Or interface
    self.ros_api = RESTServer(handler, *address)
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
      handler.prefix = params['prefix']
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

  def api_ros_get_config (self):
    """
    Implementation of REST-API RPC: get-config. Return with the global
    resource as an :any:`NFFG` if it has been changed otherwise return with
    False.

    :return: global resource view (DoV)
    :rtype: :any:`NFFG` or False
    """
    log.getChild('[Sl-Or]').info("Requesting Virtualizer for REST-API")
    virt = self.resource_orchestrator.virtualizerManager.get_virtual_view(
      virtualizer_id=self.ros_api.api_id, type=self.ros_api.virtualizer_type)
    if virt is not None:
      # Check if the resource is changed
      if virt.is_changed():
        log.getChild('[Sl-Or]').info("Generate topo description...")
        res = virt.get_resource_info()
        return res
      # If resource has not been changed return False
      # This causes to response with the cached topology
      else:
        return False
    else:
      log.error("Virtualizer(id=%s) assigned to REST-API is not found!" %
                self.ros_api.api_id)

  def api_ros_edit_config (self, nffg):
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
    # ESCAPE serves as a global or proxy orchestrator
    self.__proceed_instantiation(nffg=nffg)

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
      local_mgr = CONFIG.get_local_manager()
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

  ##############################################################################
  # Cf-Or API functions starts here
  ##############################################################################

  def api_cfor_get_config (self):
    """
    Implementation of Cf-Or REST-API RPC: get-config.

    :return: dump of a single BiSBiS view based on DoV
    :rtype: str
    """
    log.getChild('[Cf-Or]').info("Requesting Virtualizer for REST-API...")
    virt = self.resource_orchestrator.virtualizerManager.get_virtual_view(
      virtualizer_id=self.cfor_api.api_id, type=self.cfor_api.virtualizer_type)
    if virt is not None:
      log.getChild('[Cf-Or]').info("Generate topo description...")
      return virt.get_resource_info()
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
    self.__proceed_instantiation(nffg=nffg)

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
    self.__proceed_instantiation(nffg=event.nffg)

  @schedule_as_coop_task
  def __proceed_instantiation (self, nffg):
    """
    Helper function to instantiate the NFFG mapping from different source.

    :param nffg: pre-mapped service request
    :type nffg: :any:`NFFG`
    :return: None
    """
    log.getChild('API').info("Invoke instantiate_nffg on %s with NF-FG: %s " % (
      self.__class__.__name__, nffg.name))
    # Initiate request mapping
    mapped_nffg = self.resource_orchestrator.instantiate_nffg(nffg=nffg)
    log.getChild('API').debug("Invoked instantiate_nffg on %s is finished" %
                              self.__class__.__name__)
    # If mapping is not threaded and finished with OK
    if mapped_nffg is not None and not \
       self.resource_orchestrator.mapper.threaded:
      self._proceed_to_install_NFFG(mapped_nffg=mapped_nffg)
    else:
      log.warning("Something went wrong in service request instantiation: "
                  "mapped service request is missing!")

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
    v = self.resource_orchestrator.virtualizerManager.get_virtual_view(
      event.sid, type=virtualizer_type)
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
    self.resource_orchestrator.virtualizerManager.dov = event.dov

  def _handle_InstallationFinishedEvent (self, event):
    """
    Get information from NFFG installation process.

    :param event: event object info
    :type event: :any:`InstallationFinishedEvent`
    :return: None
    """
    if event.result:
      log.getChild('API').info(
        "NF-FG instantiation has been finished successfully!")
    else:
      log.getChild('API').error(
        "NF-FG instantiation has been finished with error!")
    self.raiseEventNoErrors(InstantiationFinishedEvent, id=event.id,
                            result=event.result)
