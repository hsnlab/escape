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
from escape.util.misc import enum
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
  """

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
  Abstract class for different domain adapters

  Domain adapters can handle domains as a whole or well-separated parts of a
  domain e.g. control part of an SDN network, infrastructure containers or
  other entities through a specific protocol (NETCONF, ReST)

  Follows the Adapter design pattern (Adaptor base class)

  Follows the MixIn design patteran approach to support general adapter
  functionality for manager classes mostly
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
    """
    Request info  from VNF(s).

    :param vnf_id: VNF ID
    :type vnf_id: str
    :return: reply data
    """


class VNFStarterAPI(object):
  """
  Define interface for managing VNFs.

  .. seealso::
      :file:`vnf_starter.yang`

  Follows the MixIn design pattern approach to support VNFStarter functionality
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
  pass


class AbstractRESTAdapter(object):
  pass
