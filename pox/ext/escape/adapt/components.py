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
other different domains.
"""
from ncclient.operations.rpc import RPCError
from requests.exceptions import ConnectionError, HTTPError, Timeout

from escape.adapt import log as log
from escape.infr.il_API import InfrastructureLayerAPI
from escape.util.domain import *
from escape.util.netconf import AbstractNETCONFAdapter
from escape.util.pox_extension import ExtendedOFConnectionArbiter, \
  OpenFlowBridge


class InternalPOXAdapter(AbstractESCAPEAdapter):
  """
  Adapter class to handle communication with internal POX OpenFlow controller.

  Can be used to define a controller (based on POX) for other external domains.
  """
  name = "INTERNAL-POX"

  def __init__ (self, name=None, address="127.0.0.1", port=6653):
    """
    Initialize attributes, register specific connection Arbiter if needed and
    set up listening of OpenFlow events.

    :param name: name used to register component ito ``pox.core``
    :type name: str
    :param address: socket address (default: 127.0.0.1)
    :type address: str
    :param port: socket port (default: 6653)
    :type port: int
    """
    name = name if name is not None else self.name
    log.debug("Init InternalPOXAdapter with name: %s address %s:%s" % (
      name, address, port))
    super(InternalPOXAdapter, self).__init__()
    # Set an OpenFlow nexus as a source of OpenFlow events
    self.openflow = OpenFlowBridge()
    self.controller_address = (address, port)
    # Initiate our specific connection Arbiter
    arbiter = ExtendedOFConnectionArbiter.activate()
    # Register our OpenFlow event source
    arbiter.add_connection_listener(self.controller_address, self.openflow)
    # Launch OpenFlow connection handler if not started before with given name
    # launch() return the registered openflow module which is a coop Task
    from pox.openflow.of_01 import launch

    of = launch(name=name, address=address, port=port)
    # Start listening for OpenFlow connections
    of.start()
    self.task_name = name if name else "of_01"
    of.name = self.task_name
    # register OpenFlow event listeners
    self.openflow.addListeners(self)
    log.debug("%s adapter: Start listening connections..." % self.name)

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
    Handle incoming OpenFlow connections.
    """
    log.debug("Handle connection by %s" % self.task_name)
    if self.filter_connections(event):
      event = DomainChangedEvent(domain=self.name,
                                 cause=DomainChangedEvent.TYPE.NODE_UP,
                                 data={"DPID": event.dpid})
      self.raiseEventNoErrors(event)

  def _handle_ConnectionDown (self, event):
    """
    Handle disconnected device.
    """
    log.debug("Handle disconnection by %s" % self.task_name)
    event = DomainChangedEvent(domain=self.name,
                               cause=DomainChangedEvent.TYPE.NODE_DOWN,
                               data={"DPID": event.dpid})
    self.raiseEventNoErrors(event)

  def install_routes (self, routes):
    """
    Install routes related to the managed domain. Translates the generic
    format of the routes into OpenFlow flow rules.

    Routes are computed by the ControllerAdapter's main adaptation algorithm.

    :param routes: list of routes
    :type routes: :any:`NFFG`
    :return: None
    """
    log.info("Install POX domain part: routes...")
    # TODO - implement
    pass


class InternalMininetAdapter(AbstractESCAPEAdapter):
  """
  Adapter class to handle communication with Mininet domain.

  Implement VNF managing API using direct access to the
  :class:`mininet.net.Mininet` object.
  """
  # Events raised by this class
  _eventMixin_events = {DomainChangedEvent}
  name = "MININET"

  def __init__ (self, net=None):
    """
    Init.

    :param net: set pre-defined network (optional)
    :type net: :class:`ESCAPENetworkBridge`
    """
    log.debug("Init InternalMininetAdapter - initial network: %s" % net)
    # Call base constructors directly to avoid super() and MRO traps
    AbstractESCAPEAdapter.__init__(self)
    if not net:
      from pox import core

      if core.core.hasComponent(InfrastructureLayerAPI._core_name):
        # reference to MN --> ESCAPENetworkBridge
        self.IL_topo_ref = core.core.components[
          InfrastructureLayerAPI._core_name].topology
        if self.IL_topo_ref is None:
          log.error("Unable to get emulated network reference!")

  def check_domain_is_up (self):
    """
    Checker function for domain polling.
    """
    # Direct access to IL's Mininet wrapper <-- Internal Domain
    return self.IL_topo_ref.started

  def get_topology_description (self):
    """
    Return with the topology description as an :any:`NFFG`.

    :return: the emulated topology description
    :rtype: :any:`NFFG`
    """
    # Direct access to IL's Mininet wrapper <-- Internal Domain
    return self.IL_topo_ref.topo_desc if self.IL_topo_ref.started else None

  def get_agent_connection_params (self, ee_name):
    """
    Return the connection parameters for the agent of the switch given by the
    ``switch_name``.

    :param ee_name: name of the container Node
    :type ee_name: str
    :return: connection params
    :rtype: dict
    """
    agent = self.IL_topo_ref.get_agent_to_switch(ee_name)
    return {"server": "127.0.0.1", "port": agent.agentPort,
            "username": agent.username,
            "password": agent.passwd} if agent is not None else {}


