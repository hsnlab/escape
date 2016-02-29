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
Emulate UNIFY's Infrastructure Layer for testing purposes based on Mininet.
"""
from escape import CONFIG
from escape.infr import LAYER_NAME
from escape.infr import log as log  # Infrastructure layer logger
from escape.infr.topology import ESCAPENetworkBuilder
from escape.util.api import AbstractAPI
from escape.util.misc import schedule_as_coop_task
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
  Entry point for Infrastructure Layer (IL).

  Maintain the contact with other UNIFY layers.

  Implement a specific part of the Co - Rm reference point.
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
    self.topology = None
    super(InfrastructureLayerAPI, self).__init__(standalone, **kwargs)

  def initialize (self):
    """
    .. seealso::
      :func:`AbstractAPI.initialize() <escape.util.api.AbstractAPI.initialize>`
    """
    log.debug("Initializing Infrastructure Layer...")
    # Set layer's LOADED value manually here to avoid issues
    CONFIG.set_layer_loaded(self._core_name)
    mn_opts = CONFIG.get_mn_network_opts()
    # Build the emulated topology with the NetworkBuilder
    optional_topo = getattr(self, '_topo', None)
    self.topology = ESCAPENetworkBuilder(**mn_opts).build(topo=optional_topo)
    log.info("Infrastructure Layer has been initialized!")

  def shutdown (self, event):
    """
    .. seealso::
      :func:`AbstractAPI.shutdown() <escape.util.api.AbstractAPI.shutdown>`

    :param event: event object
    """
    log.info("Infrastructure Layer is going down...")
    if self.topology:
      self.topology.stop_network()

  def _handle_ComponentRegistered (self, event):
    """
    Wait for controller (internal POX module)

    :param event: registered component event
    :type event: :class:`ComponentRegistered`
    :return: None
    """
    # Check if our POX controller is up
    # ESCAPEConfig follows Singleton design pattern
    internal_adapters = CONFIG.get_component_params(component="INTERNAL")[
      'adapters']
    # print internal_adapters
    internal_controller = CONFIG.get_component(component="CONTROLLER",
                                               parent=internal_adapters)
    # print internal_controller
    if event.name == internal_controller.name and isinstance(event.component,
                                                             OpenFlow_01_Task):
      if self.topology is not None:
        log.info("Internal domain controller is up! Initiate network emulation "
                 "now...")
        self.topology.start_network()
      else:
        log.error("Mininet topology is missing! Skip network starting...")

  ##############################################################################
  # UNIFY Co - Rm API functions starts here
  ##############################################################################

  @schedule_as_coop_task
  def _handle_DeployNFFGEvent (self, event):
    """
    Install mapped NFFG part into the emulated network.

    :param event:event object
    :return: :any:`DeployNFFGEvent`
    """
    log.getChild('API').info("Received mapped NF-FG: %s from %s Layer" % (
      event.nffg_part, str(event.source._core_name).title()))
    # TODO - implement static deployment
    # TODO - probably will not be supported in the future
    log.getChild('API').info(
      "NF-FG: %s deployment has been finished successfully!" % event.nffg_part)
    self.raiseEventNoErrors(DeploymentFinishedEvent, True)
