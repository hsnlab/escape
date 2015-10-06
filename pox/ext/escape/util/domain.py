# Copyright 2015 Janos Czentye <czentye@tmit.bme.hu>
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
Implement the supporting classes for domain adapters.
"""
import urlparse
from requests import Session

from escape import __version__
from escape.adapt import log
from escape.util.misc import enum
from escape.util.nffg import NFFG
from pox.lib.recoco import Timer
from pox.lib.revent import EventMixin, Event


class DomainChangedEvent(Event):
  """
  Event class for signaling all kind of change(s) in specific domain.

  This event's purpose is to hide the domain specific operations and give a
  general and unified way to signal domain changes to ControllerAdapter in
  order to handle all the changes in the same function/algorithm.
  """
  # Causes of possible changes
  TYPE = enum('NETWORK_UP', 'NETWORK_DOWN', 'NODE_UP', 'NODE_DOWN',
              'CONNECTION_UP', 'CONNECTION_DOWN')

  def __init__ (self, domain, cause, data=None):
    """
    Init event object

    :param domain: domain name. Should be :any:`AbstractESCAPEAdapter.name`
    :type domain: str
    :param cause: type of the domain change: :any:`DomainChangedEvent.TYPE`
    :type cause: str
    :param data: data connected to the change (optional)
    :type data: :any:`NFFG` or str
    :return: None
    """
    super(DomainChangedEvent, self).__init__()
    self.domain = domain
    self.cause = cause
    self.data = data


class DeployEvent(Event):
  """
  Event class for signaling NF-FG deployment to infrastructure layer API.

  Used by DirectMininetAdapter for internal NF-FG deployment.
  """

  def __init__ (self, nffg_part):
    super(DeployEvent, self).__init__()
    self.nffg_part = nffg_part


class AbstractDomainManager(EventMixin):
  """
  Abstract class for different domain managers.
  DomainManagers is top level classes to handle and manage domains
  transparently.

  Follows the MixIn design pattern approach to support general manager
  functionality for topmost ControllerAdapter class.

  Follows the Component Configurator design pattern as base component class.
  """
  # Events raised by this class
  _eventMixin_events = {DomainChangedEvent}
  # Domain name
  name = "UNDEFINED"
  # Polling interval
  POLL_INTERVAL = 3

  def __init__ (self, **kwargs):
    """
    Init.
    """
    super(AbstractDomainManager, self).__init__()
    # Timer for polling function
    self._timer = None
    self._detected = None  # Actual domain is detected or not
    self.internal_topo = None  # Description of the domain topology as an NFFG
    self.topoAdapter = None  # Special adapter which can handle the topology
    # description, request it, and install mapped NFs from internal NFFG
    if 'poll' in kwargs:
      self._poll = kwargs['poll']
    else:
      self._poll = False

  ##############################################################################
  # Abstract functions for component control
  ##############################################################################

  def init (self, configurator, **kwargs):
    """
    Abstract function for component initialization.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`

    :return: None
    """
    # Skip to start polling is it's set
    if not self._poll:
      # Try to request/parse/update Mininet topology
      if not self._detect_topology():
        log.warning("%s domain not confirmed during init!" % self.name)
    else:
      log.debug("Start polling %s domain..." % self.name)
      self.start_polling(self.POLL_INTERVAL)

  def run (self):
    """
    Abstract function for starting component.

    :return: None
    """
    pass

  def finit (self):
    """
    Abstract function for starting component.
    """
    self.stop_polling()

  def suspend (self):
    """
    Abstract class for suspending a running component.

    .. note::
      Not used currently!

    :return: None
    """
    pass

  def resume (self):
    """
    Abstract function for resuming a suspended component.

    .. note::
      Not used currently!

    :return: None
    """
    pass

  def info (self):
    """
    Abstract function for requesting information about the component.

    .. note::
      Not used currently!

    :return: None
    """
    return self.__class__.__name__

  ##############################################################################
  # Common functions for polling
  ##############################################################################

  def start_polling (self, wait=1):
    """
    Initialize and start a Timer co-op task for polling.

    :param wait: polling period (default: 1)
    :type wait: int
    """
    if self._timer:
      # Already timing
      return
    self._timer = Timer(wait, self.poll, recurring=True, started=True,
                        selfStoppable=True)

  def restart_polling (self, wait=POLL_INTERVAL):
    """
    Reinitialize and start a Timer co-op task for polling.

    :param wait: polling period (default: 3)
    :type wait: int
    """
    self._timer.cancel()
    self._timer = Timer(wait, self.poll, recurring=True, started=True,
                        selfStoppable=True)

  def stop_polling (self):
    """
    Stop timer.
    """
    if self._timer:
      self._timer.cancel()
    self._timer = None

  def poll (self):
    """
    Poll the defined domain agent. Handle different connection errors and go
    to slow/rapid poll. When an agent is (re)detected update the current
    resource information.
    """
    if not self._detected:
      if self._detect_topology():
        # detected
        self.restart_polling()
        return
    else:
      if self.topoAdapter.check_domain_reachable():
        return
    # Not returned before --> got error
    if self._detected is None:
      # detected = None -> First try
      log.warning("%s agent is not detected! Keep trying..." % self.name)
      self._detected = False
    elif self._detected:
      # Detected before -> lost connection = big Problem
      log.warning("Lost connection with %s agent! Go slow poll..." % self.name)
      self._detected = False
      self.restart_polling()
    else:
      # No success but not for the first try -> keep trying silently
      pass

  ##############################################################################
  # ESCAPE specific functions
  ##############################################################################

  def _detect_topology (self):
    """
    Check the undetected topology is up or not.

    :return: detected or not
    :rtype: bool
    """
    if self.topoAdapter.check_domain_reachable():
      log.info(">>> %s domain confirmed!" % self.name)
      self._detected = True
      log.info("Requesting resource information from %s domain..." % self.name)
      topo_nffg = self.topoAdapter.get_topology_resource()
      # print topo_nffg.dump()
      if topo_nffg:
        log.debug("Save received NF-FG: %s..." % topo_nffg)
        # Cache the requested topo
        self.update_local_resource_info(topo_nffg)
        # Notify all components for topology change --> this event causes
        # the DoV updating
        self.raiseEventNoErrors(DomainChangedEvent, domain=self.name,
                                cause=DomainChangedEvent.TYPE.NETWORK_UP,
                                data=topo_nffg)
      else:
        log.warning("Resource info is missing!")
    return self._detected

  def update_local_resource_info (self, data=None):
    """
    Update the resource information of this domain with the requested
    configuration.

    :return: None
    """
    # Cache requested topo info
    if not self.internal_topo:
      self.internal_topo = data
    else:
      # FIXME - maybe just merge especially if we got a diff
      self.internal_topo = data
      # TODO - implement actual updating
      # update DoV

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the specific domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    raise NotImplementedError("Not implemented yet!")

  def clear_domain (self):
    """
    Clear the Domain according to the first received config.
    """
    raise NotImplementedError("Not implemented yet!")


class AbstractESCAPEAdapter(EventMixin):
  """
  Abstract class for different domain adapters.

  Domain adapters can handle domains as a whole or well-separated parts of a
  domain e.g. control part of an SDN network, infrastructure containers or
  other entities through a specific protocol (NETCONF, HTTP/REST).

  Follows the Adapter design pattern (Adaptor base class).

  Follows the MixIn design pattern approach to support general adapter
  functionality for manager classes mostly.
  """
  # Events raised by this class
  _eventMixin_events = {DomainChangedEvent}
  # Adapter name used in CONFIG and ControllerAdapter class
  name = None

  def __init__ (self):
    """
    Init.
    """
    super(AbstractESCAPEAdapter, self).__init__()
    self._timer = None

  def start_polling (self, wait=1):
    """
    Initialize and start a Timer co-op task for polling.

    :param wait: polling period (default: 1)
    :type wait: int
    """
    if self._timer:
      # Already timing
      return
    self._timer = Timer(wait, self.poll, recurring=True, started=True,
                        selfStoppable=True)

  def stop_polling (self):
    """
    Stop timer.
    """
    self._timer.cancel()

  def poll (self):
    """
    Template function to poll domain state. Called by a Timer co-op multitask.
    If the function return with False the timer will be cancelled.
    """
    pass

  def check_domain_reachable (self):
    """
    Checker function for domain polling.

    :return: the domain is detected or not
    :rtype: bool
    """
    raise NotImplementedError("Not implemented yet!")

  def get_topology_resource (self):
    """
    Return with the topology description as an :any:`NFFG`.

    :return: the emulated topology description
    :rtype: :any:`NFFG`
    """
    raise NotImplementedError("Not implemented yet!")


class VNFStarterAPI(object):
  """
  Define interface for managing VNFs.

  .. seealso::
      :file:`vnf_starter.yang`

  Follows the MixIn design pattern approach to support VNFStarter functionality.
  """
  # Pre-defined VNF types
  VNF_HEADER_COMP = "headerCompressor"
  VNF_HEADER_DECOMP = "headerDecompressor"
  VNF_FORWARDER = "simpleForwarder"

  class VNFStatus(object):
    """
    Helper class for define VNF status code constants.

    From YANG: Enum for indicating statuses.
    """
    FAILED = -1
    s_FAILED = "FAILED"
    INITIALIZING = 0
    s_INITIALIZING = "INITIALIZING"
    UP_AND_RUNNING = 1
    s_UP_AND_RUNNING = "UP_AND_RUNNING"

  class ConnectedStatus(object):
    """
    Helper class for define VNF connection code constants.

    From YANG: Connection status.
    """
    DISCONNECTED = 0
    s_DISCONNECTED = "DISCONNECTED"
    CONNECTED = 1
    s_CONNECTED = "CONNECTED"

  def __init__ (self):
    super(VNFStarterAPI, self).__init__()

  def initiateVNF (self, vnf_type, vnf_description=None, options=None):
    """
    Initiate/define a VNF.

    :param vnf_type: pre-defined VNF type (see in vnf_starter/available_vnfs)
    :type vnf_type: str
    :param vnf_description: Click description if there are no pre-defined type
    :type vnf_description: str
    :param options: unlimited list of additional options as name-value pairs
    :type options: collections.OrderedDict
    :return: parsed RPC response
    :rtype: dict
    """
    raise NotImplementedError("Not implemented yet!")

  def connectVNF (self, vnf_id, vnf_port, switch_id):
    """
    Connect a VNF to a switch.

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :param vnf_port: VNF port (mandatory)
    :type vnf_port: str
    :param switch_id: switch ID (mandatory)
    :type switch_id: str
    :return: Returns the connected port(s) with the corresponding switch(es).
    :rtype: dict
    """
    raise NotImplementedError("Not implemented yet!")

  def disconnectVNF (self, vnf_id, vnf_port):
    """
    Disconnect VNF from a switch.

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :param vnf_port: VNF port (mandatory)
    :type vnf_port: str
    :return: reply data
    :rtype: dict
    """
    raise NotImplementedError("Not implemented yet!")

  def startVNF (self, vnf_id):
    """
    Start VNF.

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :return: reply data
    :rtype: dict
    """
    raise NotImplementedError("Not implemented yet!")

  def stopVNF (self, vnf_id):
    """
    Stop VNF.

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :return: reply data
    :rtype: dict
    """
    raise NotImplementedError("Not implemented yet!")

  def getVNFInfo (self, vnf_id=None):
    """
    Request info from available VNF instances.

    :param vnf_id: particular VNF id (default: list info about all VNF)
    :type vnf_id: str
    :return: parsed RPC reply
    :rtype: dict
    """
    raise NotImplementedError("Not implemented yet!")


class DefaultDomainRESTAPI(object):
  """
  Define unified interface for managing UNIFY domains with REST-API.

  Follows the MixIn design pattern approach to support OpenStack functionality.
  """

  def get_config (self):
    """
    Queries the infrastructure view with a netconf-like "get-config" command.

    :return: infrastructure view
    :rtype: :any::`NFFG`
    """
    raise NotImplementedError("Not implemented yet!")

  def edit_config (self, data):
    """
    Send the requested configuration with a netconf-like "edit-config" command.

    :param data: whole domain view
    :type data: :any::`NFFG`
    :return: status code
    :rtype: str
    """
    raise NotImplementedError("Not implemented yet!")

  def ping (self):
    """
    Call the ping RPC.

    :return: response text (should be: 'OK')
    :rtype: str
    """
    raise NotImplementedError("Not implemented yet!")


class OpenStackAPI(DefaultDomainRESTAPI):
  """
  Define interface for managing OpenStack domain.

  .. note::
    Fitted to the API of ETH REST-like server which rely on virtualizer3!

  Follows the MixIn design pattern approach to support OpenStack functionality.
  """


class UniversalNodeAPI(DefaultDomainRESTAPI):
  """
  Define interface for managing Universal Node domain.

  .. note::
    Fitted to the API of ETH REST-like server which rely on virtualizer3!

  Follows the MixIn design pattern approach to support UN functionality.
  """


class RemoteESCAPEv2API(DefaultDomainRESTAPI):
  """
  Define interface for managing remote ESCAPEv2 domain.

  Follows the MixIn design pattern approach to support remote ESCAPEv2
  functionality.
  """


class AbstractRESTAdapter(Session):
  """
  Abstract class for various adapters rely on a RESTful API.
  Contains basic functions for managing HTTP connections.

  Based on :any::`Session` class.

  Follows Adapter design pattern.
  """
  # Set custom header
  custom_headers = {'User-Agent': "ESCAPE/" + __version__}
  # Connection timeout (sec)
  CONNECTION_TIMEOUT = 5
  # HTTP methods
  GET = "GET"
  POST = "POST"

  def __init__ (self, base_url, auth=None):
    super(AbstractRESTAdapter, self).__init__()
    self._base_url = base_url
    self.auth = auth
    # Store the last request
    self._response = None
    self.__suppress_requests_logging()

  @property
  def URL (self):
    return self._base_url

  def __suppress_requests_logging (self, level=None):
    """
    Suppress annoying and detailed logging of `requests` and `urllib3` packages.

    :return: None
    """
    import logging
    level = level if level is not None else logging.WARNING
    logging.getLogger("requests").setLevel(level)
    logging.getLogger("urllib3").setLevel(level)

  def send_request (self, method, url=None, body=None, **kwargs):
    """
    Prepare the request and send it. If valid URL is given that value will be
    used else it will be append to the end of the ``base_url``. If ``url`` is
    not given only the ``base_url`` will be used.

    :param method: HTTP method
    :type method: str
    :param url: valid URL or relevant part follows ``self.base_url``
    :type url: str
    :param body: request body
    :type body: :any:`NFFG` or dict or bytes or str
    :return: raw response data
    :rtype: str
    """
    # Setup parameters - headers
    if 'headers' not in kwargs:
      kwargs['headers'] = dict()
    kwargs['headers'].update(self.custom_headers)
    # Setup connection timeout even if it is not defined explicitly
    if 'timeout' not in kwargs:
      kwargs['timeout'] = self.CONNECTION_TIMEOUT
    # Setup parameters - body
    if body is not None:
      if isinstance(body, NFFG):
        # if given body is an NFFG
        body = body.dump()
        kwargs['headers']['Content-Type'] = "application/json"
    # Setup parameters - URL
    if url is not None:
      if not url.startswith('http'):
        url = urlparse.urljoin(self._base_url, url)
    else:
      url = self._base_url
    # Make request
    self._response = self.request(method=method, url=url, data=body, **kwargs)
    # Raise an exception in case of bad request (4xx <= status code <= 5xx)
    self._response.raise_for_status()
    # Return with body content
    return self._response.text
