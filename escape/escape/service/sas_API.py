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
Implements the platform and POX dependent logic for the Service Adaptation
Sublayer.
"""
import json
import os
from subprocess import Popen

from escape import CONFIG
from escape.nffg_lib.nffg import NFFG, NFFGToolBox
from escape.service import LAYER_NAME, log as log  # Service layer logger
from escape.service.element_mgmt import ClickManager
from escape.service.sas_orchestration import ServiceOrchestrator
from escape.util.api import AbstractAPI, RESTServer, AbstractRequestHandler
from escape.util.conversion import NFFGConverter
from escape.util.mapping import PreMapEvent, PostMapEvent
from escape.util.misc import schedule_delayed_as_coop_task, \
  schedule_as_coop_task, notify_remote_visualizer, VERBOSE
from pox.lib.revent.revent import Event


class InstantiateNFFGEvent(Event):
  """
  Event for passing NFFG (mapped SG) to Orchestration layer.
  """

  def __init__ (self, nffg):
    """
    Init.

    :param nffg: NF-FG need to be initiated
    :type nffg: :any:`NFFG`
    """
    super(InstantiateNFFGEvent, self).__init__()
    self.nffg = nffg


class GetVirtResInfoEvent(Event):
  """
  Event for requesting virtual resource info from Orchestration layer.
  """

  def __init__ (self, sid):
    """
    Init.

    :param sid: Service layer ID
    :type sid: int
    """
    super(GetVirtResInfoEvent, self).__init__()
    # service layer ID
    self.sid = sid


class ServiceRequestHandler(AbstractRequestHandler):
  """
  Request Handler for Service Adaptation SubLayer.

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
  request_perm = {
    'GET': ('ping', 'version', 'operations', 'topology'),
    'POST': ('ping', 'result', 'sg', 'topology')
  }
  # Statically defined layer component to which this handler is bounded
  # Need to be set by container class
  bounded_layer = 'service'
  # Logger name
  LOGGER_NAME = "U-Sl"
  log = log.getChild("[%s]" % LOGGER_NAME)
  # Use Virtualizer format
  virtualizer_format_enabled = False

  def __init__ (self, request, client_address, server):
    """
    Init.
    """
    AbstractRequestHandler.__init__(self, request, client_address, server)

  def result (self):
    """
    Return the result of a request given by the id.
    """
    params = json.loads(self._get_body())
    try:
      id = params["id"]
    except:
      id = None
    res = self._proceed_API_call('get_result', id)
    self._send_json_response({'id': id, 'result': res})

  def topology (self):
    """
    Provide internal topology description

    Same functionality as "get-config" in UNIFY interface.

    :return: None
    """
    self.log.info("Call %s function: topology" % self.LOGGER_NAME)
    # Forward call to main layer class
    topology = self._proceed_API_call('api_sas_get_topology')
    if topology is None:
      self.send_error(404, message="Resource info is missing!")
      return
    # Setup OK status for HTTP response
    self.send_response(200)
    if topology is False:
      self.log.info(
        "Requested resource has not changed! Respond with cached topology...")
      if self.virtualizer_format_enabled:
        data = self.server.last_response.xml()
      else:
        data = self.server.last_response.dump()
    else:
      if self.virtualizer_format_enabled:
        self.log.debug("Convert internal NFFG to Virtualizer...")
        converter = NFFGConverter(domain=None, logger=log)
        # Dump to plain text format
        v_topology = converter.dump_to_Virtualizer(nffg=topology)
        # Cache converted data for edit-config patching
        self.log.debug("Cache converted topology...")
        self.server.last_response = v_topology
        # Dump to plain text format
        data = v_topology.xml()
        # Setup HTTP response format
      else:
        self.log.debug("Cache converted topology...")
        self.server.last_response = topology
        data = topology.dump()
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

  def sg (self):
    """
    Main API function for Service Graph initiation.

    Same functionality as "get-config" in UNIFY interface.

    Bounded to POST HTTP verb.

    :return: None
    """
    self.log.debug("Called REST-API function: sg")
    # Obtain NFFG from request body
    log.debug("Detected response format: %s" % self.headers.get("Content-Type"))
    body = self._get_body()
    # log.getChild("REST-API").debug("Request body:\n%s" % body)
    if body is None or not body:
      log.warning("Received data is empty!")
      self.send_error(400, "Missing body!")
      return
    # Expect XML format --> need to convert first
    if self.virtualizer_format_enabled:
      if self.headers.get("Content-Type") != "application/xml" or \
         not body.startswith("<?xml version="):
        log.error("Received data is not in XML format despite of the UNIFY "
                  "interface is enabled!")
        self.send_error(415)
        return
      # Convert response's body to NFFG
      nffg = NFFGConverter(domain="INTERNAL",
                           logger=log).parse_from_Virtualizer(vdata=body)
    else:
      try:
        nffg = NFFG.parse(body)  # Initialize NFFG from JSON representation
      except Exception as e:
        self.log.error(
          "Abort request! Received exception during payload parsing: %s" % e)
        return
    self.log.debug("Parsed service request: %s" % nffg)
    self._proceed_API_call('api_sas_sg_request', nffg)
    self.send_acknowledge()
    self.log.debug("%s function: get-config ended!" % self.LOGGER_NAME)


