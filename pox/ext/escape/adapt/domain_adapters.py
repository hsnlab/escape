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
Contains Adapter classes which represent the connections between ESCAPEv2 and
other different domains
"""
from escape.adapt import log as log
from escape.util.misc import enum
from escape.util.netconf import AbstractNETCONFAdapter
from pox.core import core
from pox.lib.revent import Event, EventMixin


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
  Event class for signaling NF-FG deployment to layer API
  """

  def __init__ (self, nffg_part):
    super(DeployEvent, self).__init__()
    self.nffg_part = nffg_part


class AbstractDomainAdapter(EventMixin):
  """
  Abstract class for different domain adapters

  Follows the Adapter design pattern (Adaptor base class)
  """
  # Events raised by this class
  _eventMixin_events = {DomainChangedEvent, DeployEvent}
  # Adapter name used in CONFIG and ControllerAdapter class
  name = None

  def __init__ (self):
    """
    Init
    """
    super(AbstractDomainAdapter, self).__init__()

  def install (self, nffg_part):
    """
    Intall domain specific part of a mapped NFFG

    :param nffg_part: domain specific slice of mapped NFFG
    :type nffg_part: NFFG
    :return: None
    """
    raise NotImplementedError("Derived class have to override this function")


class POXDomainAdapter(AbstractDomainAdapter):
  """
  Adapter class to handle communication with internal POX OpenFlow controller
  """
  name = "POX"

  def __init__ (self, name=None, of_port=6633, of_address="0.0.0.0"):
    """
    Init
    """
    super(POXDomainAdapter, self).__init__()
    # Launch OpenFlow connection handler if not started before with given name
    from pox.openflow.of_01 import launch

    launch(name=name, port=of_port, address=of_address)
    # register OpenFlow event listeners
    core.openflow.addListeners(self)
    self._connections = []
    log.debug("Init %s" % self.__class__.__name__)

  def filter_connections (self, event):
    """
    Handle which connection should be handled by this Adapter class.

    This adapter accept every OpenFlow connection by default.

    :param event: POX internal ConnectionUp event (event.dpid, event.connection)
    :type event: :class:`pox.openflow.ConnectionUp`
    :return: True os False obviously
    :rtype: bool
    """
    return True

  def _handle_ConnectionUp (self, event):
    """
    Handle incoming OpenFlow connections
    """
    if self.filter_connections(event):
      self._connections.append(event.connection)
    e = DomainChangedEvent(domain=self.name,
                           cause=DomainChangedEvent.type.DEVICE_UP,
                           data={"DPID": event.dpid})
    self.raiseEventNoErrors(e)

  def _handle_ConnectionDown (self, event):
    """
    Handle disconnected device
    """
    self._connections.remove(event.connection)
    e = DomainChangedEvent(domain=self.name,
                           cause=DomainChangedEvent.type.DEVICE_DOWN,
                           data={"DPID": event.dpid})
    self.raiseEventNoErrors(e)

  def install (self, nffg_part):
    log.info("Install POX domain part...")
    # TODO - implement
    # dummy reply
    self.raiseEventNoErrors(DeployEvent, nffg_part)


class InternalDomainManager(AbstractDomainAdapter):
  """
  Adapter class to handle communication with internally emulated network

  .. warning::
    Not implemented yet!
  """
  name = "INTERNAL"

  def __init__ (self):
    """
    Init
    """
    super(InternalDomainManager, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)

  def install (self, nffg_part):
    log.info("Install Internal domain part...")
    # TODO - implement
    pass


class MininetDomainAdapter(AbstractDomainAdapter):
  """
  Adapter class to handle communication with external Mininet domain

  .. warning::
    Not implemented yet!
  """
  name = "MNININET"

  def __init__ (self):
    """
    Init
    """
    super(MininetDomainAdapter, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)

  def install (self, nffg_part):
    log.info("Install Mininet domain part...")
    # TODO - implement
    pass


class OpenStackDomainAdapter(AbstractDomainAdapter):
  """
  Adapter class to handle communication with OpenStack domain

  .. warning::
    Not implemented yet!
  """
  name = "OPENSTACK"

  def __init__ (self):
    """
    Init
    """
    super(OpenStackDomainAdapter, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)

  def install (self, nffg_part):
    log.info("Install OpenStack domain part...")
    # TODO - implement
    pass


