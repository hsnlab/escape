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
from escape.infr.il_API import InfrastructureLayerAPI
from escape.util.adapter import AbstractDomainAdapter, AbstractDomainManager, \
  DomainChangedEvent, DeployEvent, VNFStarterAPI, OpenStackAPI, \
  AbstractRESTAdapter
from escape.util.netconf import AbstractNETCONFAdapter
from pox.core import core


class POXDomainAdapter(AbstractDomainAdapter):
  """
  Adapter class to handle communication with internal POX OpenFlow controller

  Can be used to define a controller (based on POX) for other external domains
  """
  name = "POX"

  def __init__ (self, of_name=None, of_address="127.0.0.1", of_port=6633):
    """
    Init
    """
    log.debug("Init %s" % self.__class__.__name__)
    super(POXDomainAdapter, self).__init__()
    self.nexus = of_name
    self.controller_address = (of_address, of_port)
    # Launch OpenFlow connection handler if not started before with given name
    # launch() return the registered openflow module which is a coop Task
    from pox.openflow.of_01 import launch

    of = launch(name=of_name, address=of_address, port=of_port)
    # Start listening for OpenFlow connections
    of.start()
    # register OpenFlow event listeners
    core.openflow.addListeners(self)
    self._connections = []
    log.debug("Start polling POX domain...")
    self.start_polling()

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
    log.debug("Handle connection by %s" % self.__class__.__name__)
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
    log.debug("Handle disconnection by %s" % self.__class__.__name__)
    self._connections.remove(event.connection)
    e = DomainChangedEvent(domain=self.name,
                           cause=DomainChangedEvent.type.DEVICE_DOWN,
                           data={"DPID": event.dpid})
    self.raiseEventNoErrors(e)

  def install_routes (self, routes):
    """
    Install routes related to the managed domain. Translates the generic
    format of the routes into OpenFlow flow rules.

    Routes are computed by the ControllerAdapter's main adaptation algorithm

    :param routes: list of routes
    :type routes: :any:`NFFG`
    :return: None
    """
    log.info("Install POX domain part: routes...")
    # TODO - implement
    pass


class MininetDomainAdapter(AbstractDomainAdapter, VNFStarterAPI):
  """
  Adapter class to handle communication with Mininet domain

  Implement VNF managing API using direct access to the
  :class:`mininet.net.Mininet` object
  """
  # Events raised by this class
  _eventMixin_events = {DomainChangedEvent, DeployEvent}
  name = "MININET"

  def __init__ (self, mininet=None):
    """
    Init

    :param mininet: set pre-defined network (optional)
    :type mininet: :any`mininet.net.Mininet`
    """
    log.debug("Init %s" % self.__class__.__name__)
    # super(MininetDomainAdapter, self).__init__()
    # Call base constructors directly to avoid super() and MRO traps
    AbstractDomainAdapter.__init__(self)
    if not mininet:
      from pox import core

      if core.core.hasComponent(InfrastructureLayerAPI._core_name):
        mininet = core.core.components[
          InfrastructureLayerAPI._core_name].topology
        if mininet is None:
          log.error("Unable to get emulated network reference!")
    self.mininet = mininet

  def initiate_VNFs (self, nffg_part):
    log.info("Install Mininet domain part: initiate VNFs...")
    # TODO - implement
    self.raiseEventNoErrors(DeployEvent, nffg_part)

  def stopVNF (self, vnf_id):
    # TODO - implement
    pass

  def getVNFInfo (self, vnf_id=None):
    # TODO - implement
    pass

  def disconnectVNF (self, vnf_id, vnf_port):
    # TODO - implement
    pass

  def startVNF (self, vnf_id):
    # TODO - implement
    pass

  def connectVNF (self, vnf_id, vnf_port, switch_id):
    # TODO - implement
    pass

  def initiateVNF (self, vnf_type=None, vnf_description=None, options=None):
    # TODO - implement
    pass