class ServiceLayerAPI(AbstractAPI):
  """
  Entry point for Service Adaptation Sublayer.

  Maintain the contact with other UNIFY layers.

  Implement the U - Sl reference point.
  """
  # Define specific name for core object as pox.core.<_core_name>
  _core_name = LAYER_NAME
  # Layer id constant
  LAYER_ID = "ESCAPE-" + LAYER_NAME
  # Events raised by this class
  _eventMixin_events = {InstantiateNFFGEvent, GetVirtResInfoEvent, PreMapEvent,
                        PostMapEvent}
  # Dependencies
  dependencies = ('orchestration',)

  def __init__ (self, standalone=False, **kwargs):
    """
    .. seealso::
      :func:`AbstractAPI.__init__() <escape.util.api.AbstractAPI.__init__>`
    """
    log.info("Starting Service Layer...")
    # Mandatory super() call
    self.last_sg = NFFG(id=0, name='empty')
    # Set element manager
    self.__sid = None
    self.elementManager = None
    self.service_orchestrator = None
    self.gui_proc = None
    super(ServiceLayerAPI, self).__init__(standalone, **kwargs)

  def initialize (self):
    """
    .. seealso::
      :func:`AbstractAPI.initialize() <escape.util.api.AbstractAPI.initialize>`
    """
    log.debug("Initializing Service Layer...")
    self.__sid = CONFIG.get_service_layer_id()
    if self.__sid is not None:
      log.debug("Setup ID for Service Layer: %s" % self.__sid)
    else:
      self.__sid = self.LAYER_ID
      log.error(
        "Missing ID of Service Layer from config. Using default value: %s" %
        self.__sid)
    # Set element manager
    self.elementManager = ClickManager()
    # Init central object of Service layer
    self.service_orchestrator = ServiceOrchestrator(self)
    # Read input from file if it's given and initiate SG
    if self._sg_file:
      try:
        service_request = self._read_data_from_file(self._sg_file)
        log.info("Graph representation is loaded successfully!")
        if service_request.startswith('{'):
          log.debug("Detected format: JSON - Parsing from NFFG format...")
          nffg = NFFG.parse(raw_data=service_request)
        elif service_request.startswith('<'):
          log.debug("Detected format: XML - Parsing from Virtualizer format...")
          converter = NFFGConverter(domain="INTERNAL", logger=log)
          nffg = converter.parse_from_Virtualizer(vdata=service_request)
        else:
          log.warning("Detected unexpected format...")
          return
        log.info("Schedule service request delayed by 3 seconds...")
        self.api_sas_sg_request_delayed(service_nffg=nffg)
      except (ValueError, IOError, TypeError) as e:
        log.error(
          "Can't load service request from file because of: " + str(e))
    else:
      # Init REST-API if no input file is given
      self._initiate_rest_api()
    # Init GUI
    if self._gui:
      self._initiate_gui()
    log.info("Service Layer has been initialized!")

  def shutdown (self, event):
    """
    .. seealso::
      :func:`AbstractAPI.shutdown() <escape.util.api.AbstractAPI.shutdown>`

    :param event: event object
    """
    log.info("Service Layer is going down...")
    if hasattr(self, 'rest_api') and self.rest_api:
      log.debug("REST-API: %s is shutting down..." % self.rest_api.api_id)
      # self.rest_api.stop()
    if self.gui_proc:
      log.debug("Shut down GUI process - PID: %s" % self.gui_proc.pid)
      self.gui_proc.terminate()

  def _initiate_rest_api (self):
    """
    Initialize and set up REST API in a different thread.

    :return: None
    """
    # set bounded layer name here to avoid circular dependency problem
    handler = CONFIG.get_sas_api_class()
    handler.bounded_layer = self._core_name
    params = CONFIG.get_sas_agent_params()
    # can override from global config
    if 'prefix' in params:
      handler.prefix = params['prefix']
    if 'unify_interface' in params:
      handler.virtualizer_format_enabled = params['unify_interface']
    address = (params.get('address'), params.get('port'))
    self.rest_api = RESTServer(handler, *address)
    self.rest_api.api_id = handler.LOGGER_NAME = "U-Sl"
    handler.log.debug("Init REST-API for %s on %s:%s!" % (
      self.rest_api.api_id, address[0], address[1]))
    self.rest_api.start()
    handler.log.debug("Enforced configuration for %s: interface: %s" % (
      self.rest_api.api_id,
      "UNIFY" if handler.virtualizer_format_enabled else "Internal-NFFG"))

  def _initiate_gui (self):
    """
    Initiate and set up GUI.
    """
    # TODO - set up and initiate MiniEdit here???
    devnull = open(os.devnull, 'r+')
    gui_path = os.path.abspath(os.getcwd() + "/gui/gui.py")
    self.gui_proc = Popen(gui_path, stdin=devnull, stdout=devnull,
                          stderr=devnull, close_fds=True)
    log.info("GUI has been initiated!")

  def _handle_SGMappingFinishedEvent (self, event):
    """
    Handle SGMappingFinishedEvent and proceed with  :class:`NFFG
    <escape.util.nffg.NFFG>` instantiation.

    :param event: event object
    :type event: :any:`SGMappingFinishedEvent`
    :return: None
    """
    self._proceed_to_instantiate_NFFG(event.nffg)

  ##############################################################################
  # UNIFY U - Sl API functions starts here
  ##############################################################################

  @schedule_as_coop_task
  def api_sas_sg_request (self, service_nffg):
    """
    Initiate service graph in a cooperative micro-task.

    :param service_nffg: service graph instance
    :type service_nffg: :any:`NFFG`
    :return: None
    """
    self.__proceed_sg_request(service_nffg)

  @schedule_delayed_as_coop_task(delay=3)
  def api_sas_sg_request_delayed (self, service_nffg):
    """
    Initiate service graph in a cooperative micro-task.

    :param service_nffg: service graph instance
    :type service_nffg: :any:`NFFG`
    :return: None
    """
    return self.__proceed_sg_request(service_nffg)

  def __proceed_sg_request (self, service_nffg):
    """
    Initiate a Service Graph (UNIFY U-Sl API).

    :param service_nffg: service graph instance
    :type service_nffg: :any:`NFFG`
    :return: None
    """
    # Store request if it is received on REST-API
    if hasattr(self, 'rest_api') and self.rest_api:
      self.rest_api.request_cache.add_request(id=service_nffg.id)
      self.rest_api.request_cache.set_in_progress(id=service_nffg.id)
    log.getChild('API').info("Invoke request_service on %s with SG: %s " %
                             (self.__class__.__name__, service_nffg))
    # Initiate service request mapping
    mapped_nffg = self.service_orchestrator.initiate_service_graph(
      service_nffg)
    log.getChild('API').debug("Invoked request_service on %s is finished" %
                              self.__class__.__name__)
    # If mapping is not threaded and finished with OK
    if mapped_nffg is not None and not \
       self.service_orchestrator.mapper.threaded:
      self._proceed_to_instantiate_NFFG(mapped_nffg)
      self.last_sg = mapped_nffg
    else:
      log.warning("Something went wrong in service request initiation: "
                  "mapped service data is missing!")

  def api_sas_get_topology (self):
    """
    Return with the topology description.

    :return: topology description requested from the layer's Virtualizer
    :rtype: :any:`NFFG`
    """
    log.getChild('[U-Sl]').info("Requesting Virtualizer for REST-API...")
    # Get or if not available then request the layer's Virtualizer
    sas_virtualizer = self.service_orchestrator.virtResManager.virtual_view
    if sas_virtualizer is not None:
      log.getChild('[U-Sl]').info("Generate topo description...")
      # return with the virtual view as an NFFG
      return sas_virtualizer.get_resource_info()
    else:
      log.getChild('[U-Sl]').error(
        "Virtualizer(id=%s) assigned to REST-API is not found!" %
        self.cfor_api.api_id)

  def get_result (self, id):
    """
    Return the state of a request given by ``id``.

    :param id: request id
    :type id: str or int
    :return: state
    :rtype: str
    """
    return self.rest_api.request_cache.get_result(id=id)

  def _proceed_to_instantiate_NFFG (self, mapped_nffg):
    """
    Send NFFG to Resource Orchestration Sublayer in an implementation-specific
    way.

    General function which is used from microtask and Python thread also.

    This function contains the last steps before the mapped NFFG will be sent
    to the next layer.

    :param mapped_nffg: mapped Service Graph
    :type mapped_nffg: :any:`NFFG`
    :return: None
    """
    # Rebind requirement link fragments for lower layer mapping
    mapped_nffg = NFFGToolBox.rebind_e2e_req_links(nffg=mapped_nffg, log=log)
    # Log verbose mapping result in unified way (threaded/non-threaded)
    log.log(VERBOSE,
            "Mapping result of Service Layer:\n%s" % mapped_nffg.dump())
    # Notify remote visualizer about the mapping result if it's needed
    notify_remote_visualizer(data=mapped_nffg, id=LAYER_NAME)
    # Sending mapped SG / NF-FG to Orchestration layer as an Event
    # Exceptions in event handlers are caught by default in a non-blocking way
    self.raiseEventNoErrors(InstantiateNFFGEvent, mapped_nffg)
    log.getChild('API').info(
      "Generated NF-FG: %s has been sent to Orchestration..." % mapped_nffg)

  ##############################################################################
  # UNIFY Sl - Or API functions starts here
  ##############################################################################

  def _handle_MissingVirtualViewEvent (self, event):
    """
    Request virtual resource info from Orchestration layer (UNIFY Sl - Or API).

    Invoked when a :class:`MissingVirtualViewEvent` raised.

    Service layer is identified with the sid value automatically.

    :param event: event object
    :type event: :any:`MissingVirtualViewEvent`
    :return: None
    """
    log.getChild('API').debug(
      "Send <Virtual View> request(with layer ID: %s) to Orchestration "
      "layer..." % self.__sid)
    self.raiseEventNoErrors(GetVirtResInfoEvent, self.__sid)

  def _handle_VirtResInfoEvent (self, event):
    """
    Save requested virtual resource info as an :class:`AbstractVirtualizer
    <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`.

    :param event: event object
    :type event: :any:`VirtResInfoEvent`
    :return: None
    """
    log.getChild('API').debug("Received <Virtual View>: %s from %s layer" % (
      event.virtualizer, str(event.source._core_name).title()))
    self.service_orchestrator.virtResManager.virtual_view = event.virtualizer

  def _handle_InstantiationFinishedEvent (self, event):
    """
    """
    if hasattr(self, 'rest_api') and self.rest_api:
      self.rest_api.request_cache.set_result(id=event.id, result=event.result)
    if event.result:
      log.getChild('API').info(
        "Service request(id=%s) has been finished successfully!" % event.id)
    else:
      log.getChild('API').error(
        "Service request(id=%s) has been finished with error!" % event.id)