class DockerDomainAdapter(AbstractDomainAdapter):
  """
  Adapter class to handle communication component in a Docker domain

  .. warning::
    Not implemented yet!
  """
  name = "DOCKER"

  def __init__ (self):
    """
    Init
    """
    super(DockerDomainAdapter, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)

  def install (self, nffg_part):
    log.info("Install Docker domain part...")
    # TODO - implement
    pass


class VNFStarterManager(AbstractNETCONFAdapter):
  """
  This class is devoted to provide NETCONF specific functions for vnf_starter
  module. Documentation is transferred from vnf_starter.yang

  .. seealso::
      :file:`vnf_starter.yang`

  This class is devoted to start and stop CLICK-based VNFs that will be
  connected to a mininet switch.
  """
  # RPC namespace
  RPC_NAMESPACE = u'http://csikor.tmit.bme.hu/netconf/unify/vnf_starter'

  def __init__ (self, **kwargs):
    super(VNFStarterManager, self).__init__(**kwargs)
    log.debug("Init VNFStarterManager")

  # RPC calls starts here

  def initiateVNF (self, vnf_type=None, vnf_description=None, options=None):
    """
    This RCP will start a VNF.

    0. initiate new VNF (initiate datastructure, generate unique ID)
    1. set its arguments (control port, control ip, and VNF type/command)
    2. returns the connection data, which from the vnf_id is the most important

    :param vnf_type: pre-defined VNF type (see in vnf_starter/available_vnfs)
    :type vnf_type: str
    :param vnf_description: Click description if there are no pre-defined type
    :type vnf_description: str
    :param options: unlimited list of additional options as name-value pairs
    :type options: collections.OrderedDict
    :return: RPC reply data
    :raises: RPCError, OperationError, TransportError
    """
    params = locals()
    del params['self']
    log.debug("Call initiateVNF...")
    return self.call_RPC("initiateVNF", **params)

  def connectVNF (self, vnf_id, vnf_port, switch_id):
    """
    This RPC will practically start and connect the initiated VNF/CLICK to
    the switch.

    0. create virtualEthernet pair(s)
    1. connect either end of it (them) to the given switch(es)

    This RPC is also used for reconnecting a VNF. In this case, however,
    if the input fields are not correctly set an error occurs

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :param vnf_port: VNF port (mandatory)
    :type vnf_port: str
    :param switch_id: switch ID (mandatory)
    :type switch_id: str
    :return: Returns the connected port(s) with the corresponding switch(es).
    :raises: RPCError, OperationError, TransportError
    """
    params = locals()
    del params['self']
    log.debug("Call connectVNF...")
    return self.call_RPC("connectVNF", **params)

  def disconnectVNF (self, vnf_id, vnf_port):
    """
    This RPC will disconnect the VNF(s)/CLICK(s) from the switch(es).

    0. ip link set uny_0 down
    1. ip link set uny_1 down
    2. (if more ports) repeat 1. and 2. with the corresponding data

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :param vnf_port: VNF port (mandatory)
    :type vnf_port: str
    :return: reply data
    :raises: RPCError, OperationError, TransportError
    """
    params = locals()
    del params['self']
    log.debug("Call disconnectVNF...")
    return self.call_RPC("disconnectVNF", **params)

  def startVNF (self, vnf_id):
    """
    This RPC will actually start the VNF/CLICK instance.

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :return: reply data
    :raises: RPCError, OperationError, TransportError
    """
    params = locals()
    del params['self']
    log.debug("Call startVNF...")
    return self.call_RPC("startVNF", **params)

  def stopVNF (self, vnf_id):
    """
    This RPC will gracefully shut down the VNF/CLICK instance.

    0. if disconnect() was not called before, we call it
    1. delete virtual ethernet pairs
    2. stop (kill) click
    3. remove vnf's data from the data structure

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :return: reply data
    :raises: RPCError, OperationError, TransportError
    """
    params = locals()
    del params['self']
    log.debug("Call stopVNF...")
    return self.call_RPC("stopVNF", **params)

  def getVNFInfo (self, vnf_id=None):
    """
    This RPC will send back all data of all VNFs that have been initiated by
    this NETCONF Agent. If an input of vnf_id is set, only that VNF's data
    will be sent back. Most of the data this RPC replies is used for DEBUG,
    however 'status' is useful for indicating to upper layers whether a VNF
    is UP_AND_RUNNING"

    :param vnf_id: VNF ID
    :type vnf_id: str
    :return: reply data
    :raises: RPCError, OperationError, TransportError
    """
    params = {"vnf_id": vnf_id}
    log.debug("Call getVNFInfo...")
    return self.call_RPC('getVNFInfo', **params)