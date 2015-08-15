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

from escape.infr.il_API import InfrastructureLayerAPI
from escape.util.conversion import NFFGConverter
from escape.util.domain import *
from escape.util.netconf import AbstractNETCONFAdapter
from escape.util.pox_extension import ExtendedOFConnectionArbiter, \
  OpenFlowBridge
from escape import CONFIG


class TopologyLoadException(Exception):
  """
  Exception class for topology errors.
  """
  pass

class InternalPOXAdapter(AbstractESCAPEAdapter):
  """
  Adapter class to handle communication with internal POX OpenFlow controller.

  Can be used to define a controller (based on POX) for other external domains.
  """
  name = "INTERNAL-POX"

  # Static mapping of infra IDs and DPIDs
  infra_to_dpid = {
    'MT1': 0x14c5e0c376e24,
    'MT2': 0x14c5e0c376fc6,
    'SW1': 0x1,
    'SW2': 0x2,
    'SW3': 0x3,
    'SW4': 0x4,
    }
  dpid_to_infra = {
    0x14c5e0c376e24 : 'MT1',
    0x14c5e0c376fc6 : 'MT2',
    0x1 : 'SW1',
    0x2 : 'SW2',
    0x3 : 'SW3',
    0x4 : 'SW4'
    }

  def __init__ (self, name=None, address="127.0.0.1", port=6633):
    """
    Initialize attributes, register specific connection Arbiter if needed and
    set up listening of OpenFlow events.

    :param name: name used to register component ito ``pox.core``
    :type name: str
    :param address: socket address (default: 127.0.0.1)
    :type address: str
    :param port: socket port (default: 6633)
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
    # Currently static initialization from a config file
    # TODO: discover SDN topology and create the NFFG
    self.topo = None   # SDN domain topology stored in NFFG
    self.__init_from_CONFIG()

  def __init_from_CONFIG (self, path=None):
    """
    Load a pre-defined topology from an NFFG stored in a file.
    The file path is searched in CONFIG with tha name ``SDN-TOPO``.

    :param path: additional file path
    :type path: str
    :param format: NF-FG storing format (default: internal NFFG representation)
    :type format: str
    :return: None
    """
    if path is None:
      path = CONFIG.get_sdn_topology()
    if path is None:
      log.warning("SDN topology is missing from CONFIG!")
      raise TopologyLoadException("Missing Topology!")
    else:
      try:
        with open(path, 'r') as f:
          log.info("Load SDN topology from file: %s" % path)
          self.topo = NFFG.parse(f.read())
      except IOError:
        log.debug("SDN topology file not found: %s" % path)
        raise TopologyLoadException("Missing topology file!")
      except ValueError as e:
        log.error(
          "An error occurred when load topology from file: %s" % e.message)
        raise TopologyLoadException("File parsing error!")

  def check_domain_reachable (self):
    """
    Checker function for domain polling.

    :return: the domain is detected or not
    :rtype: bool
    """
    from pox.core import core
    return core.hasComponent(self.name)

  def get_topology_resource (self):
    """
    Return with the topology description as an :any:`NFFG`.

    :return: the emulated topology description
    :rtype: :any:`NFFG`
    """
    # raise RuntimeError("InternalPoxController not supported this function: "
    #                    "get_topology_resource() !")
    # return static topology
    return self.topo

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

  def install_flowrule (self, id, match, action):
    """
    Install a flowrule in an OpenFlow switch.

    :param id: ID of the infra element stored in the NFFG
    :type id: str
    :param match: match part of the rule (keys: in_port, vlan_id)
    :type match: dict
    :param action: action part of the rule (keys: out, vlan_push, vlan_pop)
    :type action: dict
    :return: None
    """
    log.info("Install POX domain part: flow entry to INFRA %s..." % id)
    print id
    print infra_to_dpid[id]
    print match
    print action


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

  def check_domain_reachable (self):
    """
    Checker function for domain polling.

    :return: the domain is detected or not
    :rtype: bool
    """
    # Direct access to IL's Mininet wrapper <-- Internal Domain
    return self.IL_topo_ref.started

  def get_topology_resource (self):
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

  RPC_NAMESPACE = u'http://csikor.tmit.bme.hu/netconf/unify/vnf_starter'

  name = "VNFStarter"

  # RPC namespace
  # Adapter name used in CONFIG and ControllerAdapter class
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

  def check_domain_reachable (self):
    """
    Checker function for domain polling.

    :return: the domain is detected or not
    :rtype: bool
    """
    try:
      return self.get(expr="vnf_starter/agent_name") is not None
    except:
      return False

  def get_topology_resource (self):
    """
    Return with the topology description as an :any:`NFFG`.

    :return: the emulated topology description
    :rtype: :any:`NFFG`
    """
    raise RuntimeError("VNFStarterAdapter not supported this function: "
                       "get_topology_resource() !")

  def update_connection_params (self, **kwargs):
    """
    Update connection params.

    :return: only updated params
    :rtype: dict
    """
    for param in ('server', 'port', 'username', 'password'):
      if param in kwargs:
        if kwargs[param] == getattr(self, param):
          del kwargs[param]
        else:
          setattr(self, param, kwargs[param])
    return kwargs

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


class RemoteESCAPEv2RESTAdapter(AbstractRESTAdapter, AbstractESCAPEAdapter,
                                RemoteESCAPEv2API):
  """
  This class is devoted to provide REST specific functions for remote ESCAPEv2
  domain.
  """
  name = "ESCAPE-REST"

  def __init__ (self, url):
    """
    Init.

    :param url: remote ESCAPEv2 RESTful API URL
    :type url: str
    """
    log.debug("Init RemoteESCAPEv2RESTAdapter with URL: %s" % url)
    AbstractRESTAdapter.__init__(self, base_url=url)
    log.debug("RemoteESCAPEv2 base URL is set to %s" % url)
    AbstractESCAPEAdapter.__init__(self)

  def ping (self):
    try:
      return self.send_request(self.GET, 'ping')
    except ConnectionError:
      log.warning(
        "Remote ESCAPEv2 agent (%s) is not reachable!" % self._base_url)
    except Timeout:
      log.warning("Remote ESCAPEv2 agent (%s) not responding!" % self._base_url)
    except HTTPError as e:
      log.warning(
        "Remote ESCAPEv2 agent responded with an error during 'ping': %s" %
        e.message)

  def topology_resource (self):
    try:
      data = self.send_request(self.POST, 'topology-resource')
    except ConnectionError:
      log.warning(
        "Remote ESCAPEv2 agent (%s) is not reachable!" % self._base_url)
      return None
    except Timeout:
      log.warning("Remote ESCAPEv2 agent (%s) not responding!" % self._base_url)
      return None
    except HTTPError as e:
      log.warning("Remote ESCAPEv2 agent responded with an error during "
                  "'topology-resource': %s" % e.message)
      return None
    return NFFG.parse(data)

  def install_nffg (self, config):
    if isinstance(config, NFFG):
      config = NFFG.dump(config)
    elif not isinstance(config, (str, unicode)):
      raise RuntimeError("Not supported config format for 'install-nffg'!")
    try:
      self.send_request(self.POST, 'install-nffg', config)
    except ConnectionError:
      log.warning(
        "Remote ESCAPEv2 agent (%s) is not reachable: %s" % self._base_url)
      return None
    except HTTPError as e:
      log.warning(
        "Remote ESCAPEv2 responded with an error during 'install-nffg': %s" %
        e.message)
      return None
    return self._response.status_code

  def check_domain_reachable (self):
    return self.ping()

  def get_topology_resource (self):
    return self.topology_resource()


class OpenStackRESTAdapter(AbstractRESTAdapter, AbstractESCAPEAdapter,
                           OpenStackAPI):
  """
  This class is devoted to provide REST specific functions for OpenStack
  domain.
  """
  # Adapter name used in CONFIG and ControllerAdapter class
  name = "OpenStack-REST"

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
    return NFFGConverter(NFFG.DOMAIN_OS).parse_from_Virtualizer3(data)

  def edit_config (self, config):
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

  def check_domain_reachable (self):
    return self.ping()

  def get_topology_resource (self):
    return self.get_config()


class UnifiedNodeRESTAdapter(AbstractRESTAdapter, AbstractESCAPEAdapter,
                             UnifiedNodeAPI):
  """
  This class is devoted to provide REST specific functions for UN domain.
  """
  # Adapter name used in CONFIG and ControllerAdapter class
  name = "UN-REST"

  def __init__ (self, url):
    """
    Init.

    :param url: Unified Node RESTful API URL
    :type url: str
    """
    log.debug("Init UnifiedNodeRESTAdapter with URL: %s" % url)
    AbstractRESTAdapter.__init__(self, base_url=url)
    log.debug("Unified Node base URL is set to %s" % url)
    AbstractESCAPEAdapter.__init__(self)

  def ping (self):
    try:
      return self.send_request(self.GET, 'ping')
    except ConnectionError:
      log.warning("Unified Node agent (%s) is not reachable!" % self._base_url)
    except Timeout:
      log.warning("Unified Node agent (%s) not responding!" % self._base_url)
    except HTTPError as e:
      log.warning(
        "Unified Node agent responded with an error during 'ping': %s" %
        e.message)

  def get_config (self):
    try:
      data = self.send_request(self.POST, 'get-config')
    except ConnectionError:
      log.warning("Unified Node agent (%s) is not reachable!" % self._base_url)
      return None
    except Timeout:
      log.warning("Unified Node agent (%s) not responding!" % self._base_url)
      return None
    except HTTPError as e:
      log.warning(
        "Unified Node agent responded with an error during 'get-config': %s"
        % e.message)
      return None
    return NFFG.parse(data)

  def edit_config (self, config):
    if isinstance(config, NFFG):
      config = NFFG.dump(config)
    elif not isinstance(config, (str, unicode)):
      raise RuntimeError("Not supported config format for 'edit-config'!")
    try:
      self.send_request(self.POST, 'edit-config', config)
    except ConnectionError:
      log.warning(
        "Unified Node agent (%s) is not reachable: %s" % self._base_url)
      return None
    except HTTPError as e:
      log.warning(
        "Unified Node agent responded with an error during 'get-config': %s"
        % e.message)
      return None
    return self._response.status_code

  def check_domain_reachable (self):
    return self.ping()

  def get_topology_resource (self):
    return self.get_config()


class InternalDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with internally emulated network.

  .. note::
    Uses :class:`InternalMininetAdapter` for managing the emulated network and
    :class:`InternalPOXAdapter` for controlling the network.
  """
  # Domain name
  name = "INTERNAL"

  def __init__ (self, **kwargs):
    """
    Init
    """
    log.debug("Init InternalDomainManager - params: %s" % kwargs)
    super(InternalDomainManager, self).__init__(**kwargs)
    self.controlAdapter = None  # DomainAdapter for POX - InternalPOXAdapter
    self.remoteAdapter = None  # NETCONF communication - VNFStarterAdapter

  def init (self, configurator, **kwargs):
    """
    Initialize Internal domain manager.

    :return: None
    """
    # Init adapter for internal topo emulation: Mininet
    self.topoAdapter = configurator.load_component(InternalMininetAdapter.name)
    # Init adapter for internal controller: POX
    self.controlAdapter = configurator.load_component(InternalPOXAdapter.name)
    # Init default NETCONF adapter
    self.remoteAdapter = configurator.load_component(VNFStarterAdapter.name)
    super(InternalDomainManager, self).init(configurator, **kwargs)

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """

    super(InternalDomainManager, self).finit()
    del self.controlAdapter
    del self.remoteAdapter

  @property
  def controller_name (self):
    return self.controlAdapter.task_name

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the internal domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    print nffg_part.dump()
    log.info("Install %s domain part..." % self.name)
    # print nffg_part.dump()
    self._deploy_nfs(nffg_part=nffg_part)
    # TODO ... VNF initiation etc.
    self._deploy_flowrules(nffg_part=nffg_part)

  def _deploy_nfs (self, nffg_part):
    """
    Install the NFs mapped in the given NFFG.

    If an NF is already defined in the topology and it's state is up and
    running then the actual NF's initiation will be skipped!

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    # Remove unnecessary SG and Requirement links to avoid mess up port
    # definition of NFs
    nffg_part.clear_links(NFFG.TYPE_LINK_SG)
    nffg_part.clear_links(NFFG.TYPE_LINK_REQUIREMENT)
    # Get physical topology description from Mininet
    mn_topo = self.topoAdapter.get_topology_resource()
    # Iter through the container INFRAs in the given mapped NFFG part
    for infra in nffg_part.infras:
      if infra.infra_type not in (
           NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE):
        log.debug(
          "Infrastructure Node: %s (type: %s) is not Container type! Continue "
          "to next Node..." % (infra.short_name, infra.infra_type))
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
        connection_params = self.topoAdapter.get_agent_connection_params(
          infra.id)
        if connection_params is None:
          log.error(
            "Missing connection params for communication with the agent of "
            "Node: %s" % infra.short_name)
        # Save last used adapter --> and last RPC result
        log.debug("Initiating NF: %s with params: %s" % (nf.short_name, params))
        updated = self.remoteAdapter.update_connection_params(
          **connection_params)
        if updated:
          log.debug("Update connection params in %s: %s" % (
            self.remoteAdapter.__class__.__name__, updated))
        try:
          vnf = self.remoteAdapter.deployNF(**params)
        except RPCError:
          log.error(
            "Got RPC communication error during NF: %s initiation! Skip "
            "initiation..." % nf.name)
          continue
        # Check if NETCONF communication was OK
        if vnf is not None and vnf['initiated_vnfs']['pid'] and \
                  vnf['initiated_vnfs'][
                    'status'] == VNFStarterAPI.VNFStatus.s_UP_AND_RUNNING:
          log.info("NF: %s initiation has been verified on Node: %s" % (
            nf.short_name, infra.short_name))
        else:
          log.error(
            "Initiated NF: %s is not verified. Initiation was unsuccessful!"
            % nf.short_name)
          continue
        # Add initiated NF to topo description
        log.info("Update Infrastructure layer topology description...")
        deployed_nf = nf.copy()
        deployed_nf.ports.clear()
        mn_topo.add_nf(nf=deployed_nf)
        # Add Link between actual NF and INFRA
        for nf_id, infra_id, link in nffg_part.network.out_edges_iter((nf.id,),
                                                                      data=True):
          # Get Link's src ref to new NF's port
          # nf_port = deployed_nf.ports[link.src.id]
          # Create new Port for new NF
          nf_port = deployed_nf.ports.append(nf.ports[link.src.id].copy())

          def get_sw_port (vnf):
            """
            Return the switch port parsed from result of getVNFInfo
            """
            if isinstance(vnf['initiated_vnfs']['link'], list):
              for _link in vnf['initiated_vnfs']['link']:
                if str(_link['vnf_port']) == str(nf_port.id):
                  return int(_link['sw_port'])
            else:
              return int(vnf['initiated_vnfs']['link']['sw_port'])

          # Get OVS-generated physical port number
          infra_port_num = get_sw_port(vnf)
          if infra_port_num is None:
            log.warning(
              "Can't get Container port from RPC result! Set generated port "
              "number...")
          # Create INFRA side Port
          infra_port = mn_topo.network.node[infra_id].add_port(
            id=infra_port_num)
          # Add Links to mn topo
          l1, l2 = mn_topo.add_undirected_link(port1=nf_port, port2=infra_port,
                                               dynamic=True, delay=link.delay,
                                               bandwidth=link.bandwidth)
        log.debug("%s topology description is updated with NF: %s" % (
          self.name, deployed_nf.name))
    log.info("Initiation of NFs in NFFG part: %s is finished!" % nffg_part)

  def _deploy_flowrules(self, nffg_part):
    """
    Install the flowrules given in the NFFG.

    If a flowrule is already defined it will be updated.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    pass


class RemoteESCAPEDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with other ESCAPEv2 processes started
  in agent-mode through
  a REST-API which is provided by the Resource Orchestration Sublayer.

  .. note::
    Uses :class:`RemoteESCAPEv2RESTAdapter` for communicate with the remote
    domain.
  """
  # Domain name
  name = "REMOTE-ESCAPE"

  def __init__ (self, **kwargs):
    """
    Init
    """
    log.debug("Init RemoteESCAPEDomainManager - params: %s" % kwargs)
    super(RemoteESCAPEDomainManager, self).__init__(**kwargs)

  def init (self, configurator, **kwargs):
    """
    Initialize Internal domain manager.

    :return: None
    """
    # Init adapter for remote ESCAPEv2 domain
    self.topoAdapter = configurator.load_component(
      RemoteESCAPEv2RESTAdapter.name)

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(RemoteESCAPEDomainManager, self).finit()

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the internal domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    self.topoAdapter.install_nffg(nffg_part)


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
    Init.
    """
    log.debug("Init OpenStackDomainManager - params: %s" % kwargs)
    super(OpenStackDomainManager, self).__init__(**kwargs)

  def init (self, configurator, **kwargs):
    """
    Initialize OpenStack domain manager.

    :return: None
    """
    self.topoAdapter = configurator.load_component(OpenStackRESTAdapter.name)
    super(OpenStackDomainManager, self).init(configurator, **kwargs)

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(OpenStackDomainManager, self).finit()

  # def poll (self):
  #   try:
  #     if not self._detected:
  #       # Trying to request config
  #       raw_data = self.rest_adapter.send_request(self.rest_adapter.POST,
  #                                                 'get-config')
  #       # If no exception -> success
  #       log.info("%s agent detected!" % self.name)
  #       self._detected = True
  #       log.info("Updating resource information from %s domain..." %
  # self.name)
  #       self.update_resource_info(raw_data)
  #       self.restart_polling()
  #     else:
  #       # Just ping the agent if it's alive. If exception is raised -> problem
  #       self.rest_adapter.send_request(self.rest_adapter.GET, 'ping')
  #   except ConnectionError:
  #     if self._detected is None:
  #       # detected = None -> First try
  #       log.warning("%s agent is not detected! Keep trying..." % self.name)
  #       self._detected = False
  #     elif self._detected:
  #       # Detected before -> lost connection = big Problem
  #       log.warning(
  #         "Lost connection with %s agent! Go slow poll..." % self.name)
  #       self._detected = False
  #       self.restart_polling()
  #     else:
  #       # No success but not for the first try -> keep trying silently
  #       pass
  #   except Timeout:
  #     if self._detected is None:
  #       # detected = None -> First try
  #       log.warning("%s agent not responding!" % self.name)
  #       self._detected = False
  #     elif self._detected:
  #       # Detected before -> not responding = big Problem
  #       log.warning(
  #         "Detected %s agent not responding! Go slow poll..." % self.name)
  #       self._detected = False
  #       self.restart_polling()
  #     else:
  #       # No success but not for the first try -> keep trying silently
  #       pass
  #   except HTTPError:
  #     raise

  def install_nffg (self, nffg_part):
    log.info("Install %s domain part..." % self.name)
    # TODO - implement just convert NFFG to appropriate format and send out
    # FIXME - convert to appropriate format
    config = nffg_part.dump()
    self.topoAdapter.edit_config(config)


class UnifiedNodeDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with Unified Node (UN) domain.

  .. note::
    Uses :class:`UnifiedNodeRESTAdapter` for communicate with the remote domain.
  """
  # Domain name
  name = "UN"

  def __init__ (self, **kwargs):
    """
    Init.
    """
    log.debug("Init UnifiedNodeDomainManager - params: %s" % kwargs)
    super(UnifiedNodeDomainManager, self).__init__(**kwargs)

  def init (self, configurator, **kwargs):
    """
    Initialize OpenStack domain manager.

    :return: None
    """
    self.topoAdapter = configurator.load_component(UnifiedNodeRESTAdapter.name)
    super(UnifiedNodeDomainManager, self).init(configurator, **kwargs)

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(UnifiedNodeDomainManager, self).finit()

  def install_nffg (self, nffg_part):
    log.info("Install %s domain part..." % self.name)
    # TODO - implement just convert NFFG to appropriate format and send out
    # FIXME - convert to appropriate format
    config = nffg_part.dump()
    self.topoAdapter.edit_config(config)


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


class SDNDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with POX-controlled SDN domain.

  .. note::
    Uses :class:`InternalPOXAdapter` for controlling the network.
  """
  # Domain name
  name = "SDN"

  def __init__ (self, **kwargs):
    """
    Init
    """
    log.debug("Init SDNDomainManager - params: %s" % kwargs)
    super(SDNDomainManager, self).__init__(**kwargs)
    self.controlAdapter = None  # DomainAdapter for POX - InternalPOXAdapter
    self.topo = None  # SDN domain topology stored in NFFG

  def init (self, configurator, **kwargs):
    """
    Initialize SDN domain manager.

    :return: None
    """
    # Init adapter for internal controller: POX
    self.controlAdapter = configurator.load_component(InternalPOXAdapter.name)
    # Use the same adapter for checking resources
    self.topoAdapter = self.controlAdapter
    super(SDNDomainManager, self).init(configurator, **kwargs)

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(SDNDomainManager, self).finit()
    del self.controlAdapter

  @property
  def controller_name (self):
    return self.controlAdapter.task_name

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the SDN domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    log.info("Install %s domain part..." % self.name)
    self._deploy_flowrules(nffg_part=nffg_part)

  def _deploy_flowrules(self, nffg_part):
    """
    Install the flowrules given in the NFFG.

    If a flowrule is already defined it will be updated.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    # Remove unnecessary SG and Requirement links to avoid mess up port
    # definition of NFs
    nffg_part.clear_links(NFFG.TYPE_LINK_SG)
    nffg_part.clear_links(NFFG.TYPE_LINK_REQUIREMENT)
    # Get physical topology description from POX adapter
    topo = self.controlAdapter.get_topology_resource()
    import re  # regular expressions
    # Iter through the container INFRAs in the given mapped NFFG part
    for infra in nffg_part.infras:
      if infra.infra_type not in (
           NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
           NFFG.TYPE_INFRA_SDN_SW):
        log.debug(
          "Infrastructure Node: %s (type: %s) is not Switch or Container type! "
          "Continue to next Node..." % (infra.short_name, infra.infra_type))
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in topo.infras):
        log.error(
          "Infrastructure Node: %s is not found in the %s domain! Skip "
          "flowrule install on this Node..." % (infra.short_name, self.name))
        continue
      for flowrule in nffg_part.flowrules:
        match = {}
        action = {}
        if re.search(r';', flowrule['match']):
          # multiple elements in match field
          in_port = re.sub(r'.*in_port=(.*);.*', r'\1', flowrule.match)
        else:
          # single element in match field
          in_port = re.sub(r'.*in_port=(.*)', r'\1', flowrule.match)
        match['in_port'] = in_port
        # Check match fileds - currently only vlan_id
        # TODO: add further match fields
        if re.search(r'TAG', flowrule['match']):
          tag = re.sub(r'.*TAG=.*-(.*);?', r'\1', flowrule.match)
          match['vlan_id'] = tag

        if re.search(r';', flowrule['action']):
          # multiple elements in action field
          out = re.sub(r'.*output=(.*);.*', r'\1', flowrule.action)
        else:
          # single element in action field
          out = re.sub(r'.*output=(.*)', r'\1', flowrule.action)
        action['out'] = out

        if re.search(r'TAG', flowrule['action']):
          if re.search(r'UNTAG', flowrule['action']):
            action['vlan_pop'] = True
          else:
            push_tag = re.sub(r'.*TAG=.*-(.*);?', r'\1', flowrule.action)
            action['vlan_push'] = push_tag

        self.controlAdapter.install_flowrule(infra.id, 
                                             match=match, action=action)
