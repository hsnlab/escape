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
import httplib
import os
from subprocess import Popen

from escape.nffg_lib.nffg import NFFG, NFFGToolBox
from escape.orchest.ros_API import InstantiationFinishedEvent, \
  BasicUnifyRequestHandler
from escape.service import LAYER_NAME, log as log  # Service layer logger
from escape.service.element_mgmt import ClickManager
from escape.service.sas_orchestration import ServiceOrchestrator
from escape.util.api import AbstractAPI, RESTServer, AbstractRequestHandler, \
  RequestStatus, RequestScheduler
from escape.util.config import CONFIG
from escape.util.conversion import NFFGConverter
from escape.util.domain import BaseResultEvent
from escape.util.mapping import PreMapEvent, PostMapEvent, ProcessorError
from escape.util.misc import schedule_delayed_as_coop_task, \
  schedule_as_coop_task, VERBOSE, quit_with_ok, \
  get_global_parameter, quit_with_error
from escape.util.stat import stats
from pox.lib.revent.revent import Event

SCHEDULED_SERVICE_REQUEST_DELAY = CONFIG.get_sas_request_delay()


class InstantiateNFFGEvent(Event):
  """
  Event for passing NFFG (mapped SG) to Orchestration layer.
  """

  def __init__ (self, nffg, resource_nffg):
    """
    Init.

    :param nffg: NF-FG need to be initiated
    :type nffg: :class:`NFFG`
    :return: None
    """
    super(InstantiateNFFGEvent, self).__init__()
    self.nffg = nffg
    self.resource_nffg = resource_nffg
    stats.add_measurement_end_entry(type=stats.TYPE_SERVICE, info=LAYER_NAME)


class GetVirtResInfoEvent(Event):
  """
  Event for requesting virtual resource info from Orchestration layer.
  """

  def __init__ (self, sid):
    """
    Init.

    :param sid: Service layer ID
    :type sid: int
    :return: None
    """
    super(GetVirtResInfoEvent, self).__init__()
    # service layer ID
    self.sid = sid


class ServiceRequestHandler(BasicUnifyRequestHandler):
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
    'GET': ('ping', 'version', 'operations', 'topology', 'status'),
    'POST': ('ping', 'sg', 'topology'),
    # 'DELETE': ('sg',),
    'PUT': ('sg',)
  }
  """Bind HTTP verbs to UNIFY's API functions"""
  # Statically defined layer component to which this handler is bounded
  # Need to be set by container class
  bounded_layer = 'service'
  """Statically defined layer component to which this handler is bounded"""
  static_prefix = "escape"
  # Logger name
  LOGGER_NAME = "U-Sl"
  """Logger name"""
  log = log.getChild("[%s]" % LOGGER_NAME)
  # Use Virtualizer format
  virtualizer_format_enabled = False
  """Use Virtualizer format"""
  # Default communication approach
  DEFAULT_DIFF = True
  """Default communication approach"""
  # Bound function
  API_CALL_RESOURCE = 'api_sas_get_topology'
  API_CALL_REQUEST = 'api_sas_sg_request'

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

  def status (self, params):
    """
    Return status of the given request.

    :param params:
    :return:
    """
    message_id = params.get('message-id')
    if not message_id:
      self.send_error(code=httplib.BAD_REQUEST, message="message-id is missing")
      return
    code, result = self._proceed_API_call('api_sas_status', message_id)
    if not result:
      self.send_acknowledge(code=code, message_id=message_id)
      self.log.debug("Responded status code: %s" % code)
    else:
      self.send_json_response(code=code, data=result)
      self.log.debug("Responded status code: %s, data: %s" % (code, result))

  def topology (self, params):
    """
    Provide internal topology description

    Same functionality as "get-config" in UNIFY interface.

    :return: None
    """
    self.log.debug("Call %s function: topology" % self.LOGGER_NAME)
    # Forward call to main layer class
    resource = self._proceed_API_call(self.API_CALL_RESOURCE)
    self._topology_view_responder(resource_nffg=resource,
                                  message_id=params.get(self.MESSAGE_ID_NAME))
    self.log.debug("%s function: topology ended!" % self.LOGGER_NAME)

  def sg (self, params):
    """
    Main API function for Service Graph initiation.

    Same functionality as "get-config" in UNIFY interface.

    Bounded to POST HTTP verb.

    :return: None
    """
    self.log.debug("Call %s function: sg" % self.LOGGER_NAME)
    nffg = self._service_request_parser()
    if nffg:
      if nffg.service_id is None:
        nffg.service_id = nffg.id
      nffg.id = params[self.MESSAGE_ID_NAME]
      self.log.debug("Set NFFG id: %s" % nffg.id)
      nffg.metadata['params'] = params
      # self._proceed_API_call(self.API_CALL_REQUEST,
      #                        service_nffg=nffg,
      #                        params=params)
      self.server.scheduler.schedule_request(id=nffg.id,
                                             layer=self.bounded_layer,
                                             function=self.API_CALL_REQUEST,
                                             service_nffg=nffg, params=params)
      self.send_acknowledge(message_id=params[self.MESSAGE_ID_NAME])
    self.log.debug("%s function: sg ended!" % self.LOGGER_NAME)


