# Copyright 2015 Janos Czentye
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
from escape.util.api import AbstractAPI, RESTServer, AbstractRequestHandler
from escape.service import LAYER_NAME
from escape.util.misc import schedule_as_coop_task
from escape.util.nffg import NFFG
from lib.revent.revent import Event
import pox.core as core

log = core.getLogger(LAYER_NAME)


class ServiceEvent(Event):
  """
  Dummy event to force dependency checking working
  Should/Will be removed shortly!
  """

  def __init__ (self):
    super(ServiceEvent, self).__init__()


class ServiceLayerAPI(AbstractAPI):
  """
  Entry point for Service Layer

  Maintain the contact with other UNIFY layers
  Implement the U - Sl reference point
  """
  # Define specific name for core object i.e. pox.core.<_core_name>
  _core_name = LAYER_NAME
  # Events raised by this class
  _eventMixin_events = {ServiceEvent}
  # Dependencies
  _dependencies = ('orchestration',)

  def __init__ (self, standalone=False, **kwargs):
    log.info("Starting Service Layer...")
    # Mandatory super() call
    super(ServiceLayerAPI, self).__init__(standalone=standalone, **kwargs)

  def initialize (self):
    """
    Called when every componenet on which depends are initialized and registered
    in pox.core. Contain actual initialization steps.
    """
    if self.sg_file:
      try:
        graph_json = self._read_json_from_file(self.sg_file)
        # TODO - handle return value NFFG.init_from_json(graph_json)
        NFFG.init_from_json(graph_json)
      except (ValueError, IOError, TypeError) as e:
        log.error(
          "Can't load graph representation from file because of: " + str(e))
      else:
        log.info("Graph representation is loaded sucessfully!")
    if self.gui:
      self._initiate_gui()
    self._initiate_rest_api(address='')
    log.info("Service Layer has been initialized!")

  def shutdown (self, event):
    log.info("Service Layer is going down...")
    if hasattr(self, 'rest_api'):
      self.rest_api.stop()

  def _handle_orchestration_ResourceEvent (self, event):
    # palceholder for orchestration dependency
    pass

  def _initiate_rest_api (self, address='localhost', port=8008):
    self.rest_api = RESTServer(ServiceRequestHandler, address, port)
    self.rest_api.start()

  def _initiate_gui (self):
    # TODO - set up and initiate MiniEdit here
    pass

  # UNIFY U - Sl API functions starts here

  @schedule_as_coop_task
  def request_service (self, sg):
    """
    Initiate service graph
    :param sg service graph represented as NFFG instance
    """
    # Initiate service graph
    # TODO
    log.debug("Call request_service in %s with param: %s " % (
      self.__class__.__name__, sg))
    pass


class ServiceRequestHandler(AbstractRequestHandler):
  """
  Request Handler for Service layer

  IMPORTANT!
  This class is out of the context of the recoco's co-operative thread context!
  While you don't need to worry much about synchronization between recoco
  tasks, you do need to think about synchronization between recoco task and
  normal threads.
  Synchronisation is needed to take care manually: use relevant helper
  function of core object: callLater/raiseLater or use schedule_as_coop_task
  decorator defined in util.misc on the called function
  """
  # Bind HTTP verbs to UNIFY's API functions
  request_perm = {'GET': ('echo',), 'POST': ('echo', 'sg'), 'PUT': ('echo',),
                  'DELETE': ('echo',)}
  # Statically defined layer component to which this handler is bounded
  bounded_layer = ServiceLayerAPI._core_name
  # Logger. Must define
  log = core.getLogger(str(bounded_layer) + "-REST-API")

  # REST API call --> UNIFY U-Sl call

  def echo (self):
    """
    Test function for REST-API
    """
    self.log_full_message("ECHO: %s - %s", self.raw_requestline,
                          self._parse_json_body())
    self._send_json_response({'echo': True})

  def sg (self):
    """
    Initiate sg graph
    Bounded to POST verb
    """
    self.log.debug("Call REST API function: sg")
    body = self._parse_json_body()
    self.log.debug("sg - Parsed input: %s" % body)
    sg = NFFG.init_from_json(body)
    self.proceed_API_call('request_service', sg)