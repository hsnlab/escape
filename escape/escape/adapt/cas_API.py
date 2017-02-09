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
Sublayer.
"""
from escape.adapt import LAYER_NAME
from escape.adapt import log as log  # Adaptation layer logger
from escape.adapt.adaptation import ControllerAdapter, InstallationFinishedEvent, \
  InfoRequestFinishedEvent
from escape.infr import LAYER_NAME as INFR_LAYER_NAME
from escape.nffg_lib.nffg import NFFG
from escape.util.api import AbstractAPI
from escape.util.misc import schedule_as_coop_task, quit_with_error
from pox.lib.revent.revent import Event


class GlobalResInfoEvent(Event):
  """
  Event for sending back requested Global Resource View.
  """

  def __init__ (self, dov):
    """
    Init.

    :param dov: Domain Virtualizer which handles the Global Infrastructure View.
    :type dov: :any:`DomainVirtualizer`
    :return: None
    """
    super(GlobalResInfoEvent, self).__init__()
    self.dov = dov


class DeployNFFGEvent(Event):
  """
  Event for passing mapped :any:`NFFG` to internally emulated network based on
  Mininet for testing.
  """

  def __init__ (self, nffg_part):
    """
    Init.

    :param nffg_part: NFFG needs to deploy
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    super(DeployNFFGEvent, self).__init__()
    self.nffg_part = nffg_part


class ControllerAdaptationAPI(AbstractAPI):
  """
  Entry point for Controller Adaptation Sublayer (CAS).

  Maintain the contact with other UNIFY layers.

  Implement the Or - Ca reference point.
  """
  # Define specific name for core object i.e. pox.core.<_core_name>
  _core_name = LAYER_NAME
  # Events raised by this class
  _eventMixin_events = {GlobalResInfoEvent, InstallationFinishedEvent,
                        DeployNFFGEvent, InfoRequestFinishedEvent}

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
    self.controller_adapter = None
    super(ControllerAdaptationAPI, self).__init__(standalone, **kwargs)

  def initialize (self):
    """
    .. seealso::
      :func:`AbstractAPI.initialize() <escape.util.api.AbstractAPI.initialize>`
    """
    log.debug("Initializing Controller Adaptation Sublayer...")
    self.controller_adapter = ControllerAdapter(self, with_infr=self._with_infr)
    if self._mapped_nffg:
      try:
        mapped_request = self._read_data_from_file(self._mapped_nffg)
        mapped_request = NFFG.parse(mapped_request)
        self.__proceed_installation(mapped_nffg=mapped_request)
      except (ValueError, IOError, TypeError) as e:
        log.error("Can't load service request from file because of: " + str(e))
        quit_with_error(msg=str(e), logger=log)
      else:
        log.debug("Graph representation is loaded successfully!")
    log.info("Controller Adaptation Sublayer has been initialized!")

  def shutdown (self, event):
    """
    .. seealso::
      :func:`AbstractAPI.shutdown() <escape.util.api.AbstractAPI.shutdown>`

    :param event: event object
    :type: :class:`pox.lib.revent.revent.Event`
    :return: None
    """
    log.info("Controller Adaptation Sublayer is going down...")
    self.controller_adapter.shutdown()

  ##############################################################################
  # UNIFY Or - Ca API functions starts here
  ##############################################################################

  def _handle_InstallNFFGEvent (self, event):
    """
    Install mapped NF-FG (UNIFY Or - Ca API).

    :param event: event object contains mapped NF-FG
    :type event: :any:`InstallNFFGEvent`
    :return: None
    """
    log.getChild('API').info("Received mapped NF-FG: %s from %s Layer" % (
      event.mapped_nffg, str(event.source._core_name).title()))
    self.__proceed_installation(mapped_nffg=event.mapped_nffg)

  @schedule_as_coop_task
  def __proceed_installation (self, mapped_nffg):
    """
    Helper function to instantiate the NFFG mapping from different source.

    :param mapped_nffg: pre-mapped service request
    :type mapped_nffg: :any:`NFFG`
    :return: None
    """
    log.getChild('API').info("Invoke install_nffg on %s with NF-FG: %s " % (
      self.__class__.__name__, mapped_nffg))
    try:
      deploy_status = self.controller_adapter.install_nffg(mapped_nffg)
    except Exception:
      log.error("Something went wrong during NFFG installation!")
      self.raiseEventNoErrors(InstallationFinishedEvent,
                              result=InstallationFinishedEvent.DEPLOY_ERROR)
      raise
    log.getChild('API').debug("Invoked install_nffg on %s is finished!" %
                              self.__class__.__name__)
    if not deploy_status.still_pending and deploy_status.reset:
      id = mapped_nffg.id
      result = InstallationFinishedEvent.get_result_from_status(deploy_status)
      self.raiseEventNoErrors(InstallationFinishedEvent, id=id, result=result)

  @schedule_as_coop_task
  def _handle_CollectMonitoringDataEvent (self, event):
    """

    :param event:
    :return:
    """
    log.getChild('API').info("Received recursive monitoring request from %s "
                             "Layer" % event.source._core_name.title())
    try:
      status = self.controller_adapter.propagate_info_requests(id=event.id,
                                                               info=event.info)
    except Exception:
      log.exception("Something went wrong during info request processing!")
      self.raiseEventNoErrors(InfoRequestFinishedEvent,
                              result=InfoRequestFinishedEvent.ERROR)
      return
    log.getChild('API').debug("Invoked 'info' on %s is finished!" %
                              self.__class__.__name__)
    if not status.still_pending:
      self.raiseEventNoErrors(InfoRequestFinishedEvent, status=status)

  ##############################################################################
  # UNIFY ( Ca - ) Co - Rm API functions starts here
  ##############################################################################

  def _handle_GetGlobalResInfoEvent (self, event):
    """
    Generate global resource info and send back to ROS.

    :param event: event object
    :type event: :any:`GetGlobalResInfoEvent`
    :return: None
    """
    log.getChild('API').debug(
      "Received DoV request from %s layer" % str(
        event.source._core_name).title())
    # Currently global view is a reference to the DoV to keep ESCAPE fast
    dov = self.controller_adapter.DoVManager.dov
    log.getChild('API').debug(
      "Sending back DoV: %s..." % dov)
    self.raiseEventNoErrors(GlobalResInfoEvent, dov)