class ServiceLayerAPI(AbstractAPI):
  """
  Entry point for Service Adaptation Sublayer.

  Maintain the contact with other UNIFY layers.

  Implement the U - Sl reference point.
  """
  # Defined specific name for core object as pox.core.<_core_name>
  _core_name = LAYER_NAME
  """Defined specific name for core object """
  # Layer id constant
  LAYER_ID = "ESCAPE-" + LAYER_NAME
  """Layer id constant"""
  # Events raised by this class
  _eventMixin_events = {InstantiateNFFGEvent, GetVirtResInfoEvent, PreMapEvent,
                        PostMapEvent}
  """Events raised by this class"""
  # Dependencies
  dependencies = ('orchestration',)
  """Layer dependencies"""

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
    """:type ServiceOrchestrator"""
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
        stats.init_request_measurement(request_id=self._sg_file)
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
        if nffg.mode is not None:
          log.info('Detected mapping mode in NFFG: %s' % nffg.mode)
        else:
          nffg.mode = NFFG.MODE_ADD
          log.info("No mapping mode has been detected in NFFG! "
                   "Set default mode: %s" % nffg.mode)
        log.info("Schedule service request delayed by %d seconds..."
                 % SCHEDULED_SERVICE_REQUEST_DELAY)
        stats.set_request_id(request_id=nffg.id)
        self.api_sas_sg_request_delayed(service_nffg=nffg)
      except (ValueError, IOError, TypeError) as e:
        log.error(
          "Can't load service request from file because of: " + str(e))
        quit_with_error(msg=str(e), logger=log)
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
    handler.log.info("Init REST-API for %s on %s:%s!" % (
      self.rest_api.api_id, address[0], address[1]))
    self.rest_api.start()
    handler.log.debug("Enforced configuration for %s: interface: %s" % (
      self.rest_api.api_id,
      "UNIFY" if handler.virtualizer_format_enabled else "Internal-NFFG"))

  def _initiate_gui (self):
    """
    Initiate and set up GUI.

    :return: None
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
  def api_sas_sg_request (self, service_nffg, *args, **kwargs):
    """
    Initiate service graph in a cooperative micro-task.

    :param service_nffg: service graph instance
    :type service_nffg: :class:`NFFG`
    :return: None
    """
    self.__proceed_sg_request(service_nffg)

  @schedule_delayed_as_coop_task(delay=SCHEDULED_SERVICE_REQUEST_DELAY)
  def api_sas_sg_request_delayed (self, service_nffg, *args, **kwargs):
    """
    Initiate service graph in a cooperative micro-task.

    :param service_nffg: service graph instance
    :type service_nffg: :class:`NFFG`
    :return: None
    """
    return self.__proceed_sg_request(service_nffg)

  def __proceed_sg_request (self, service_nffg):
    """
    Initiate a Service Graph (UNIFY U-Sl API).

    :param service_nffg: service graph instance
    :type service_nffg: :class:`NFFG`
    :return: None
    """
    log.getChild('API').info("Invoke request_service on %s with SG: %s " %
                             (self.__class__.__name__, service_nffg))
    stats.add_measurement_start_entry(type=stats.TYPE_SERVICE, info=LAYER_NAME)
    # Check if mapping mode is set globally in CONFIG
    mapper_params = CONFIG.get_mapping_config(layer=LAYER_NAME)
    if 'mode' in mapper_params and mapper_params['mode'] is not None:
      mapping_mode = mapper_params['mode']
      log.info("Detected mapping mode from configuration: %s" % mapping_mode)
    elif service_nffg.mode is not None:
      mapping_mode = service_nffg.mode
      log.info("Detected mapping mode from NFFG: %s" % mapping_mode)
    else:
      mapping_mode = None
      log.info("No mapping mode was detected!")
    self.__sg_preprocessing(nffg=service_nffg)
    # Store request if it is received on REST-API
    if hasattr(self, 'rest_api') and self.rest_api:
      log.getChild('API').debug("Store received NFFG request info...")
      msg_id = self.rest_api.request_cache.cache_request_by_nffg(
        nffg=service_nffg)
      if msg_id is not None:
        self.rest_api.request_cache.set_in_progress(id=msg_id)
        log.getChild('API').debug("Request is stored with id: %s" % msg_id)
      else:
        log.getChild('API').debug("No request info detected.")
    try:
      if CONFIG.get_mapping_enabled(layer=LAYER_NAME):
        # Initiate service request mapping
        mapped_nffg = self.service_orchestrator.initiate_service_graph(
          service_nffg)
      else:
        log.warning("Mapping is disabled! Skip instantiation step...")
        mapped_nffg = service_nffg
        mapped_nffg.status = NFFG.MAP_STATUS_SKIPPED
        log.debug("Mark NFFG status: %s!" % mapped_nffg.status)
      # Rewrite REMAP mode for backward compatibility
      if mapped_nffg is not None and mapping_mode == NFFG.MODE_REMAP:
        mapped_nffg.mode = mapping_mode
        log.debug("Rewrite mapping mode: %s into mapped NFFG..." %
                  mapped_nffg.mode)
      else:
        log.debug(
          "Skip mapping mode rewriting! Mode remained: %s" % mapping_mode)
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
        self.__handle_mapping_result(nffg_id=service_nffg.id, fail=True)
        self._handle_InstantiationFinishedEvent(
          event=InstantiationFinishedEvent(
            id=service_nffg.id,
            result=InstantiationFinishedEvent.MAPPING_ERROR))
    except ProcessorError as e:
      self.__handle_mapping_result(nffg_id=service_nffg.id, fail=True)
      self._handle_InstantiationFinishedEvent(
        event=InstantiationFinishedEvent(
          id=service_nffg.id,
          result=InstantiationFinishedEvent.REFUSED_BY_VERIFICATION,
          error=e))

  def __sg_preprocessing (self, nffg):
    if nffg.mode == NFFG.MODE_DEL:
      log.debug("Explicitly mark NF nodes in DELETE request...")
      for nf in nffg.nfs:
        nf.operation = NFFG.OP_DELETE
        log.debug("%s --> %s" % (nf.id, nf.operation))

  def __handle_mapping_result (self, nffg_id, fail):
    if not (hasattr(self, 'rest_api') and self.rest_api):
      return
    log.getChild('API').debug("Cache request status...")
    req_status = self.rest_api.request_cache.get_request_by_nffg_id(nffg_id)
    if req_status is None:
      log.getChild('API').debug("Request status is missing for NFFG: %s! "
                                "Skip result processing..." % nffg_id)
      return
    log.getChild('API').debug("Process mapping result...")
    message_id = req_status.message_id
    if message_id is not None:
      if fail:
        self.rest_api.request_cache.set_error_result(id=message_id)
      else:
        self.rest_api.request_cache.set_success_result(id=message_id)
      ret = self.rest_api.invoke_callback(message_id=message_id)
      if ret is None:
        log.getChild('API').debug("No callback was defined!")
      else:
        log.getChild('API').debug(
          "Callback: %s has invoked with return value: %s" % (
            req_status.get_callback(), ret))
    RequestScheduler().set_orchestration_finished(id=nffg_id)

  def __get_sas_resource_view (self):
    """
    Return with the resource view of SAS layer.

    :return: resource view
    :rtype: :any:`AbstractVirtualizer`
    """
    return self.service_orchestrator.virtResManager.virtual_view

  def api_sas_get_topology (self):
    """
    Return with the topology description.

    :return: topology description requested from the layer's Virtualizer
    :rtype: :class:`NFFG`
    """
    log.getChild('[U-Sl]').debug("Requesting Virtualizer for REST-API...")
    # Get or if not available then request the layer's Virtualizer
    sas_virt = self.__get_sas_resource_view()
    if sas_virt is not None:
      log.getChild('[U-Sl]').debug("Generate topo description...")
      # return with the virtual view as an NFFG
      return sas_virt.get_resource_info()
    else:
      log.getChild('[U-Sl]').error(
        "Virtualizer(id=%s) assigned to REST-API is not found!" %
        self.rest_api.api_id)

  def api_sas_status (self, message_id):
    """
    Return the state of a request given by ``message_id``.

    Function is not invoked in coop-microtask, only write-type operations
    must not be used.

    :param message_id: request id
    :type message_id: str or int
    :return: state
    :rtype: str
    """
    status = self.rest_api.request_cache.get_domain_status(id=message_id)
    if status == RequestStatus.SUCCESS:
      return 200, None
    elif status == RequestStatus.UNKNOWN:
      return 404, None
    elif status == RequestStatus.ERROR:
      return 500, status
    else:
      # PROCESSING or INITIATED
      return 202, None

  def _proceed_to_instantiate_NFFG (self, mapped_nffg):
    """
    Send NFFG to Resource Orchestration Sublayer in an implementation-specific
    way.

    General function which is used from microtask and Python thread also.

    This function contains the last steps before the mapped NFFG will be sent
    to the next layer.

    :param mapped_nffg: mapped Service Graph
    :type mapped_nffg: :class:`NFFG`
    :return: None
    """
    # Rebind requirement link fragments for lower layer mapping
    mapped_nffg = NFFGToolBox.rebind_e2e_req_links(nffg=mapped_nffg, log=log)
    # Log verbose mapping result in unified way (threaded/non-threaded)
    log.log(VERBOSE,
            "Mapping result of Service Layer:\n%s" % mapped_nffg.dump())
    # Sending mapped SG / NF-FG to Orchestration layer as an Event
    # Exceptions in event handlers are caught by default in a non-blocking way
    sas_res = self.__get_sas_resource_view().get_resource_info()
    self.raiseEventNoErrors(InstantiateNFFGEvent, mapped_nffg, sas_res)
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
    Receive the result of the instantiated NFFG and save it.

    :param event: event object
    :type event: :any:`InstantiationFinishedEvent`
    :return: None
    """
    if not BaseResultEvent.is_error(event.result):
      log.getChild('API').info(
        "Service request(id=%s) has been finished successfully with result: %s!"
        % (event.id, event.result))
    else:
      log.getChild('API').error(
        "Service request(id=%s) has been finished with error result: %s!" %
        (event.id, event.result))
    if not event.is_pending(event.result):
      self.__handle_mapping_result(nffg_id=event.id,
                                   fail=event.is_error(event.result))
      # Quit ESCAPE if test mode is active
      if get_global_parameter(name="QUIT_AFTER_PROCESS"):
        stats.finish_request_measurement()
        quit_with_ok("Detected QUIT mode! Exiting ESCAPE...")