class VNFStarterAdapter(AbstractNETCONFAdapter, AbstractESCAPEAdapter,
                        VNFStarterAPI):
  """
  This class is devoted to provide NETCONF specific functions for vnf_starter
  module. Documentation is transferred from `vnf_starter.yang`.

  This class is devoted to start and stop CLICK-based VNFs that will be
  connected to a mininet switch.

  Follows the MixIn design pattern approach to support NETCONF functionality.
  """
  # RPC namespace
  RPC_NAMESPACE = u'http://csikor.tmit.bme.hu/netconf/unify/vnf_starter'
  # Adapter name used in CONFIG and ControllerAdapter class
  name = "VNFStarter"

  def __init__ (self, **kwargs):
    """
    Init.

    :param server: server address
    :type server: str
    :param port: port number
    :type port: int
    :param username: username
    :type username: str
    :param password: password
    :type password: str
    :param timeout: connection timeout (default=30)
    :type timeout: int
    :return:
    """
    # Call base constructors directly to avoid super() and MRO traps
    AbstractNETCONFAdapter.__init__(self, **kwargs)
    AbstractESCAPEAdapter.__init__(self)
    log.debug("Init VNFStarterAdapter - params: %s" % kwargs)

  ##############################################################################
  # RPC calls starts here
  ##############################################################################

  def initiateVNF (self, vnf_type, vnf_description=None, options=None):
    """
    This RCP will start a VNF.

    0. initiate new VNF (initiate datastructure, generate unique ID)
    1. set its arguments (control port, control ip, and VNF type/command)
    2. returns the connection data, which from the vnf_id is the most important

    .. raw:: json

      Reply: {"access_info": {"vnf_id": <mandatory>,
                              "control_ip": <optional>,
                              "control_port": <optional>},
              "other": <optional>}

    :param vnf_type: pre-defined VNF type (see in vnf_starter/available_vnfs)
    :type vnf_type: str
    :param vnf_description: Click description if there are no pre-defined type
    :type vnf_description: str
    :param options: unlimited list of additional options as name-value pairs
    :type options: collections.OrderedDict
    :return: RPC reply data
    :rtype: dict
    :raises: RPCError, OperationError, TransportError
    """
    log.debug("Call initiateVNF - VNF type: %s" % vnf_type)
    return self.call_RPC("initiateVNF", vnf_type=vnf_type,
                         vnf_description=vnf_description, options=options)

  def connectVNF (self, vnf_id, vnf_port, switch_id):
    """
    This RPC will practically start and connect the initiated VNF/CLICK to
    the switch.

    0. create virtualEthernet pair(s)
    1. connect either end of it (them) to the given switch(es)

    .. raw:: json

      Reply: {"port": <mandatory>,  # Currently just got RPC OK
              "other": <optional>}

    This RPC is also used for reconnecting a VNF. In this case, however,
    if the input fields are not correctly set an error occurs

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :param vnf_port: VNF port (mandatory)
    :type vnf_port: str or int
    :param switch_id: switch ID (mandatory)
    :type switch_id: str
    :return: Returns the connected port(s) with the corresponding switch(es).
    :raises: RPCError, OperationError, TransportError
    """
    log.debug("Call connectVNF - VNF: %s port: %s --> node: %s" % (
      vnf_id, vnf_port, switch_id))
    return self.call_RPC("connectVNF", vnf_id=vnf_id, vnf_port=vnf_port,
                         switch_id=switch_id)

  def disconnectVNF (self, vnf_id, vnf_port):
    """
    This RPC will disconnect the VNF(s)/CLICK(s) from the switch(es).

    0. ip link set uny_0 down
    1. ip link set uny_1 down
    2. (if more ports) repeat 1. and 2. with the corresponding data

    .. raw:: json

      Reply: {"other": <optional>}  # Currently just got RPC OK

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :param vnf_port: VNF port (mandatory)
    :type vnf_port: str
    :return: reply data
    :raises: RPCError, OperationError, TransportError
    """
    log.debug("Call disconnectVNF - VNF: %s port: %s" % (vnf_id, vnf_port))
    return self.call_RPC("disconnectVNF", vnf_id=vnf_id, vnf_port=vnf_port)

  def startVNF (self, vnf_id):
    """
    This RPC will actually start the VNF/CLICK instance.

    .. raw:: json

      Reply: {"other": <optional>}  # Currently just got RPC OK

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :return: reply data
    :raises: RPCError, OperationError, TransportError
    """
    log.debug("Call startVNF - VNF: %s" % vnf_id)
    return self.call_RPC("startVNF", vnf_id=vnf_id)

  def stopVNF (self, vnf_id):
    """
    This RPC will gracefully shut down the VNF/CLICK instance.

    .. raw:: json

      Reply: {"other": <optional>}  # Currently just got RPC OK

    0. if disconnect() was not called before, we call it
    1. delete virtual ethernet pairs
    2. stop (kill) click
    3. remove vnf's data from the data structure

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :return: reply data
    :raises: RPCError, OperationError, TransportError
    """
    log.debug("Call stopVNF...")
    return self.call_RPC("stopVNF", vnf_id=vnf_id)

  def getVNFInfo (self, vnf_id=None):
    """
    This RPC will send back all data of all VNFs that have been initiated by
    this NETCONF Agent. If an input of vnf_id is set, only that VNF's data
    will be sent back. Most of the data this RPC replies is used for DEBUG,
    however 'status' is useful for indicating to upper layers whether a VNF
    is UP_AND_RUNNING.

    .. raw:: json

      Reply: {"initiated_vnfs": {"vnf_id": <initiated_vnfs key>,
                                "pid": <VNF PID>,
                                "control_ip": <cntr IP>,
                                "control_port": <cntr port>,
                                "command": <VNF init command>
                                "link": ["vnf_port": <port of VNF end>,
                                         "vnf_dev": <VNF end intf>,
                                         "vnf_dev_mac": <VNF end MAC address>,
                                         "sw_dev": <switch/EE end intf>,
                                         "sw_id": <switch/EE end id>,
                                         "sw_port": <switch/EE end port>,
                                         "connected": <conn status>
                                          ],
                                "other": <optional>}}

    :param vnf_id: VNF ID  (default: list info about all VNF)
    :type vnf_id: str
    :return: reply data
    :raises: RPCError, OperationError, TransportError
    """
    log.debug(
      "Call getVNFInfo - VNF: %s" % vnf_id if vnf_id is not None else "all")
    return self.call_RPC('getVNFInfo', vnf_id=vnf_id)

  ##############################################################################
  # High-level helper functions
  ##############################################################################

  def deployNF (self, nf_type, nf_ports, infra_id, nf_desc=None, nf_opt=None):
    """
    Initiate and start the given NF using the general RPC calls.

    :param nf_type: pre-defined NF type (see in vnf_starter/available_vnfs)
    :type nf_type: str
    :param nf_ports: NF port number or list of ports (mandatory)
    :type nf_ports: str or int or tuple
    :param infra_id: id of the base node (mandatory)
    :type infra_id: str
    :param nf_desc: Click description if there are no pre-defined type
    :type nf_desc: str
    :param nf_opt: unlimited list of additional options as name-value pairs
    :type nf_opt: collections.OrderedDict
    :return: initiated NF description parsed from RPC reply
    :rtype: dict
    """
    with self as adapter:
      try:
        # Initiate VNF
        reply = adapter.initiateVNF(vnf_type=nf_type, vnf_description=nf_desc,
                                    options=nf_opt)
        # Get created VNF's id
        vnf_id = reply['access_info']['vnf_id']
        # Connect VNF to the given Container
        if isinstance(nf_ports, (tuple, list)):
          for port in nf_ports:
            adapter.connectVNF(vnf_id=vnf_id, vnf_port=port, switch_id=infra_id)
        else:
          adapter.connectVNF(vnf_id=vnf_id, vnf_port=nf_ports,
                             switch_id=infra_id)
        # Start Click-based VNF
        adapter.startVNF(vnf_id=vnf_id)
        # Return with whole VNF description
        return adapter.getVNFInfo(vnf_id=vnf_id)
      except RPCError as e:
        log.error("Got Error during initiate VNF through NETCONF:")
        from pprint import pprint
        pprint(e.to_dict())
      except KeyError as e:
        log.warning(
          "Missing required attribute from NETCONF-based RPC reply: %s! Skip "
          "VNF initiation." % e.args[0])


