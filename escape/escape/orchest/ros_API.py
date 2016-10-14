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
from escape.nffg_lib.nffg import NFFG, NFFGToolBox
from escape.orchest import LAYER_NAME, log as log  # Orchestration layer logger
from escape.orchest.ros_orchestration import ResourceOrchestrator
from escape.util.api import AbstractAPI, RESTServer, AbstractRequestHandler
from escape.util.conversion import NFFGConverter
from escape.util.domain import BaseResultEvent
from escape.util.mapping import ProcessorError
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


class BasicUnifyRequestHandler(AbstractRequestHandler):
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
    'POST': ('ping', 'get_config', 'edit_config'),
    # 'DELETE': ('edit_config',),
    'PUT': ('edit_config',)
  }
  # Statically defined layer component to which this handler is bounded
  # Need to be set by container class
  bounded_layer = 'orchestration'
  """Statically defined layer component to which this handler is bounded"""
  # Set special prefix to imitate OpenStack agent API
  static_prefix = "escape"
  """ special prefix to imitate OpenStack agent API"""
  # Logger name
  LOGGER_NAME = "Sl-Or"
  """Logger name"""
  log = log.getChild("[%s]" % LOGGER_NAME)
  # Use Virtualizer format
  virtualizer_format_enabled = True
  """Use Virtualizer format"""
  # Default communication approach
  DEFAULT_DIFF = True
  """Default communication approach"""
  # Name mapper to avoid Python naming constraint
  rpc_mapper = {
    'get-config': "get_config",
    'edit-config': "edit_config"
  }
  """ Name mapper to avoid Python naming constraint"""
  # Bound function
  API_CALL_RESOURCE = 'api_ros_get_config'
  API_CALL_REQUEST = 'api_ros_edit_config'

  def __init__ (self, request, client_address, server):
    """
    Init.

    :param request: request type
    :type request: str
    :param client_address: client address
    :type client_address: str
    :param server: server object
    :type server: :any:`BaseHTTPServer.HTTPServer`
    :return: None
    """
    AbstractRequestHandler.__init__(self, request, client_address, server)

  def get_config (self):
    """
    Response configuration.

    :return: None
    """
    self.log.debug("Call %s function: get-config" % self.LOGGER_NAME)
    # Forward call to main layer class
    resource = self._proceed_API_call(self.API_CALL_RESOURCE)
    self._topology_view_responder(resource_nffg=resource)
    self.log.debug("%s function: get-config ended!" % self.LOGGER_NAME)

  def edit_config (self):
    """
    Receive configuration and initiate orchestration.

    :return: None
    """
    self.log.debug("Call %s function: edit-config" % self.LOGGER_NAME)
    nffg = self._service_request_parser()
    if nffg:
      self._proceed_API_call(self.API_CALL_REQUEST, nffg)
      self.send_acknowledge(id=nffg.id)
    self.log.debug("%s function: edit-config ended!" % self.LOGGER_NAME)

  def _topology_view_responder (self, resource_nffg):
    """
    Process the required topology data and sent back to the REST client.

    :param resource_nffg: required data
    :type resource_nffg: :any: `NFFG`
    :return: None
    """
    if resource_nffg is None:
      self.send_error(404, message="Resource info is missing!")
      return
    # Setup OK status for HTTP response
    self.send_response(200)
    # Global resource has not changed -> respond with the cached topo
    if resource_nffg is False:
      self.log.debug(
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
        v_topology = converter.dump_to_Virtualizer(nffg=resource_nffg)
        # Cache converted data for edit-config patching
        self.log.debug("Cache converted topology...")
        self.server.last_response = v_topology
        # Dump to plain text format
        data = v_topology.xml()
        # Setup HTTP response format
      else:
        self.log.debug("Cache acquired topology...")
        self.server.last_response = resource_nffg
        data = resource_nffg.dump()
    if self.virtualizer_format_enabled:
      self.send_header('Content-Type', 'application/xml')
    else:
      self.send_header('Content-Type', 'application/json')
    # Setup length for HTTP response
    self.send_header('Content-Length', len(data))
    self.end_headers()
    self.log.debug("Send back topology description...")
    self.wfile.write(data)
    self.log.log(VERBOSE, "Responded topology:\n%s" % data)

  def _service_request_parser (self):
    """
    Process the received service request.

    :return: Parsed service request
    :rtype: :any:`NFFG`
    """
    # Obtain NFFG from request body
    self.log.debug("Detected message format: %s" %
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
      self.log.log(VERBOSE, "Received request:\n%s" % raw_body)
      # If there was not get-config request so far
      if self.DEFAULT_DIFF:
        if self.server.last_response is None:
          self.log.info("Missing cached Virtualizer! Acquiring topology now...")
          config = self._proceed_API_call(self.API_CALL_RESOURCE)
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
    if nffg.mode:
      self.log.info(
        "Detected mapping mode in request body: %s" % nffg.mode)
    else:
      command = self.command.upper()
      if command == 'POST':
        nffg.mode = NFFG.MODE_ADD
        self.log.debug(
          'Add mapping mode: %s based on HTTP verb: %s' % (nffg.mode, command))
      elif command == 'PUT':
        nffg.mode = NFFG.MODE_DEL
        self.log.debug(
          'Add mapping mode: %s based on HTTP verb: %s' % (nffg.mode, command))
      else:
        self.log.info('No mode parameter has benn defined in body!')
    self.log.debug("Parsed NFFG install request: %s" % nffg)
    return nffg

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


class CfOrRequestHandler(BasicUnifyRequestHandler):
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
  """Bind HTTP verbs to UNIFY's API functions"""
  # Statically defined layer component to which this handler is bounded
  # Need to be set by container class
  bounded_layer = 'orchestration'
  """Statically defined layer component to which this handler is bounded"""
  static_prefix = "cfor"
  # Logger name
  LOGGER_NAME = "Cf-Or"
  """Logger name"""
  log = log.getChild("[%s]" % LOGGER_NAME)
  # Use Virtualizer format
  virtualizer_format_enabled = True
  """Use Virtualizer format"""
  # Default communication approach
  DEFAULT_DIFF = True
  """Default communication approach"""
  # Name mapper to avoid Python naming constraint
  rpc_mapper = {
    'get-config': "get_config",
    'edit-config': "edit_config"
  }
  """Name mapper to avoid Python naming constraint"""
  # Bound function
  API_CALL_RESOURCE = 'api_cfor_get_config'
  API_CALL_REQUEST = 'api_cfor_edit_config'

  def __init__ (self, request, client_address, server):
    """
    Init.

    :param request: request type
    :type request: str
    :param client_address: client address
    :type client_address: str
    :param server: server object
    :type server: :any:`BaseHTTPServer.HTTPServer`
    :return: None
    """
    BasicUnifyRequestHandler.__init__(self, request, client_address, server)

  def get_config (self):
    """
    Response configuration.

    :return: None
    """
    self.log.debug("Call %s function: get-config" % self.LOGGER_NAME)
    # Forward call to main layer class
    resource = self._proceed_API_call(self.API_CALL_RESOURCE)
    self._topology_view_responder(resource_nffg=resource)
    self.log.debug("%s function: get-config ended!" % self.LOGGER_NAME)

  def edit_config (self):
    """
    Receive configuration and initiate orchestration.

    :return: None
    """
    self.log.debug("Call %s function: edit-config" % self.LOGGER_NAME)
    nffg = self._service_request_parser()
    if nffg:
      self._proceed_API_call(self.API_CALL_REQUEST, nffg)
      self.send_acknowledge(id=nffg.id)
    self.log.debug("%s function: edit-config ended!" % self.LOGGER_NAME)


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
                        VirtResInfoEvent, InstantiationFinishedEvent}
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
        dov = self.resource_orchestrator.virtualizerManager.dov
        self.__proceed_instantiation(nffg=service_request,
                                     resource_view=dov.get_resource_info())
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
    self.resource_orchestrator.finalize()
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

  def __get_slor_resource_view (self):
    """
    Return with the Virtualizer object assigned to the Sl-Or interface.
    """
    virt_mgr = self.resource_orchestrator.virtualizerManager
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

  ##############################################################################
  # Cf-Or API functions starts here
  ##############################################################################

  def __get_cfor_resource_view (self):
    """
    Return with the Virtualizer object assigned to the Cf-Or interface.

    :return: Virtualizer of Cf-Or interface
    :rtype: :any:`AbstractVirtualizer`
    """
    virt_mgr = self.resource_orchestrator.virtualizerManager
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
      log.log(VERBOSE, "New NFFG:\n%s" % nffg.dump())
      log.log(VERBOSE, "Resource NFFG:\n%s" % resource_nffg.dump())
      add_nffg, del_nffg = NFFGToolBox.generate_difference_of_nffgs(
        old=resource_nffg, new=nffg)
      log.log(VERBOSE, "Calculated ADD NFFG:\n%s" % add_nffg.dump())
      log.log(VERBOSE, "Calculated DEL NFFG:\n%s" % del_nffg.dump())
      if not add_nffg.is_empty() and del_nffg.is_empty():
        nffg = add_nffg
        log.info("Calculated mapping mode: %s" % nffg.mode)
      elif add_nffg.is_empty() and not del_nffg.is_empty():
        nffg = del_nffg
        log.info("Calculated mapping mode: %s" % nffg.mode)
      elif not add_nffg.is_empty() and not del_nffg.is_empty():
        log.warning("Both ADD / DEL mode is not supported currently")
        return
      else:
        log.debug("Difference calculation resulted empty subNFFGs!")
        log.info("No change has been detected in request! Skip mapping...")
        log.getChild('API').debug("Invoked instantiate_nffg on %s is finished!"
                                  % self.__class__.__name__)
        return
    else:
      log.debug("Mode: %s detected from config! Skip difference calculation..."
                % mapping_mode)
    try:
      # Initiate request mapping
      mapped_nffg = self.resource_orchestrator.instantiate_nffg(nffg=nffg)
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
         self.resource_orchestrator.mapper.threaded:
        self._proceed_to_install_NFFG(mapped_nffg=mapped_nffg)
      else:
        log.warning("Something went wrong in service request instantiation: "
                    "mapped service request is missing!")
        self.raiseEventNoErrors(InstantiationFinishedEvent,
                                id=nffg.id,
                                result=InstantiationFinishedEvent.MAPPING_ERROR)
    except ProcessorError as e:
      self.raiseEventNoErrors(InstantiationFinishedEvent,
                              id=nffg.id,
                              result=InstantiationFinishedEvent.REFUSED_BY_VERIFICATION,
                              error=e)

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
    if not InstantiationFinishedEvent.is_error(event.result):
      log.getChild('API').info(
        "NF-FG instantiation has been finished successfully with result: %s!" %
        event.result)
    else:
      log.getChild('API').error(
        "NF-FG instantiation has been finished with error result: %s!" %
        event.result)
    self.raiseEventNoErrors(InstantiationFinishedEvent,
                            id=event.id,
                            result=event.result)
