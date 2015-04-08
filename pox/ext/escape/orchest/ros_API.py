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
"""
Implements the platform and POX dependent logic for the Resource Orchestration
Sublayer

:class:`InstallNFFGEvent` can send mapped NF-FG to the lower layer

:class:`VirtResInfoEvent` can send back virtual resource info requested from
upper layer

:class:`GetGlobalResInfoEvent` can request global resource info from lower layer

:class:`ResourceOrchestrationAPI` represents the ROS layer and implement all
related functionality
"""
import repr

from escape.orchest.ros_orchestration import ResourceOrchestrator
from escape.orchest.virtualization_mgmt import VirtualizerManager
from escape.orchest import log as log  # Orchestration layer logger
from escape.orchest import LAYER_NAME
from escape.util.api import AbstractAPI
from escape.util.misc import schedule_as_coop_task
from pox.lib.revent.revent import Event


class InstallNFFGEvent(Event):
  """
  Event for passing mapped :class:`NFFG <escape.util.nffg.NFFG>` to  Controller
  Adaptation Sublayer
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
  Event for sending back requested virtual resource info
  """

  def __init__ (self, resource_info):
    """
    Init

    :param resource_info: virtual resource info
    :type resource_info: ESCAPEVirtualizer
    """
    super(VirtResInfoEvent, self).__init__()
    self.resource_info = resource_info


class GetGlobalResInfoEvent(Event):
  """
  Event for requesting :class:`DomainVirtualizer` from CAS
  """

  def __init__ (self):
    """
    Init
    """
    super(GetGlobalResInfoEvent, self).__init__()


class ResourceOrchestrationAPI(AbstractAPI):
  """
  Entry point for Resource Orchestration Sublayer (ROS)

  Maintain the contact with other UNIFY layers

  Implement the Sl - Or reference point
  """
  # Define specific name for core object i.e. pox.core.<_core_name>
  _core_name = LAYER_NAME
  # Events raised by this class
  _eventMixin_events = {InstallNFFGEvent, GetGlobalResInfoEvent,
                        VirtResInfoEvent}
  # Dependencies
  dependencies = ('adaptation',)

  def __init__ (self, standalone=False, **kwargs):
    """
    .. seealso::
      :func:`AbstractAPI.__init__() <escape.util.api.AbstractAPI.__init__>`
    """
    log.info("Starting Resource Orchestration Sublayer...")
    # Mandatory super() call
    super(ResourceOrchestrationAPI, self).__init__(standalone=standalone,
                                                   **kwargs)

  def initialize (self):
    """
    .. seealso::
      :func:`AbstractAPI.initialze() <escape.util.api.AbstractAPI.initialize>`
    """
    log.debug("Initializing Resource Orchestration Sublayer...")
    virtualizerManager = VirtualizerManager(self)
    self.resource_orchestrator = ResourceOrchestrator(virtualizerManager)
    if self._nffg_file:
      self._read_json_from_file(self.nffg_file)
    log.info("Resource Orchestration Sublayer has been initialized!")

  def shutdown (self, event):
    """
    .. seealso::
      :func:`AbstractAPI.shutdown() <escape.util.api.AbstractAPI.shutdown>`
    """
    log.info("Resource OrchestrationSublayer is going down...")

  # UNIFY Sl- Or API functions starts here

  @schedule_as_coop_task
  def _handle_InstantiateNFFGEvent (self, event):
    """
    Instantiate given NF-FG (UNIFY Sl - Or API)

    :param event: event object contains NF-FG
    :type event: InstantiateNFFGEvent
    :return: None
    """
    log.getChild('API').info(
      "Received NF-FG from %s layer" % str(event.source._core_name).title())
    log.getChild('API').info("Invoke instantiate_nffg on %s with NF-FG: %s " % (
      self.__class__.__name__, repr.repr(event.nffg)))
    mapped_nffg = self.resource_orchestrator.instantiate_nffg(event.nffg)
    log.getChild('API').debug(
      "Invoked instantiate_nffg on %s is finished" % self.__class__.__name__)
    if mapped_nffg is not None:
      # Sending NF-FG to Adaptation layer as an Event
      # Exceptions in event handlers are caught by default in a non-blocking way
      self.raiseEventNoErrors(InstallNFFGEvent, mapped_nffg)
      log.getChild('API').info("Mapped NF-FG has been sent to Adaptation...\n")

  def _handle_GetVirtResInfoEvent (self, event):
    """
    Generate virtual resource info and send back to SAS

    :param event: event object contains service layer id
    :type event: GetVirtResInfoEvent
    :return: None
    """
    log.getChild('API').debug(
      "Received virtual resource info request from %s layer" % str(
        event.source._core_name).title())
    # Currently view is a Virtualizer to keep ESCAPE fast
    view = self.resource_orchestrator.virtualizerManager.get_virtual_view(
      event.sid)
    log.getChild('API').debug("Sending back virtual resource info...\n")
    self.raiseEventNoErrors(VirtResInfoEvent, view)

  # UNIFY Or - Ca API functions starts here

  def request_domain_resource_info (self):
    """
    Request global resource info from CAS (UNIFY Or - CA API)

    :return: None
    """
    log.getChild('API').debug(
      "Send global resource info request to Adaptation layer...\n")
    self.raiseEventNoErrors(GetGlobalResInfoEvent)

  def _handle_GlobalResInfoEvent (self, event):
    """
    Save requested global resource info as the :class:`DomainVirtualizer`

    :param event: event object contains resource info
    :type event: GlobalResInfoEvent
    :return: None
    """
    log.getChild('API').debug(
      "Received global resource info from %s layer" % str(
        event.source._core_name).title())
    self.resource_orchestrator.virtualizerManager.dov = event.resource_info
    pass