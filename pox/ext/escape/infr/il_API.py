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
Emulate UNIFY's Infrastructure Layer for testing purposes based on Mininet
"""
from escape import CONFIG
from escape.infr import LAYER_NAME
from escape.infr.topology import ESCAPENetworkBridge
from escape.infr import log as log  # Infrastructure layer logger
from escape.adapt import LAYER_NAME as ADAPT_LAYER_NAME
from escape.util.api import AbstractAPI
from escape.util.misc import schedule_as_coop_task, quit_with_error
from pox.lib.revent import Event
from pox.openflow.of_01 import OpenFlow_01_Task


class DeploymentFinishedEvent(Event):
  """
  Event for signaling NF-FG deployment
  """

  def __init__ (self, success, error=None):
    super(DeploymentFinishedEvent, self).__init__()
    self.success = success
    self.error = error


class InfrastructureLayerAPI(AbstractAPI):
  """
  Entry point for Infrastructure Layer (IL)

  Maintain the contact with other UNIFY layers

  Implement a specific part of the Co - Rm reference point
  """
  # Define specific name for core object i.e. pox.core.<_core_name>
  _core_name = LAYER_NAME
  # Events raised by this class
  _eventMixin_events = {DeploymentFinishedEvent}
  # Dependencies
  # None

  def __init__ (self, standalone=False, **kwargs):
    """
    .. seealso::
      :func:`AbstractAPI.__init__() <escape.util.api.AbstractAPI.__init__>`
    """
    log.info("Starting Infrastructure Layer...")
    super(InfrastructureLayerAPI, self).__init__(standalone, **kwargs)

  def initialize (self):
    """
    .. seealso::
      :func:`AbstractAPI.initialize() <escape.util.api.AbstractAPI.initialize>`
    """
    log.debug("Initializing Infrastructure Layer...")
    CONFIG.set_loaded(self._core_name)
    self._need_clean = False
    # FIXME - change to dynamic initialization
    self.topology = ESCAPENetworkBridge()
    self.topology.test_network()
    self.topology.start_network()
    # self.topology.initialize(wait_for_controller=True)
    log.info("Infrastructure Layer has been initialized!")

  def shutdown (self, event):
    """
    .. seealso::
      :func:`AbstractAPI.shutdown() <escape.util.api.AbstractAPI.shutdown>`
    """
    log.info("Infrastructure Layer is going down...")
    if self.topology:
      self.topology.stop_network()
    if self._need_clean:
      from mininet import clean

      clean.cleanup()

  def _handle_ComponentRegistered (self, event):
    """
    Wait for controller (internal POX module)

    :param event: registered component event
    :type event: :class:`ComponentRegistered`
    :return: None
    """
    if event.name == CONFIG[ADAPT_LAYER_NAME]['INTERNAL'][
      'listener-id'] and isinstance(event.component, OpenFlow_01_Task):
      try:
        log.debug(
          "Internal domain controller is up! Initiate network emulation...")
        self.topology.start_network()
      except SystemExit as e:
        quit_with_error(msg="Mininet emulation requires root privileges!",
                        logger=self._core_name)

  ##############################################################################
  # UNIFY Co - Rm API functions starts here
  ##############################################################################

  @schedule_as_coop_task
  def _handle_DeployNFFGEvent (self, event):
    """
    Install mapped NFFG part into the emulated network

    :param event:event object
    :return: :any:`DeployNFFGEvent`
    """
    log.getChild('API').info("Received mapped NF-FG from %s Layer" % str(
      event.source._core_name).title())
    # TODO - implement deployment
    log.getChild('API').info("NF-FG deployment has been finished successfully!")
    self.raiseEventNoErrors(DeploymentFinishedEvent, True)

  def install_route (self):
    pass
