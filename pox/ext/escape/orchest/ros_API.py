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
from escape.orchest.ros_orchestration import ResourceOrchestrator
from escape.orchest import log as log  # Orchestration layer logger
from escape.orchest import LAYER_NAME
from escape.service.sas_API import InstantiateNFFGEvent
from escape.util.api import AbstractAPI, RESTServer, AbstractRequestHandler
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
  Request Handler for the Cf-OR interface..

  .. warning::
    This class is out of the context of the recoco's co-operative thread
    context! While you don't need to worry much about synchronization between
    recoco tasks, you do need to think about synchronization between recoco task
    and normal threads. Synchronisation is needed to take care manually: use
    relevant helper function of core object: `callLater`/`raiseLater` or use
    `schedule_as_coop_task` decorator defined in util.misc on the called
    function.
  """
  # Bind HTTP verbs to UNIFY's API functions
  request_perm = {'GET': ('ping', 'get_config'),
                  'POST': ('ping', 'get_config', 'edit_config')}
  # Statically defined layer component to which this handler is bounded
  # Need to be set by container class
  bounded_layer = 'orchestration'
  static_prefix = "cfor"
  # Logger. Must define.
  log = log.getChild("Cf-Or")
  # Name mapper to avoid Python naming constraint
  rpc_mapper = {'get-config': "get_config",
                'edit-config': "edit_config"}

  def __init__ (self, request, client_address, server):
    """
    Init.
    """
    AbstractRequestHandler.__init__(self, request, client_address, server)

  def ping (self):
    """
    For testing REST API aliveness and reachability.
    """
    response_body = "OK"
    self.send_response(200)
    self.send_header('Content-Type', 'text/plain')
    self.send_header('Content-Length', len(response_body))
    self.send_REST_headers()
    self.end_headers()
    self.wfile.write(response_body)

  def get_config (self):
    """
    Response configuration.
    """
    log.info("Call Cf-Or function: get-config")
    config = self._proceed_API_call('api_cfor_get_config')
    self.send_response(200)
    self.send_header('Content-Type', 'application/json')
    self.send_header('Content-Length', len(config))
    self.end_headers()
    self.wfile.write(config)

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
  """
  # Bind HTTP verbs to UNIFY's API functions
  request_perm = {'GET': ('ping', 'get_config'),
                  'POST': ('ping', 'get_config', 'edit_config')}
  # Statically defined layer component to which this handler is bounded
  # Need to be set by container class
  bounded_layer = 'orchestration'
  # Set special prefix to imitate OpenStack agent API
  static_prefix = "escape"
  # Logger. Must define.
  log = log.getChild("Sl-Or-API")
  # Name mapper to avoid Python naming constraint
  rpc_mapper = {'get-config': "get_config",
                'edit-config': "edit_config"}

  def __init__ (self, request, client_address, server):
    """
    Init.
    """
    AbstractRequestHandler.__init__(self, request, client_address, server)

  def ping (self):
    """
    For testing REST API aliveness and reachability.
    """
    response_body = "OK"
    self.send_response(200)
    self.send_header('Content-Type', 'text/plain')
    self.send_header('Content-Length', len(response_body))
    self.send_REST_headers()
    self.end_headers()
    self.wfile.write(response_body)

  def get_config (self):
    """
    Response configuration.
    """
    log.info("Call REST-API function: get-config")
    config = self._proceed_API_call('api_agent_get_config')
    self.send_response(200)
    self.send_header('Content-Type', 'application/json')
    self.send_header('Content-Length', len(config))
    self.end_headers()
    self.wfile.write(config)

  def edit_config (self):
    """
    Receive configuration and initiate orchestration.
    """
    log.info("Call REST-API function: edit-config")
    body = self._get_body()
    # log.getChild("REST-API").debug("Request body:\n%s" % body)
    nffg = NFFG.parse(body)  # Initialize NFFG from JSON representation
    # Rewrite domain name to INTERNAL
    # nffg = self._update_REMOTE_ESCAPE_domain(nffg_part=nffg)
    log.debug("Parsed NFFG install request: %s" % nffg)
    self._proceed_API_call('api_agent_edit_config', nffg)
    self.send_acknowledge()

  def _update_REMOTE_ESCAPE_domain (self, nffg_part):
    """
    Update domain descriptor of infras: REMOTE -> INTERNAL

    :param nffg_part: NF-FG need to be updated
    :type nffg_part: :any:`NFFG`
    :return: updated NFFG
    :rtype: :any:`NFFG`
    """
    log.debug("Rewrite domain name of incoming NFFG to INTERNAL...")
    for infra in nffg_part.infras:
      if infra.infra_type not in (
           NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
           NFFG.TYPE_INFRA_SDN_SW):
        continue
      if infra.domain == 'REMOTE':
        infra.domain = 'INTERNAL'
    return nffg_part


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
      self._read_json_from_file(self._nffg_file)
    # Initiate ROS REST-API if needed
    if self._agent or self._rosapi:
      self._initiate_agent_api()
    # Initiate Cf-Or REST-API if needed
    if self._cfor:
      self._initiate_cfor_api()
    # self._initiate_agent_api()
    log.info("Resource Orchestration Sublayer has been initialized!")

  def shutdown (self, event):
    """
    .. seealso::
      :func:`AbstractAPI.shutdown() <escape.util.api.AbstractAPI.shutdown>`
    """
    log.info("Resource Orchestration Sublayer is going down...")
    if hasattr(self, 'agent_api') and self.agent_api:
      self.agent_api.stop()

  def _initiate_agent_api (self):
    """
    Initialize and setup REST API in a different thread.

    :return: None
    """
    # set bounded layer name here to avoid circular dependency problem
    handler = CONFIG.get_ros_agent_class()
    handler.bounded_layer = self._core_name
    # can override from global config
    handler.prefix = CONFIG.get_ros_agent_prefix()
    self.agent_api = RESTServer(handler, *CONFIG.get_ros_agent_address())
    self.agent_api.start()

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
    self.cfor_api = RESTServer(handler, *CONFIG.get_cfor_api_address())
    self.cfor_api.start()

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

  def api_agent_get_config (self):
    """
    Implementation of REST-API RPC: get-config.

    :return: dump of global view (DoV)
    :rtype: str
    """
    log.getChild('API').info("Generate Single BiSBiS topo description...")
    dov = self.resource_orchestrator.virtualizerManager.dov
    if dov is not None:
      return dov.get_resource_info().dump()

  class InstallEventHelper(object):
    """
    Helper class for emulating event.
    """
    _core_name = "RemoteESCAPE"

  def api_agent_edit_config (self, nffg):
    """
    Implementation of REST-API RPC: edit-config

    :param nffg: NFFG need to deploy
    :type nffg: :any:`NFFG`
    """
    log.getChild('API').info("Invoke install_nffg on %s with SG: %s " % (
      self.__class__.__name__, nffg))
    event = InstantiateNFFGEvent(nffg=nffg)
    event.source = self.InstallEventHelper
    self._handle_InstantiateNFFGEvent(event=event)

  ##############################################################################
  # Cf-Or API functions starts here
  ##############################################################################

  def api_cfor_get_config (self):
    """
    Implementation of Cf-Or REST-API RPC: get-config.

    :return: dump of a single BiSBiS view based on DoV
    :rtype: str
    """
    # Request SingleBiSBiS for Cf-Or interface
    if "CfOr" in self.resource_orchestrator.virtualizerManager._virtualizers:
      view = self.resource_orchestrator.virtualizerManager.get_virtual_view(
        "CfOr")
    else:
      view = self.resource_orchestrator.virtualizerManager.generate_single_view(
        "CfOr")
    return view.get_resource_info().dump()

  def api_cfor_edit_config (self, nffg):
    """
    Implementation of Cf-Or REST-API RPC: edit-config

    :param nffg: NFFG need to deploy
    :type nffg: :any:`NFFG`
    """
    log.getChild('API').info("Invoke install_nffg on %s with SG: %s " % (
      self.__class__.__name__, nffg))
    event = InstantiateNFFGEvent(nffg=nffg)
    event.source = self.InstallEventHelper
    self._handle_InstantiateNFFGEvent(event=event)

  ##############################################################################
  # UNIFY Sl- Or API functions starts here
  ##############################################################################

  @schedule_as_coop_task
  def _handle_InstantiateNFFGEvent (self, event):
    """
    Instantiate given NF-FG (UNIFY Sl - Or API).

    :param event: event object contains NF-FG
    :type event: :any:`InstantiateNFFGEvent`
    :return: None
    """
    log.getChild('API').info("Received NF-FG: %s from %s layer" % (
      event.nffg, str(event.source._core_name).title()))
    log.getChild('API').info("Invoke instantiate_nffg on %s with NF-FG: %s " % (
      self.__class__.__name__, event.nffg.name))
    mapped_nffg = self.resource_orchestrator.instantiate_nffg(event.nffg)
    log.getChild('API').debug(
      "Invoked instantiate_nffg on %s is finished" % self.__class__.__name__)
    # If mapping is not threaded and finished with OK
    if mapped_nffg is not None:
      self._install_NFFG(mapped_nffg)

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
    v = self.resource_orchestrator.virtualizerManager.get_virtual_view(
      event.sid)
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
