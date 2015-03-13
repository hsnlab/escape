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
from escape.util.api import AbstractAPI, RESTServer, ESCAPERequestHandler
from escape.service import LAYER_NAME
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
        # TODO - handle return value self._convert_json_to_sg(graph)
        self._convert_json_to_sg(graph_json)
      except (ValueError, IOError, TypeError) as e:
        log.error(
          "Can't load graph representation from file because of: " + str(e))
      else:
        log.info("Graph representation is loaded sucessfully!")
    if self.gui:
      self._initiate_gui()
    self._initiate_rest_api(address='')
    log.info("Service Layer has been initialized!")

  def _shutdown (self, event):
    log.info("Service Layer is going down...")
    if hasattr(self, 'api'):
      self.api.stop()

  def _handle_orchestration_ResourceEvent (self, event):
    # palceholder for orchestration dependency
    pass

  def _initiate_rest_api (self, address='localhost', port=8008):
    self.api = RESTServer(ESCAPERequestHandler, address, port)
    self.api.start()

  def _convert_json_to_sg (self, service_graph):
    # TODO - need standard SG form to implement this
    pass

  def _initiate_gui (self):
    # TODO - set up and initiate MiniEdit here
    pass