class VNFStarterAdapter(AbstractNETCONFAdapter, AbstractDomainAdapter,
                        VNFStarterAPI):
  """
  This class is devoted to provide NETCONF specific functions for vnf_starter
  module. Documentation is transferred from vnf_starter.yang

  This class is devoted to start and stop CLICK-based VNFs that will be
  connected to a mininet switch.

  Follows the MixIn design patteran approach to support NETCONF functionality
  """
  # RPC namespace
  RPC_NAMESPACE = u'http://csikor.tmit.bme.hu/netconf/unify/vnf_starter'
  # Adapter name used in CONFIG and ControllerAdapter class
  name = "VNFStarter"

  def __init__ (self, **kwargs):
    # super(VNFStarterAdapter, self).__init__(**kwargs)
    # Call base constructors directly to avoid super() and MRO traps
    AbstractNETCONFAdapter.__init__(self, **kwargs)
    AbstractDomainAdapter.__init__(self)
    log.debug("Init VNFStarterAdapter")

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
    is UP_AND_RUNNING

    :param vnf_id: VNF ID
    :type vnf_id: str
    :return: reply data
    :raises: RPCError, OperationError, TransportError
    """
    params = {"vnf_id": vnf_id}
    log.debug("Call getVNFInfo...")
    return self.call_RPC('getVNFInfo', **params)


class OpenStackRESTAdapter(AbstractRESTAdapter, AbstractDomainAdapter,
                           OpenStackAPI):
  # TODO -implement
  def __init__ (self, url):
    """
    Init

    :param url: OpenStack RESTful API URL
    :type url: str
    """
    log.debug("Init %s" % self.__class__.__name__)
    # super(OpenStackRESTAdapter, self).__init__(base_url=url)
    # Call base constructors directly to avoid super() and MRO traps
    AbstractRESTAdapter.__init__(self, base_url=url)
    AbstractDomainAdapter.__init__(self)

class InternalDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with internally emulated network

  .. note::
    Uses :class:`MininetDomainAdapter` for managing the emulated network and
    :class:`POXDomainAdapter` for controlling the network
  """
  name = "INTERNAL"

  def __init__ (self, controller=None, network=None, remote=None):
    """
    Init
    """
    log.debug("Init %s" % self.__class__.__name__)
    super(InternalDomainManager, self).__init__()
    # Initiate POX as default route handler with default params
    self._controller = controller if controller else POXDomainAdapter()
    # Initiate Mininet asa default network initiator with default params
    self._network = network if network else MininetDomainAdapter()
    # Set remote VNF handler if needed/set or skip initiation steps in lack
    # of reasonable default agent params
    self._remote = remote if remote else None

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the internal domain

    Split given :any:`NFFG` to a set of NFs need to be initiated and a set of
    routes/connections between the NFs

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    log.info("Install Internal domain part...")
    # TODO - implement
    self._network.initiate_VNFs(nffg_part=())
    # TODO ...
    self._controller.install_routes(routes=())


class OpenStackDomainManager(AbstractDomainAdapter):
  """
  Adapter class to handle communication with OpenStack domain

  .. warning::
    Not implemented yet!
  """
  name = "OPENSTACK"

  def __init__ (self, url):
    """
    Init

    :param url: OpenStack RESTful API URL
    :type url: str
    """
    log.debug("Init %s" % self.__class__.__name__)
    super(OpenStackDomainManager, self).__init__()
    # TODO
    self._adapter = OpenStackRESTAdapter(url)

  def install_nffg (self, nffg_part):
    log.info("Install OpenStack domain part...")
    # TODO - implement
    pass


class DockerDomainManager(AbstractDomainAdapter):
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
    log.debug("Init %s" % self.__class__.__name__)
    super(DockerDomainManager, self).__init__()

  def install_nffg (self, nffg_part):
    log.info("Install Docker domain part...")
    # TODO - implement
    pass
