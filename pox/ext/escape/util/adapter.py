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
Implement the supporting classes for doamin adapters
"""
import json

from requests import Session

from escape import __version__
from escape.util.misc import enum
from escape.util.nffg import NFFG
from pox.lib.recoco import Timer
from pox.lib.revent import EventMixin, Event


class DomainChangedEvent(Event):
  """
  Event class for signaling all kind of change(s) in specific domain

  This event's purpose is to hide the domain specific operations and give a
  general and unified way to signal domain changes to ControllerAdapter in
  order to handle all the changes in the same function/algorithm
  """

  type = enum('DEVICE_UP', 'DEVICE_DOWN', 'LINK_UP', 'LINK_DOWN')

  def __init__ (self, domain, cause, data=None):
    """
    Init event object

    :param domain: domain name. Should be :any:`AbstractDomainAdapter.name`
    :type domain: str
    :param cause: type of the domain change: :any:`DomainChangedEvent.type`
    :type cause: str
    :param data: data connected to the change (optional)
    :type data: object
    :return: None
    """
    super(DomainChangedEvent, self).__init__()
    self.domain = domain
    self.cause = cause
    self.data = data


class DeployEvent(Event):
  """
  Event class for signaling NF-FG deployment to infrastructure layer API

  Used by DirectMininetAdapter for internal NF-FG deployment
  """

  def __init__ (self, nffg_part):
    super(DeployEvent, self).__init__()
    self.nffg_part = nffg_part


class AbstractDomainManager(EventMixin):
  """
  Abstract class for different domain managers

  Domain managers is top level classes to handle and manage domains
  transparently

  Follows the MixIn design pattern approach to support general manager
  functionality for topmost ControllerAdapter class

  Follows the Component Configurator design pattern as base component class
  """

  # Abstract functions for component control
  def init (self):
    """
    Abstract function for component initialization
    """
    pass

  def run (self):
    """
    Abstract function for starting component
    """
    pass

  def finit (self):
    """
    Abstract function for starting component
    """
    pass

  def suspend (self):
    """
    Abstract class for suspending a running component
    """
    pass

  def resume (self):
    """
    Abstract function for resuming a suspended component
    """
    pass

  def info (self):
    """
    Abstract function for requesting information about the component
    """
    return self.__class__.__name__

  # ESCAPE specific functions
  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the specific domain

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    raise NotImplementedError("Not implemented yet!")


class AbstractDomainAdapter(EventMixin):
  """
  Abstract class for different domain adapters.

  Domain adapters can handle domains as a whole or well-separated parts of a
  domain e.g. control part of an SDN network, infrastructure containers or
  other entities through a specific protocol (NETCONF, HTTP/REST).

  Follows the Adapter design pattern (Adaptor base class).

  Follows the MixIn design patteran approach to support general adapter
  functionality for manager classes mostly.
  """
  # Events raised by this class
  _eventMixin_events = {DomainChangedEvent}
  # Adapter name used in CONFIG and ControllerAdapter class
  name = None

  def __init__ (self):
    """
    Init
    """
    super(AbstractDomainAdapter, self).__init__()
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
    Template fuction to poll domain state. Called by a Timer co-op multitask.
    If the function return with False the timer will be cancelled.
    """
    pass


class VNFStarterAPI(object):
  """
  Define interface for managing VNFs.

  .. seealso::
      :file:`vnf_starter.yang`

  Follows the MixIn design pattern approach to support VNFStarter functionality.
  """

  def __init__ (self):
    super(VNFStarterAPI, self).__init__()

  def initiateVNF (self, vnf_type=None, vnf_description=None, options=None):
    """
    Initiate a VNF.

    :param vnf_type: pre-defined VNF type (see in vnf_starter/available_vnfs)
    :type vnf_type: str
    :param vnf_description: Click description if there are no pre-defined type
    :type vnf_description: str
    :param options: unlimited list of additional options as name-value pairs
    :type options: collections.OrderedDict
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
    """
    raise NotImplementedError("Not implemented yet!")

  def startVNF (self, vnf_id):
    """
    Start VNF.

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :return: reply data
    """
    raise NotImplementedError("Not implemented yet!")

  def stopVNF (self, vnf_id):
    """
    Stop VNF.

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :return: reply data
    """
    raise NotImplementedError("Not implemented yet!")

  def getVNFInfo (self, vnf_id=None):
    raise NotImplementedError("Not implemented yet!")


class OpenStackAPI(object):
  """
  Define interface for managing OpenStack domain.

  .. note::
    Based on separated REST API which need to be discussed!

  Follows the MixIn design pattern approach to support OpenStack functionality.
  """
  pass


class AbstractRESTAdapter(Session):
  """
  Abstract class for various adapters rely on a RESTful API.

  Contains basic functions for managing connections.

  Inhereted from :any:`requests.Session`. Provided features: coockie
  persistence, connection-pooling and configuration.

  Implements Context Manager Python protocol::
    >>> with AbstractRESTAdapter as a:
    >>>   a.<method>()

  .. seealso::
    http://docs.python-requests.org/en/latest/api/#requests.Session

  Follows Adapter design pattern.
  """
  # Set custom header
  custom_headers = {'user-agent': "ESCAPE/" + __version__}

  def __init__ (self, base_url, auth=None):
    super(AbstractRESTAdapter, self).__init__()
    self.headers.update(self.custom_headers)
    self.base_url = base_url
    self.auth = auth
    self._raw_response = None

  def _send_request (self, method, url=None, body=None, **kwargs):
    """
    Prepare the request and send it. If valid URL is given that value will be
    used else it will be append to the end of the ``base_url``. If ``url`` is
    not given only the ``base_url`` will be used.

    :param method: HTTP method
    :type method: str
    :param url: valid URL or relevent part follows ``self.base_url``
    :type url: str
    :param body: request body
    :type body: :any:`NFFG` or dict or bytes or str
    :param kwargs: additional params. See :any:`requests.Session.request`
    :return: response text as JSON
    :rtype: str
    :raise HTTPError: if responde code is between 400 and 600
    :raise ConnectionError: connection error
    :raise Timeout: many error occured when request timed out
    """
    # Setup parameters
    if body:
      # if given body is an NFFG
      if isinstance(body, NFFG):
        kwargs['json'] = body.to_json()
      elif isinstance(body, (dict, bytes)):
        kwargs['data'] = body
      else:
        # try to convert to JSON as a last resort
        kwargs['json'] = json.dumps(body)
    if url:
      if not url.startswith('http'):
        kwargs['url'] = self.base_url + url
      else:
        kwargs['url'] = url
    else:
      kwargs['url'] = self.base_url
    self._raw_response = self.request(method=method, **kwargs)
    self._raw_response.raise_for_status()
    return self._raw_response.json()
