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
from escape.util.api import AbstractAPI
from escape.orchest import LAYER_NAME
from lib.revent.revent import Event
import pox.core as core

log = core.getLogger(LAYER_NAME)


class ResourceEvent(Event):
  """
  Dummy event to force dependency checking working
  Should/Will be removed shortly!
  """

  def __init__ (self):
    super(ResourceEvent, self).__init__()


class ResourceOrchestrationAPI(AbstractAPI):
  """
  Entry point for Resource Orchestration Sublayer

  Maintain the contact with other UNIFY layers
  Implement the Sl - Or reference point
  """
  # Define specific name for core object i.e. pox.core.<_core_name>
  _core_name = LAYER_NAME
  # Events raised by this class
  _eventMixin_events = {ResourceEvent}
  # Dependencies
  _dependencies = ('adaptation',)

  def __init__ (self, standalone=False, **kwargs):
    log.info("Starting Resource Orchestration Layer...")
    # Mandatory super() call
    super(ResourceOrchestrationAPI, self).__init__(standalone=standalone,
      **kwargs)

  def initialize (self):
    """
    Called when every componenet on which depends are initialized and registered
    in pox.core. Contain actual initialization steps.
    """
    if self.nffg_file:
      self._read_json_from_file(self.nffg_file)
    log.info("Resource Orchestration Layer has been initialized!")

  def _shutdown (self, event):
    log.info("Resource Orchestration Layer is going down...")

  def _handle_adaptation_AdaptationEvent (self, event):
    # placeholder for adaptation dependency
    pass