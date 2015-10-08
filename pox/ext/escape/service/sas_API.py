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

from escape import __project__, __version__, CONFIG
from escape.service import LAYER_NAME
from escape.service import log as log  # Service layer logger
from escape.service.element_mgmt import ClickManager
from escape.service.sas_orchestration import ServiceOrchestrator
from escape.util.api import AbstractAPI, RESTServer, AbstractRequestHandler
from escape.util.misc import schedule_as_coop_task
from escape.util.nffg import NFFG
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
  request_perm = {'GET': ('echo', 'version', 'operations', 'poll_nffg'),
                  'POST': ('echo', 'result', 'sg', 'poll_nffg'), 'PUT': ('echo',),
                  'DELETE': ('echo',)}
  # Statically defined layer component to which this handler is bounded
  # Need to be set by container class
  bounded_layer = 'service'
  # Logger. Must define.
  log = log.getChild("REST-API")

  # REST API call --> UNIFY U-Sl call

  def echo (self):
    """
    Test function for REST-API.

    :return: None
    """
    params = json.loads(self._get_body())
    self.log_full_message("ECHO: %s - %s", self.raw_requestline, params)
    self._send_json_response(params)

  def version (self):
    """
    Return with version

    :return: None
    """
    log.getChild("REST-API").debug("Call REST-API function: version")
    self._send_json_response({"name": __project__, "version": __version__})

  def operations (self):
    """
    Return with allowed operations

    :return: None
    """
    log.getChild("REST-API").debug("Call REST-API function: operations")
    self._send_json_response(self.request_perm)

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

  def sg (self):
    """
    Main API function for Service Graph initiation

    Bounded to POST HTTP verb
    """
    log.getChild("REST-API").debug("Called REST-API function: sg")
    body = self._get_body()
    # log.getChild("REST-API").debug("Request body:\n%s" % body)
    sg = NFFG.parse(body)  # Initialize NFFG from JSON representation
    log.getChild("REST-API").debug("Parsed service request: %s" % sg)
    self._proceed_API_call('request_service', sg)
    self.send_acknowledge()

  def poll_nffg (self):
    """
    Provide internal NFFG to the GUI

    Internal NFFG is based on NetworkX and can be viewed by networkx_viewer
    """
    log.getChild("REST-API").info("Call REST-API function: poll_nffg")
    config = self._proceed_API_call('poll_nffg')
    self.send_response(200)
    self.send_header('Content-Type', 'application/json')
    self.send_header('Content-Length', len(config))
    self.end_headers()
    self.wfile.write(config)


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
  _eventMixin_events = {InstantiateNFFGEvent, GetVirtResInfoEvent}
  # Dependencies
  dependencies = ('orchestration',)

  def __init__ (self, standalone=False, **kwargs):
    """
    .. seealso::
      :func:`AbstractAPI.__init__() <escape.util.api.AbstractAPI.__init__>`
    """
    log.info("Starting Service Layer...")
    # Mandatory super() call
    super(ServiceLayerAPI, self).__init__(standalone, **kwargs)
    self.last_sg = NFFG(id=0, name='empty')
    self.rest_api = None

  def initialize (self):
    """
    .. seealso::
      :func:`AbstractAPI.initialize() <escape.util.api.AbstractAPI.initialize>`
    """
    log.debug("Initializing Service Layer...")
    self.__sid = self.LAYER_ID
    # Set element manager
    self.elementManager = ClickManager()
    # Init central object of Service layer
    self.service_orchestrator = ServiceOrchestrator(self)
    # Read input from file if it's given and initiate SG
    if self._sg_file:
      try:
        graph_json = self._read_json_from_file(self._sg_file)
        sg_graph = NFFG.parse(graph_json)
        self.request_service(sg=sg_graph)
      except (ValueError, IOError, TypeError) as e:
        log.error(
          "Can't load graph representation from file because of: " + str(e))
      else:
        log.info("Graph representation is loaded successfully!")
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
    """
    log.info("Service Layer is going down...")
    if hasattr(self, 'rest_api') and self.rest_api:
      self.rest_api.stop()

  def _initiate_rest_api (self):
    """
    Initialize and set up REST API in a different thread.

    :return: None
    """
    # set bounded layer name here to avoid circular dependency problem
    handler = CONFIG.get_sas_api_class()
    handler.bounded_layer = self._core_name
    handler.prefix = CONFIG.get_sas_api_prefix()
    self.rest_api = RESTServer(handler, *CONFIG.get_sas_api_address())
    self.rest_api.start()

  def _initiate_gui (self):
    """
    Initiate and set up GUI.
    """
    # TODO - set up and initiate MiniEdit here
    log.info("GUI has been initiated!")

  def _handle_SGMappingFinishedEvent (self, event):
    """
    Handle SGMappingFinishedEvent and proceed with  :class:`NFFG
    <escape.util.nffg.NFFG>` instantiation.

    :param event: event object
    :type event: :any:`SGMappingFinishedEvent`
    :return: None
    """
    self._instantiate_NFFG(event.nffg)

  ##############################################################################
  # UNIFY U - Sl API functions starts here
  ##############################################################################

  @schedule_as_coop_task
  def request_service (self, sg):
    """
    Initiate a Service Graph (UNIFY U-Sl API).

    :param sg: service graph instance
    :type sg: :any:`NFFG`
    :return: None
    """
    # Store request if it is received on REST-API
    if self.rest_api:
      self.rest_api.request_cache.add_request(id=sg.id)
      self.rest_api.request_cache.set_in_progress(id=sg.id)
    log.getChild('API').info("Invoke request_service on %s with SG: %s " % (
      self.__class__.__name__, sg))
    nffg = self.service_orchestrator.initiate_service_graph(sg)
    log.getChild('API').debug(
      "Invoked request_service on %s is finished" % self.__class__.__name__)
    # If mapping is not threaded and finished with OK
    if nffg is not None:
      self._instantiate_NFFG(nffg)
    self.last_sg = sg

  def poll_nffg (self):
    """
    Poll nffg
    """
    return self.last_sg.dump()

  def get_result (self, id):
    """
    Return the state of a request given by ``id``.

    :param id: request id
    :type id: str or int
    :return: state
    :rtype: str
    """
    return self.rest_api.request_cache.get_result(id=id)

  def _instantiate_NFFG (self, nffg):
    """
    Send NFFG to Resource Orchestration Sublayer in an implementation-specific
    way.

    General function which is used from microtask and Python thread also.

    :param nffg: mapped Service Graph
    :type nffg: :any:`NFFG`
    :return: None
    """
    # Sending mapped SG / NF-FG to Orchestration layer as an Event
    # Exceptions in event handlers are caught by default in a non-blocking way
    self.raiseEventNoErrors(InstantiateNFFGEvent, nffg)
    log.getChild('API').info(
      "Generated NF-FG: %s has been sent to Orchestration..." % nffg)

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
    if self.rest_api is not None:
      self.rest_api.request_cache.set_result(id=event.id, result=event.result)
    if event.result:
      log.getChild('API').info(
        "Service request(id=%s) has been finished successfully!" % event.id)
    else:
      log.getChild('API').info(
        "Service request(id=%s) has been finished with error: %s" % (
          event.id, event.error))
