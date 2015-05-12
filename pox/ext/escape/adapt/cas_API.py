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
Implements the platform and POX dependent logic for the Controller Adaptation
Sublayer

:class:`GlobalResInfoEvent` can send back global resource info requested from
upper layer

:class:`ControllerAdaptationAPI` represents the CAS layer and implement all
related functionality
"""
import repr

from escape.adapt import LAYER_NAME
from escape.adapt import log as log  # Adaptation layer logger
from escape.adapt.adaptation import ControllerAdapter
from escape.util.api import AbstractAPI
from escape.util.misc import schedule_as_coop_task
from pox.lib.revent.revent import Event
from escape.infr import LAYER_NAME as INFR_LAYER_NAME


class GlobalResInfoEvent(Event):
  """
  Event for sending back requested global resource info
  """

  def __init__ (self, resource_info):
    """
    Init

    :param resource_info: resource info
    :type resource_info: ESCAPEVirtualizer
    """
    super(GlobalResInfoEvent, self).__init__()
    self.resource_info = resource_info


class InstallationFinishedEvent(Event):
  """
  Event for signalling end of mapping process finished with success
  """
  pass


class DeployNFFGEvent(Event):
  """
  Event for passing mapped :class:`NFFG <escape.util.nffg.NFFG>` to
  internally emulated network (Mininet) for testing
  """

  def __init__ (self, mapped_nffg):
    """
    Init

    :param mapped_nffg: NF-FG graph need to be installed
    :type mapped_nffg: NFFG
    """
    super(DeployNFFGEvent, self).__init__()
    self.mapped_nffg = mapped_nffg


class ControllerAdaptationAPI(AbstractAPI):
  """
  Entry point for Controller Adaptation Sublayer (CAS)

  Maintain the contact with other UNIFY layers

  Implement the Or - Ca reference point
  """
  # Define specific name for core object i.e. pox.core.<_core_name>
  _core_name = LAYER_NAME
  # Events raised by this class
  _eventMixin_events = {GlobalResInfoEvent, InstallationFinishedEvent,
                        DeployNFFGEvent}
  # Dependencies
  # None

  def __init__ (self, standalone=False, **kwargs):
    """
    .. seealso::
      :func:`AbstractAPI.__init__() <escape.util.api.AbstractAPI.__init__>`
    """
    log.info("Starting Controller Adaptation Sublayer...")
    # Set Infrastructure as a dependency
    if kwargs['with_infr']:
      log.debug("Set Infrastructure Layer as a dependency")
      self.dependencies = self.dependencies + (INFR_LAYER_NAME,)
    # Mandatory super() call
    super(ControllerAdaptationAPI, self).__init__(standalone, **kwargs)

  def initialize (self):
    """
    .. seealso::
      :func:`AbstractAPI.initialze() <escape.util.api.AbstractAPI.initialize>`
    """
    log.debug("Initializing Controller Adaptation Sublayer...")
    self.controller_adapter = ControllerAdapter()
    if self._mapped_nffg_file:
      self._read_json_from_file(self.mapped_nffg_file)
    log.info("Controller Adaptation Sublayer has been initialized!")

  def shutdown (self, event):
    """
    .. seealso::
      :func:`AbstractAPI.shutdown() <escape.util.api.AbstractAPI.shutdown>`
    """
    log.info("Controller Adaptation Sublayer is going down...")

  ##############################################################################
  # UNIFY Or - Ca API functions starts here
  ##############################################################################

  @schedule_as_coop_task
  def _handle_InstallNFFGEvent (self, event):
    """
    Install mapped NF-FG (UNIFY Or - Ca API)

    :param event: event object contains mapped NF-FG
    :type event: InstallNFFGEvent
    :return: None
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
    Generate global resource info and send back to ROS

    :param event: event object
    :type event: GetGlobalResInfoEvent
    :return: None
    """
    log.getChild('API').debug(
      "Received global resource info request from %s layer" % str(
        event.source._core_name).title())
    # Currently global view is a Virtualizer to keep ESCAPE fast
    log.getChild('API').debug("Sending back global resource info...\n")
    self.raiseEventNoErrors(GlobalResInfoEvent,
                            self.controller_adapter.domainResManager.dov)
