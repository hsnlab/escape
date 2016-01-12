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
from escape.orchest import LAYER_NAME
from escape.orchest import log as log  # Orchestration layer logger
from escape.orchest.ros_orchestration import ResourceOrchestrator
from escape.util.api import AbstractAPI, RESTServer, AbstractRequestHandler
from escape.util.conversion import NFFGConverter
from escape.util.misc import schedule_as_coop_task
from escape.util.nffg import NFFG
from pox.lib.revent.revent import Event


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


class CfOrRequestHandler(AbstractRequestHandler):
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
  # Logger. Must define.
  log = log.getChild("[Cf-Or]")
  # Name mapper to avoid Python naming constraint
  rpc_mapper = {
    'get-config': "get_config",
    'edit-config': "edit_config"
  }

  def __init__ (self, request, client_address, server):
    """
    Init.
    """
    AbstractRequestHandler.__init__(self, request, client_address, server)

  def get_config (self):
    """
    Response configuration.
    """
    log.info("Call Cf-Or function: get-config")
    config = self._proceed_API_call('api_cfor_get_config')
    if config is None:
      self.send_error(404, message="Resource info is missing!")
      return
    self.send_response(200)
    data = config.dump()
    self.send_header('Content-Type', 'application/json')
    self.send_header('Content-Length', len(data))
    self.end_headers()
    self.wfile.write(data)

  def edit_config (self):
    """
    Receive configuration and initiate orchestration.
    """
    log.info("Call Cf-Or function: edit-config")
    body = self._get_body()
    # log.getChild("REST-API").debug("Request body:\n%s" % body)
    nffg = NFFG.parse(body)  # Initialize NFFG from JSON representation
    log.debug("Parsed NFFG request: %s" % nffg)
    self._proceed_API_call('api_cfor_edit_config', nffg)
    self.send_acknowledge()


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
  # Logger. Must define.
  log = log.getChild("[Sl-Or]")
  # Use Virtualizer format
  virtualizer_format_enabled = False
  # Name mapper to avoid Python naming constraint
  rpc_mapper = {
    'get-config': "get_config",
    'edit-config': "edit_config"
  }

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
    log.info("Call REST-API function: get-config")
    # Forward call to main layer class
    config = self._proceed_API_call('api_ros_get_config')
    if config is None:
      self.send_error(404, message="Resource info is missing!")
      return
    # Setup OK status for HTTP response
    self.send_response(200)
    # Convert required NFFG if needed
    if self.virtualizer_format_enabled:
      converter = NFFGConverter(domain=None, logger=log)
      # Dump to plain text format
      data = converter.dump_to_Virtualizer3(nffg=config).xml()
      # Setup HTTP response format
      self.send_header('Content-Type', 'application/xml')
    else:
      data = config.dump()
      self.send_header('Content-Type', 'application/json')
    # Setup length for HTTP response
    self.send_header('Content-Length', len(data))

    self.end_headers()
    self.wfile.write(data)

  def edit_config (self):
    """
    Receive configuration and initiate orchestration.

    :return: None
    """
    log.info("Call REST-API function: edit-config")
    # Obtain NFFG from request body
    log.debug("Detected response format: %s" %
              self.headers.get("Content-Type", ""))
    body = self._get_body()
    # log.getChild("REST-API").debug("Request body:\n%s" % body)
    # Expect XML format --> need to convert first
    if self.virtualizer_format_enabled:
      if self.headers.get("Content-Type", "") != "application/xml" or \
         not body.startswith("<?xml version="):
        log.error(
           "Received data is not in XML format despite of the UNIFY "
           "interface is enabled!")
        self.send_error(415)
        return
      # Convert response's body to NFFG
      nffg = NFFGConverter(domain="REMOTE",
                           logger=log).parse_from_Virtualizer3(xml_data=body)
    else:
      nffg = NFFG.parse(body)  # Initialize NFFG from JSON representation
    # Rewrite domain name to INTERNAL
    # nffg = self._update_REMOTE_ESCAPE_domain(nffg_part=nffg)
    log.debug("Parsed NFFG install request: %s" % nffg)
    self._proceed_API_call('api_ros_edit_config', nffg)

    self.send_acknowledge()


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
        log.error(
           "Can't load service request from file because of: " + str(e))
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
    """
    log.info("Resource Orchestration Sublayer is going down...")
    if self._agent or self._rosapi:
      log.debug("REST-API [Sl-Or] is shutting down...")
      # self.ros_api.stop()
    if self._cfor:
      log.debug("REST-API [Cf-Or] is shutting down...")
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
    # can override from global config
    handler.prefix = CONFIG.get_ros_agent_prefix()
    handler.virtualizer_format_enabled = CONFIG.get_ros_api_virtualizer_format()
    address = CONFIG.get_ros_agent_address()
    self.ros_api = RESTServer(handler, *address)
    # Virtualizer ID of the Sl-Or interface
    self.ros_api.api_id = "Sl-Or"
    # Virtualizer type for Sl-Or API
    self.ros_api.virtualizer_type = CONFIG.get_api_virtualizer(
       layer_name=LAYER_NAME, api_name=self.ros_api.api_id)
    handler.log.info(
       "Init REST-API [Sl-Or] on %s:%s!" % (address[0], address[1]))
    self.ros_api.start()
    handler.log.debug(
       "Configured Virtualizer type: %s!" % self.ros_api.virtualizer_type)
    handler.log.debug(
       "Configured communication format: %s!" %
       handler.virtualizer_format_enabled)
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
    # can override from global config
    handler.prefix = CONFIG.get_cfor_api_prefix()
    address = CONFIG.get_cfor_api_address()
    self.cfor_api = RESTServer(handler, *address)
    # Virtualizer ID of the Cf-Or interface
    self.cfor_api.api_id = "Cf-Or"
    # Virtualizer type for Cf-Or API
    self.cfor_api.virtualizer_type = CONFIG.get_api_virtualizer(
       layer_name=LAYER_NAME, api_name=self.cfor_api.api_id)
    handler.log.debug(
       "Init REST-API [Cf-Or] on %s:%s!" % (address[0], address[1]))
    self.cfor_api.start()
    handler.log.debug(
       "Configured Virtualizer type: %s!" % self.cfor_api.virtualizer_type)

  def _handle_NFFGMappingFinishedEvent (self, event):
    """
    Handle NFFGMappingFinishedEvent and proceed with  :class:`NFFG
    <escape.util.nffg.NFFG>` installation.

    :param event: event object
    :type event: :any:`NFFGMappingFinishedEvent`
    :return: None
    """
    self._install_NFFG(event.nffg)

  ##############################################################################
  # Agent API functions starts here
  ##############################################################################

  def api_ros_get_config (self):
    """
    Implementation of REST-API RPC: get-config.

    :return: dump of global view (DoV)
    :rtype: str
    """
    log.getChild('Sl-Or').info("Requesting Virtualizer for REST-API")
    virt = self.resource_orchestrator.virtualizerManager.get_virtual_view(
       virtualizer_id=self.ros_api.api_id, type=self.ros_api.virtualizer_type)
    if virt is not None:
      log.getChild('Sl-Or').info("Generate topo description...")
      res = virt.get_resource_info()
      return res
    else:
      log.error(
         "Virtualizer(id=%s) assigned to REST-API is not found!" %
         self.ros_api.api_id)

  def api_ros_edit_config (self, nffg):
    """
    Implementation of REST-API RPC: edit-config

    :param nffg: NFFG need to deploy
    :type nffg: :any:`NFFG`
    """
    log.getChild('Sl-Or').info("Invoke install_nffg on %s with SG: %s " % (
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
    log.debug("Rewrite received NFFG domain to INTERNAL...")
    rewritten = []
    if not domain_name:
      domain_name = CONFIG.get_local_manager()
    for infra in nffg_part.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
         NFFG.TYPE_INFRA_SDN_SW):
        continue
      # if infra.domain == 'REMOTE':
      #   infra.domain = 'INTERNAL'
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
    log.getChild('Cf-Or').info("Requesting Virtualizer for REST-API")
    virt = self.resource_orchestrator.virtualizerManager.get_virtual_view(
       virtualizer_id=self.cfor_api.api_id, type=self.cfor_api.virtualizer_type)
    if virt is not None:
      log.getChild('Cf-Or').info("Generate topo description...")
      res = virt.get_resource_info()
      return res if res is not None else None
    else:
      log.error(
         "Virtualizer(id=%s) assigned to REST-API is not found!" %
         self.cfor_api.api_id)

  def api_cfor_edit_config (self, nffg):
    """
    Implementation of Cf-Or REST-API RPC: edit-config

    :param nffg: NFFG need to deploy
    :type nffg: :any:`NFFG`
    """
    log.getChild('Cf-Or').info("Invoke install_nffg on %s with SG: %s " % (
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
    mapped_nffg = self.resource_orchestrator.instantiate_nffg(nffg=nffg)
    log.getChild('API').debug(
       "Invoked instantiate_nffg on %s is finished" % self.__class__.__name__)
    # If mapping is not threaded and finished with OK
    if mapped_nffg is not None:
      self._install_NFFG(mapped_nffg=mapped_nffg)
    else:
      log.warning(
         "Something went wrong in service request instantiation: mapped "
         "service "
         "request is missing!")

  def _install_NFFG (self, mapped_nffg):
    """
    Send mapped :any:`NFFG` to Controller Adaptation Sublayer in an
    implementation-specific way.

    General function which is used from microtask and Python thread also.

    :param mapped_nffg: mapped NF-FG
    :type mapped_nffg: :any:`NFFG`
    :return: None
    """
    # Sending NF-FG to Adaptation layer as an Event
    # Exceptions in event handlers are caught by default in a non-blocking way
    self.raiseEventNoErrors(InstallNFFGEvent, mapped_nffg)
    log.getChild('API').info(
       "Mapped NF-FG: %s has been sent to Adaptation..." % mapped_nffg)

  def _handle_GetVirtResInfoEvent (self, event):
    """
    Generate virtual resource info and send back to SAS.

    :param event: event object contains service layer id
    :type event: :any:`GetVirtResInfoEvent`
    :return: None
    """
    log.getChild('API').debug(
       "Received <Virtual View> request from %s layer" % str(
          event.source._core_name).title())
    # Currently view is a Virtualizer to keep ESCAPE fast
    virtualizer_type = CONFIG.get_ros_virtualizer_type(component=event.sid)
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
       "Send <Global Resource View> request to Adaptation layer...")
    self.raiseEventNoErrors(GetGlobalResInfoEvent)

  def _handle_GlobalResInfoEvent (self, event):
    """
    Save requested Global Infrastructure View as the :class:`DomainVirtualizer`.

    :param event: event object contains resource info
    :type event: :any:`GlobalResInfoEvent`
    :return: None
    """
    log.getChild('API').debug(
       "Received <Global Resource View> from %s Layer" % str(
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
      log.getChild('API').info(
         "NF-FG instantiation has been finished with error: %s" % event.error)
    self.raiseEventNoErrors(InstantiationFinishedEvent, id=event.id,
                            result=event.result)