class OpenStackRESTAdapter(AbstractRESTAdapter, AbstractESCAPEAdapter,
                           OpenStackAPI):
  """
  This class is devoted to provide REST specific functions for OpenStack domain.
  """

  def __init__ (self, url):
    """
    Init.

    :param url: OpenStack RESTful API URL
    :type url: str
    """
    log.debug("Init OpenStackRESTAdapter with URL: %s" % url)
    AbstractRESTAdapter.__init__(self, base_url=url)
    log.debug("OpenStack base URL is set to %s" % url)
    AbstractESCAPEAdapter.__init__(self)

  def ping (self):
    """
    .. seealso::
      :func:`OpenStackAPI.ping() <escape.util.domain.OpenStackAPI.ping>`
    """
    try:
      return self.send_request(self.GET, 'ping')
    except ConnectionError:
      log.warning("OpenStack agent (%s) is not reachable!" % self._base_url)
    except Timeout:
      log.warning("OpenStack agent (%s) not responding!" % self._base_url)
    except HTTPError as e:
      log.warning(
        "OpenStack agent responded with an error during 'ping': %s" % e.message)

  def get_config (self):
    """
    .. seealso::
      :func:`OpenStackAPI.get_config()
      <escape.util.domain.OpenStackAPI.get_config>`
    """
    try:
      data = self.send_request(self.POST, 'get-config')
    except ConnectionError:
      log.warning("OpenStack agent (%s) is not reachable!" % self._base_url)
      return None
    except Timeout:
      log.warning("OpenStack agent (%s) not responding!" % self._base_url)
      return None
    except HTTPError as e:
      log.warning(
        "OpenStack agent responded with an error during 'get-config': %s" %
        e.message)
      return None
    return NFFG.parse(data)

  def edit_config (self, config):
    """
    .. seealso::
      :func:`OpenStackAPI.edit_config()
      <escape.util.domain.OpenStackAPI.edit_config>`
    """
    if isinstance(config, NFFG):
      config = NFFG.dump(config)
    elif not isinstance(config, (str, unicode)):
      raise RuntimeError("Not supported config format for 'edit-config'!")
    try:
      self.send_request(self.POST, 'edit-config', config)
    except ConnectionError:
      log.warning("OpenStack agent (%s) is not reachable: %s" % self._base_url)
      return None
    except HTTPError as e:
      log.warning(
        "OpenStack agent responded with an error during 'get-config': %s" %
        e.message)
      return None
    return self._response.status_code


