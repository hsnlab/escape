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
import repr

from escape.adapt import LAYER_NAME
from escape.adapt import log as log  # Adaptation layer logger
from escape.adapt.controller_adaptation import ControllerAdapter
from escape.util.api import AbstractAPI
from escape.util.misc import schedule_as_coop_task
from pox.lib.revent.revent import Event


class GlobalResInfoEvent(Event):
  """
  Event for sending back requested global resource info
  """

  def __init__ (self, resource_info):
    super(GlobalResInfoEvent, self).__init__()
    self.resource_info = resource_info


class ControllerAdaptationAPI(AbstractAPI):
  """
  Entry point for Controller Adaptation Sublayer

  Maintain the contact with other UNIFY layers
  Implement the Or - Ca reference point
  """
  # Define specific name for core object i.e. pox.core.<_core_name>
  _core_name = LAYER_NAME
  # Events raised by this class
  _eventMixin_events = {GlobalResInfoEvent}
  # Dependencies
  # None

  def __init__ (self, standalone=False, **kwargs):
    log.info("Starting Controller Adaptation Layer...")
    # Mandatory super() call
    super(ControllerAdaptationAPI, self).__init__(standalone=standalone,
                                                  **kwargs)

  def initialize (self):
    """
    Called when every componenet on which depends are initialized and registered
    in pox.core. Contain actual initialization steps.
    """
    log.debug("Initializing Controller Adaptation Layer...")
    self.controller_adapter = ControllerAdapter()
    if self.mapped_nffg_file:
      self._read_json_from_file(self.mapped_nffg_file)
    log.info("Controller Adaptation Layer has been initialized!")

  def shutdown (self, event):
    log.info("Controller Adaptation Layer is going down...")

  # UNIFY Or - Ca API functions starts here

  @schedule_as_coop_task
  def _handle_InstallNFFGEvent (self, event):
    """
    Install mapped Nf-FG
    """
    log.getChild('API').info("Received mapped NF-FG from %s Layer" % str(
      event.source._core_name).title())
    log.getChild('API').info("Invoke install_nffg on %s with NF-FG: %s " % (
      self.__class__.__name__, repr.repr(event.mapped_nffg)))
    self.controller_adapter.install_nffg(event.mapped_nffg)
    log.getChild('API').debug(
      "Invoked install_nffg on %s is finished" % self.__class__.__name__)

  def _handle_GetGlobalResInfoEvent (self, event):
    """
    Generate global resource info and send back to Orchestration layer
    """
    log.getChild('API').debug(
      "Received global resource info request from %s layer" % str(
        event.source._core_name).title())
    # Currently global view is a Virtualizer to keep ESCAPE fast
    log.getChild('API').debug("Sending back global resource info...\n")
    self.raiseEventNoErrors(GlobalResInfoEvent,
                            self.controller_adapter.domainResManager.dov)