class UnifiedNodeRESTAdapter(AbstractRESTAdapter, AbstractESCAPEAdapter,
                             UnifiedNodeAPI):
  """
  This class is devoted to provide REST specific functions for UN domain.
  """

  def __init__ (self, url):
    """
    Init.

    :param url: Unified Node RESTful API URL
    :type url: str
    """
    log.debug("Init OpenStackRESTAdapter with URL: %s" % url)
    AbstractRESTAdapter.__init__(self, base_url=url)
    log.debug("Unified Node base URL is set to %s" % url)
    AbstractESCAPEAdapter.__init__(self)


class InternalDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with internally emulated network.

  .. note::
    Uses :class:`InternalMininetAdapter` for managing the emulated network and
    :class:`InternalPOXAdapter` for controlling the network.
  """
  # Events raised by this class
  _eventMixin_events = {DomainChangedEvent}
  # Domain name
  name = "INTERNAL"

  def __init__ (self, **kwargs):
    """
    Init
    """
    log.debug("Init InternalDomainManager - params: %s" % kwargs)
    super(InternalDomainManager, self).__init__()
    if 'poll' in kwargs:
      self._poll = kwargs['poll']
    else:
      self._poll = False
    self.adapterPOX = None  # DomainAdapter for POX - InternalPOXAdapter
    self.adapterMN = None  # DomainAdapter for Mininet - InternalMininetAdapter
    self.adapterVNF = None  # NETCONF communication - VNFStarterAdapter
    self._detected = None
    self.internal_topo = None  # Description of the domain topology as an NFFG

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    self.stop_polling()
    del self.adapterPOX
    del self.adapterMN
    del self.adapterVNF

  def init (self, configurator, **kwargs):
    """
    Initialize Internal domain manager.

    :return: None
    """
    # Init adapter to internal controller: POX
    self.adapterPOX = configurator.load_component(InternalPOXAdapter.name)
    # Init adapter to internal topo emulation: Mininet
    self.adapterMN = configurator.load_component(InternalMininetAdapter.name)
    # No need to init default NETCONF adapter
    self.adapterVNF = None
    # Skip to start polling is it's set
    if not self._poll:
      # Try to request/parse/update Mininet topology
      if not self._detect_topology():
        log.warning("%s domain not confirmed during init!" % self.name)
    else:
      log.debug("Start polling %s domain..." % self.name)
      self.start_polling(self.POLL_INTERVAL)

  @property
  def controller_name (self):
    return self.adapterPOX.task_name

  def _detect_topology (self):
    """
    Check the undetected topology is up or not.

    :return: detected or not
    :rtype: bool
    """
    if self.adapterMN.check_domain_is_up():
      log.info("%s domain confirmed!" % self.name)
      self._detected = True
      log.info("Updating resource information from %s domain..." % self.name)
      topo_nffg = self.adapterMN.get_topology_description()
      if topo_nffg:
        log.debug("Set received NF-FG: %s..." % topo_nffg)
        self.internal_topo = topo_nffg
        self.raiseEventNoErrors(DomainChangedEvent, domain=self.name,
                                cause=DomainChangedEvent.TYPE.NETWORK_UP,
                                data=topo_nffg)
      else:
        log.warning(
          "Resource info is missing! Infrastructure layer is inconsistent "
          "state!")
    return self._detected

  def poll (self):
    """
    Poll the defined Internal domain based on Mininet.

    :return:
    """
    if not self._detected:
      self._detect_topology()
    else:
      self.update_resource_info()

  def update_resource_info (self):
    """
    Update the resource information of this domain with the requested
    configuration.

    :return: None
    """
    topo_nffg = self.adapterMN.get_topology_description()
    # TODO - implement actual updating
    # update local topology
    # update DoV

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the internal domain.

    Split given :any:`NFFG` to a set of NFs need to be initiated and a set of
    routes/connections between the NFs.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    log.info("Install %s domain part..." % self.name)
    self._deploy_nfs(nffg_part=nffg_part)
    # TODO ... VNF initiation etc.
    # self.controller.install_routes(routes=())

  def _deploy_nfs (self, nffg_part):
    """
    Install the NFs mapped in the given NFFG.

    If an NF is already defined in the topology and it's state is up and
    running then the actual NF's initiation will be skipped!

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    print nffg_part.dump()
    # Iter through the container INFRAs in the given mapped NFFG part
    # for ee in (infra for infra in nffg_part.infras if infra.infra_type in (
    #      NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE)):
    for infra in nffg_part.infras:
      if infra.infra_type not in (
           NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE):
        log.debug(
          "Infrastructure Node: %s is not Container type! Continue to next "
          "Node..." % infra.short_name)
        continue
      else:
        log.debug("Check NFs mapped on Node: %s" % infra.short_name)
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in self.internal_topo.infras):
        log.error(
          "Infrastructure Node: %s is not found in the %s domain! Skip NF "
          "initiation on this Node..." % (infra.short_name, self.name))
        continue
      # Iter over the NFs connected the actual INFRA
      for nf in nffg_part.running_nfs(infra.id):
        # NF with id is already deployed --> continue
        if nf.id in self.internal_topo.nfs:
          log.debug(
            "NF: %s has already been initiated. Continue to next NF..." %
            nf.short_name)
          continue
        # Extract the initiation params
        params = {'nf_type': nf.functional_type,
                  'nf_ports': [link.src.id for u, v, link in
                               nffg_part.network.out_edges_iter((nf.id,),
                                                                data=True)],
                  'infra_id': infra.id}
        # Check if every param is not None or empty
        if not all(params.values()):
          log.error(
            "Missing arguments for initiation of NF: %s. Extracted params: "
            "%s" % (nf.short_name, params))
        # Create connection Adapter to EE agent
        connection_params = self.adapterMN.get_agent_connection_params(infra.id)
        if connection_params is None:
          log.error(
            "Missing connection params for communication with the agent of "
            "Node: %s" % infra.short_name)
        # Save last used adapter --> and last RPC result
        log.debug("Initiating NF: %s with params: %s" % (nf.short_name, params))
        self.adapterVNF = VNFStarterAdapter(**connection_params)
        vnf = self.adapterVNF.deployNF(**params)
        # Check if NETCONF communication was OK
        if vnf is None:
          log.error(
            "Initiated NF: %s is not verified. Initiation was unsuccessful!"
            % nf.short_name)
        else:
          log.info("NF: %s initiation has been verified on Node: %s" % (
            nf.short_name, infra.short_name))


class OpenStackDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with OpenStack domain.

  .. note::
    Uses :class:`OpenStackRESTAdapter` for communicate with the remote domain.
  """
  # Domain name
  name = "OPENSTACK"

  def __init__ (self, **kwargs):
    """
    Init
    """
    log.debug("Init OpenStackDomainManager - params: %s" % kwargs)
    super(OpenStackDomainManager, self).__init__()
    if 'poll' in kwargs:
      self._poll = kwargs['poll']
    else:
      self._poll = False
    self.rest_adapter = None
    self._detected = None

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    self.stop_polling()
    del self.rest_adapter

  def init (self, configurator, **kwargs):
    """
    Initialize OpenStack domain manager.

    :return: None
    """
    self.rest_adapter = configurator.load_component("OpenStack-REST")
    # Skip to start polling is it's set
    if not self._poll:
      return
    log.debug("Start polling %s domain..." % self.name)
    self.start_polling()

  def poll (self):
    """
    Poll the defined OpenStack domain agent. Handle different connection
    errors and go to slow/rapid poll. When an agent is (re)detected update
    the current resource information.
    """
    try:
      if not self._detected:
        # Trying to request config
        raw_data = self.rest_adapter.send_request(self.rest_adapter.POST,
                                                  'get-config')
        # If no exception -> success
        log.info("%s agent detected!" % self.name)
        self._detected = True
        log.info("Updating resource information from %s domain..." % self.name)
        self.update_resource_info(raw_data)
        self.restart_polling()
      else:
        # Just ping the agent if it's alive. If exception is raised -> problem
        self.rest_adapter.send_request(self.rest_adapter.GET, 'ping')
    except ConnectionError:
      if self._detected is None:
        # detected = None -> First try
        log.warning("%s agent is not detected! Keep trying..." % self.name)
        self._detected = False
      elif self._detected:
        # Detected before -> lost connection = big Problem
        log.warning(
          "Lost connection with %s agent! Go slow poll..." % self.name)
        self._detected = False
        self.restart_polling()
      else:
        # No success but not for the first try -> keep trying silently
        pass
    except Timeout:
      if self._detected is None:
        # detected = None -> First try
        log.warning("%s agent not responding!" % self.name)
        self._detected = False
      elif self._detected:
        # Detected before -> not responding = big Problem
        log.warning(
          "Detected %s agent not responding! Go slow poll..." % self.name)
        self._detected = False
        self.restart_polling()
      else:
        # No success but not for the first try -> keep trying silently
        pass
    except HTTPError:
      raise

  def update_resource_info (self):
    """
    Update the resource information if this domain with the requested
    configuration. The config attribute is the raw date from request. This
    function's responsibility to parse/convert/save the data effectively.

    :return: None
    """
    # TODO - implement actual updating
    pass

  def install_nffg (self, nffg_part):
    log.info("Install OpenStack domain part...")
    # TODO - implement just convert NFFG to appropriate format ans send out
    pass


class UnifiedNodeDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with Unified Node (UN) domain.

  .. note::
    Uses :class:`UnifiedNodeRESTAdapter` for communicate with the remote domain.
  """
  # Events raised by this class
  _eventMixin_events = {DomainChangedEvent}
  # Domain name
  name = "UN"

  def __init__ (self, **kwargs):
    """
    Init
    """
    log.debug("Init UnifiedNodeDomainManager - params: %s" % kwargs)
    super(UnifiedNodeDomainManager, self).__init__()

  def install_nffg (self, nffg_part):
    log.info("Install UnifiedNode domain part...")
    # TODO - implement just convert NFFG to appropriate format ans send out
    pass


class DockerDomainManager(AbstractDomainManager):
  """
  Adapter class to handle communication component in a Docker domain.

  .. warning::
    Not implemented yet!
  """
  # Domain name
  name = "DOCKER"

  def __init__ (self, **kwargs):
    """
    Init
    """
    log.debug("Init DockerDomainManager - params %s" % kwargs)
    super(DockerDomainManager, self).__init__()

  def install_nffg (self, nffg_part):
    log.info("Install Docker domain part...")
    # TODO - implement
    pass
