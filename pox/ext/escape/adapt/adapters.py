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
Contains Adapter classes which contains protocol and technology specific
details for the connections between ESCAPEv2 and other different domains.
"""
from copy import deepcopy

from ncclient.operations import OperationError
from ncclient.operations.rpc import RPCError
from ncclient.transport import TransportError

from escape import CONFIG, __version__
from escape.infr.il_API import InfrastructureLayerAPI
from escape.util.conversion import NFFGConverter
from escape.util.domain import *
from escape.util.netconf import AbstractNETCONFAdapter
from pox.lib.util import dpid_to_str
from virtualizer4 import Virtualizer


class TopologyLoadException(Exception):
  """
  Exception class for topology errors.
  """
  pass


class InternalPOXAdapter(AbstractOFControllerAdapter):
  """
  Adapter class to handle communication with internal POX OpenFlow controller.

  Can be used to define a controller (based on POX) for other external domains.
  """
  name = "INTERNAL-POX"
  type = AbstractESCAPEAdapter.TYPE_CONTROLLER

  # Static mapping of infra IDs and DPIDs
  infra_to_dpid = {
    # 'EE1': 0x1,
    # 'EE2': 0x2,
    # 'SW3': 0x3,
    # 'SW4': 0x4
  }
  saps = {
    # 'SW3': {
    #   'port': '3',
    #   'dl_dst': '00:00:00:00:00:01',
    #   # 'dl_src': '00:00:00:00:00:02'
    #   'dl_src': 'ff:ff:ff:ff:ff:ff'
    # },
    # 'SW4': {
    #   'port': '3',
    #   'dl_dst': '00:00:00:00:00:02',
    #   # 'dl_src': '00:00:00:00:00:01'
    #   'dl_src': 'ff:ff:ff:ff:ff:ff'
    # }
  }

  def __init__ (self, name=None, address="127.0.0.1", port=6653,
                keepalive=False, *args, **kwargs):
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
    super(InternalPOXAdapter, self).__init__(name=name, address=address,
                                             port=port, keepalive=keepalive,
                                             *args, **kwargs)
    log.debug(
      "Init %s - type: %s, address %s:%s, domain: %s, optional name: %s" % (
        self.__class__.__name__, self.type, address, port, self.domain_name,
        name))
    self.topoAdapter = None

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
    return None

  def _handle_ConnectionUp (self, event):
    """
    Handle incoming OpenFlow connections.
    """
    log.debug("Handle connection by %s" % self.task_name)
    self._identify_ovs_device(connection=event.connection)
    if self.filter_connections(event):
      event = DomainChangedEvent(domain=self.name,
                                 cause=DomainChangedEvent.TYPE.NODE_UP,
                                 data={
                                   "DPID": event.dpid,
                                   "connection": event.connection
                                 })
      self.raiseEventNoErrors(event)

  def _handle_ConnectionDown (self, event):
    """
    Handle disconnected device.
    """
    log.debug("Handle disconnection by %s" % self.task_name)
    if event.dpid in self.infra_to_dpid.itervalues():
      for k in self.infra_to_dpid:
        if self.infra_to_dpid[k] == event.dpid:
          del self.infra_to_dpid[k]
          break
      log.debug("DPID: %s removed from infra-dpid assignments" % dpid_to_str(
        event.dpid))

    event = DomainChangedEvent(domain=self.name,
                               cause=DomainChangedEvent.TYPE.NODE_DOWN,
                               data={"DPID": event.dpid})
    self.raiseEventNoErrors(event)

  def _identify_ovs_device (self, connection):
    """
    Identify the representing Node of the OVS switch according to the given
    connection and extend the dpid-infra binding dictionary.

    The discovery algorithm takes the advantage of the naming convention of
    Mininet for interfaces in an OVS switch e.g.: EE1, EE1-eth1, EE1-eth2, etc.

    :param connection: inner Connection class of POX
    :type connection: :class:`pox.openflow.of_01.Connection`
    :return: None
    """
    # Get DPID
    dpid = connection.dpid
    # Generate the list of port names from OF Feature Reply msg
    ports = [port.name for port in connection.features.ports]
    # Remove inter-domain SAP ports (starting with 'eth')
    for p in [p for p in ports if p.startswith('eth')]:
      ports.remove(p)
    # Mininet naming convention for port in OVS:
    # <bridge_name> (internal), <bridge_name>-eth<num>, ...
    # Define the internal port and use the port name (same as bridge name) as
    # the Infra id
    for port in ports:
      # If all other port starts with this name --> internal port
      if all(map(lambda p: p.startswith(port), ports)):
        from pox.lib.util import dpid_to_str
        log.debug("Identified Infra(id: %s) on OF connection: %s" % (
          port, dpid_to_str(dpid)))
        self.infra_to_dpid[port] = dpid
        return
    log.warning("No Node is identified for connection: %s" % connection)


class SDNDomainPOXAdapter(InternalPOXAdapter):
  """
  Adapter class to handle communication with external SDN switches.
  """
  name = "SDN-POX"
  type = AbstractESCAPEAdapter.TYPE_CONTROLLER

  # Static mapping of infra IDs and DPIDs - overridden at init time based on
  # the SDNAdapter configuration
  infra_to_dpid = {
    # 'MT1': 0x14c5e0c376e24,
    # 'MT2': 0x14c5e0c376fc6,
  }

  def __init__ (self, name=None, address="0.0.0.0", port=6653, keepalive=False,
                binding=None, *args, **kwargs):
    super(SDNDomainPOXAdapter, self).__init__(name=name, address=address,
                                              port=port, keepalive=keepalive,
                                              *args, **kwargs)
    # Currently static initialization from a config file
    # TODO: discover SDN topology and create the NFFG
    self.topo = None  # SDN domain topology stored in NFFG
    if not binding:
      log.warning(
        "No Infra-DPID binding are defined in the configuration! Using empty "
        "data structure...")
    elif isinstance(binding, dict):
      self.infra_to_dpid = {
        infra: int(dpid, base=0) if not isinstance(dpid, int) else dpid for
        infra, dpid in binding.iteritems()}
    else:
      log.warning(
        "Wrong type: %s for binding in %s. Using empty data structure..." % (
          type(binding), self))

  def get_topology_resource (self):
    super(SDNDomainPOXAdapter, self).get_topology_resource()

  def check_domain_reachable (self):
    super(SDNDomainPOXAdapter, self).check_domain_reachable()

  def _identify_ovs_device (self, connection):
    """
    Currently we can not detect the Connection - InfraNode bindings because
    the only available infos are the connection parameters: DPID, ports, etc.
    Skip this step for the SDN domain, the assignments are statically defined.

    :param connection: inner Connection class of POX
    :type connection: :class:`pox.openflow.of_01.Connection`
    :return: None
    """
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
  type = AbstractESCAPEAdapter.TYPE_TOPOLOGY

  def __init__ (self, net=None, *args, **kwargs):
    """
    Init.

    :param net: set pre-defined network (optional)
    :type net: :class:`ESCAPENetworkBridge`
    """
    # Call base constructors directly to avoid super() and MRO traps
    AbstractESCAPEAdapter.__init__(self, *args, **kwargs)
    log.debug(
      "Init InternalMininetAdapter - type: %s, domain: %s, initial network: "
      "%s" % (self.type, self.domain_name, net))
    if not net:
      from pox import core
      if core.core.hasComponent(InfrastructureLayerAPI._core_name):
        # reference to MN --> ESCAPENetworkBridge
        self.__IL_topo_ref = core.core.components[
          InfrastructureLayerAPI._core_name].topology
        if self.__IL_topo_ref is None:
          log.error("Unable to get emulated network reference!")

  def get_mn_wrapper (self):
    """
    Return the specific wrapper for :class:`mininet.net.Mininet` object
    represents the emulated network.

    :return: emulated network wrapper
    :rtype: :any:`ESCAPENetworkBridge`
    """
    return self.__IL_topo_ref

  def check_domain_reachable (self):
    """
    Checker function for domain polling.

    :return: the domain is detected or not
    :rtype: bool
    """
    # Direct access to IL's Mininet wrapper <-- Internal Domain
    return self.__IL_topo_ref.started

  def get_topology_resource (self):
    """
    Return with the topology description as an :any:`NFFG`.

    :return: the emulated topology description
    :rtype: :any:`NFFG`
    """
    # Direct access to IL's Mininet wrapper <-- Internal Domain
    return self.rewrite_domain(
      self.__IL_topo_ref.topo_desc) if self.__IL_topo_ref.started else None

  def get_agent_connection_params (self, ee_name):
    """
    Return the connection parameters for the agent of the switch given by the
    ``switch_name``.

    :param ee_name: name of the container Node
    :type ee_name: str
    :return: connection params
    :rtype: dict
    """
    agent = self.__IL_topo_ref.get_agent_to_switch(ee_name)
    return {
      "server": "127.0.0.1", "port": agent.agentPort,
      "username": agent.username,
      "password": agent.passwd
    } if agent is not None else {}


class SDNDomainTopoAdapter(AbstractESCAPEAdapter):
  """
  Adapter class to return the topology description of the SDN domain.

  Currently it just read the static description from file, and not discover it.
  """
  name = "SDN-TOPO"
  type = AbstractESCAPEAdapter.TYPE_TOPOLOGY

  def __init__ (self, path=None, *args, **kwargs):
    super(SDNDomainTopoAdapter, self).__init__(*args, **kwargs)
    log.debug(
      "Init SDNDomainTopoAdapter - type: %s, domain: %s, optional path: %s" % (
        self.type, self.domain_name, path))
    self.topo = None
    try:
      self.__init_from_CONFIG(path=path)
    except TopologyLoadException as e:
      log.error("SDN adapter is not initialized properly: %s" % e)

  def check_domain_reachable (self):
    """
    Checker function for domain. Naively return True.

    :return: the domain is detected or not
    :rtype: bool
    """
    return self.topo is not None

  def get_topology_resource (self):
    """
    Return with the topology description as an :any:`NFFG` parsed from file.

    :return: the static topology description
    :rtype: :any:`NFFG`
    """
    return self.topo

  def __init_from_CONFIG (self, path=None):
    """
    Load a pre-defined topology from an NFFG stored in a file.
    The file path is searched in CONFIG with tha name ``SDN-TOPO``.

    :param path: additional file path
    :type path: str
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
          self.topo = self.rewrite_domain(NFFG.parse(f.read()))
          self.topo.duplicate_static_links()
          # print self.topo.dump()
      except IOError:
        log.warning("SDN topology file not found: %s" % path)
      except ValueError as e:
        log.error(
          "An error occurred when load topology from file: %s" % e.message)
        raise TopologyLoadException("File parsing error!")


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
  type = AbstractESCAPEAdapter.TYPE_MANAGEMENT

  # RPC namespace
  # Adapter name used in CONFIG and ControllerAdapter class
  def __init__ (self, *args, **kwargs):
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
    AbstractNETCONFAdapter.__init__(self, *args, **kwargs)
    AbstractESCAPEAdapter.__init__(self, *args, **kwargs)
    log.debug(
      "Init VNFStarterAdapter - type: %s, params: %s" % (self.type, kwargs))

  def check_domain_reachable (self):
    """
    Checker function for domain polling.

    :return: the domain is detected or not
    :rtype: bool
    """
    try:
      return self.get(expr="vnf_starter/agent_name") is not None
    except:
      # in case of RPCError, TransportError, OperationError
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

  def _invoke_rpc (self, request_data):
    """
    Override parent function to catch and log exceptions gracefully.
    """
    from ncclient.transport import TransportError
    from ncclient.operations import OperationError
    try:
      super(VNFStarterAdapter, self)._invoke_rpc(request_data)
    except (RPCError, TransportError, OperationError) as e:
      log.exception("Failed to invoke NETCONF based RPC! Cause: %s", e)

  ##############################################################################
  # RPC calls starts here
  ##############################################################################

  def initiateVNF (self, vnf_type, vnf_description=None, options=None):
    """
    This RCP will start a VNF.

    0. initiate new VNF (initiate datastructure, generate unique ID)
    1. set its arguments (control port, control ip, and VNF type/command)
    2. returns the connection data, which from the vnf_id is the most important

    Reply structure:

    .. code-block:: json

      {
        "access_info":
        {
          "vnf_id": "<mandatory>",
          "control_ip": "<optional>",
          "control_port": "<optional>"
        },
      "other": "<optional>"
      }

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

    Reply structure:

    .. code-block:: json

      {
        "port": "<mandatory>  # Currently just got RPC OK",
        "other": "<optional>"
      }

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
    log.debug("Call connectVNF - VNF id: %s port: %s --> node: %s" % (
      vnf_id, vnf_port, switch_id))
    return self.call_RPC("connectVNF", vnf_id=vnf_id, vnf_port=vnf_port,
                         switch_id=switch_id)

  def disconnectVNF (self, vnf_id, vnf_port):
    """
    This RPC will disconnect the VNF(s)/CLICK(s) from the switch(es).

    0. ip link set uny_0 down
    1. ip link set uny_1 down
    2. (if more ports) repeat 1. and 2. with the corresponding data

    Reply structure:

    .. code-block:: json

      {
        "other": "<optional>  # Currently just got RPC OK"
      }

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :param vnf_port: VNF port (mandatory)
    :type vnf_port: str
    :return: reply data
    :raises: RPCError, OperationError, TransportError
    """
    log.debug("Call disconnectVNF - VNF id: %s port: %s" % (vnf_id, vnf_port))
    return self.call_RPC("disconnectVNF", vnf_id=vnf_id, vnf_port=vnf_port)

  def startVNF (self, vnf_id):
    """
    This RPC will actually start the VNF/CLICK instance.

    Reply structure:

    .. code-block:: json

      {
        "other": "<optional>  # Currently just got RPC OK"
      }

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :return: reply data
    :raises: RPCError, OperationError, TransportError
    """
    log.debug("Call startVNF - VNF id: %s" % vnf_id)
    return self.call_RPC("startVNF", vnf_id=vnf_id)

  def stopVNF (self, vnf_id):
    """
    This RPC will gracefully shut down the VNF/CLICK instance.

    0. if disconnect() was not called before, we call it
    1. delete virtual ethernet pairs
    2. stop (kill) click
    3. remove vnf's data from the data structure

    Reply structure:

    .. code-block:: json

      {
        "other": "<optional>  # Currently just got RPC OK"
      }

    :param vnf_id: VNF ID (mandatory)
    :type vnf_id: str
    :return: reply data
    :raises: RPCError, OperationError, TransportError
    """
    log.debug("Call stopVNF - VNF id: %s" % vnf_id)
    return self.call_RPC("stopVNF", vnf_id=vnf_id)

  def getVNFInfo (self, vnf_id=None):
    """
    This RPC will send back all data of all VNFs that have been initiated by
    this NETCONF Agent. If an input of vnf_id is set, only that VNF's data
    will be sent back. Most of the data this RPC replies is used for DEBUG,
    however 'status' is useful for indicating to upper layers whether a VNF
    is UP_AND_RUNNING.

    Reply structure:

    .. code-block:: json

      {
        "initiated_vnfs":
        {
          "vnf_id": "<initiated_vnfs key>",
          "pid": "<VNF PID>",
          "control_ip": "<cntr IP>",
          "control_port": "<cntr port>",
          "command": "<VNF init command>",
          "link":
          [
            {
              "vnf_port": "<port of VNF end>",
              "vnf_dev": "<VNF end intf>",
              "vnf_dev_mac": "<VNF end MAC address>",
              "sw_dev": "<switch/EE end intf>",
              "sw_id": "<switch/EE end id>",
              "sw_port": "<switch/EE end port>",
              "connected": "<conn status>"
            }
          ],
        "other": "<optional>"
        }
      }

    :param vnf_id: VNF ID  (default: list info about all VNF)
    :type vnf_id: str
    :return: reply data
    :raises: RPCError, OperationError, TransportError
    """
    log.debug(
      "Call getVNFInfo - VNF id: %s" % vnf_id if vnf_id is not None else "all")
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
        log.error("Got Error during deployVNF through NETCONF:")
        raise
      except KeyError as e:
        log.warning(
          "Missing required attribute from NETCONF-based RPC reply: %s! Skip "
          "VNF initiation." % e.args[0])
      except (TransportError, OperationError) as e:
        log.error(
          "Failed to deploy NF due to a connection error! Cause: %s" % e)

  def removeNF (self, vnf_id):
    """
    Stop and remove the given NF using the general RPC calls.
    """
    with self as adapter:
      try:
        # Stop and remove VNF
        return adapter.stopVNF(vnf_id=vnf_id)
      except RPCError as e:
        log.error("Got Error during removeVNF through NETCONF:")
        raise
      except KeyError as e:
        log.warning(
          "Missing required attribute from NETCONF-based RPC reply: %s! Skip "
          "VNF initiation." % e.args[0])
      except (TransportError, OperationError) as e:
        log.error(
          "Failed to remove NF due to a connection error! Cause: %s" % e)


class RemoteESCAPEv2RESTAdapter(AbstractRESTAdapter, AbstractESCAPEAdapter,
                                RemoteESCAPEv2API):
  """
  This class is devoted to provide REST specific functions for remote ESCAPEv2
  domain.
  """
  name = "ESCAPE-REST"
  type = AbstractESCAPEAdapter.TYPE_REMOTE

  def __init__ (self, url, prefix="", unify_interface=False, **kwargs):
    """
    Init.

    :param url: remote ESCAPEv2 RESTful API URL
    :type url: str
    """
    AbstractRESTAdapter.__init__(self, base_url=url, prefix=prefix, **kwargs)
    AbstractESCAPEAdapter.__init__(self, **kwargs)
    log.debug(
      "Init RemoteESCAPEv2RESTAdapter - type: %s, domain: %s, URL: %s" % (
        self.type, self.domain_name, url))
    # Converter for the Adapter
    self.converter = None
    self._unify_interface = unify_interface
    # Cache for parsed virtualizer
    self.virtualizer = None
    # Empty data structures for domain deletions
    self._original_nffg = None
    self._original_virtualizer = None
    if self._unify_interface:
      log.info("Setup ESCAPEv2 adapter as a Unify interface!")
      self.converter = NFFGConverter(domain=self.domain_name, logger=log,
                                     ensure_unique_id=CONFIG.ensure_unique_id())

  def ping (self):
    log.debug("Send ping request to remote agent: %s" % self._base_url)
    return self.send_no_error(self.GET, 'ping')

  def get_config (self, filter=None):
    log.debug("Send get-config request to remote agent: %s" % self._base_url)
    # Get topology from remote agent handling every exception
    data = self.send_no_error(self.POST, 'get-config')
    if data:
      # Got data
      log.debug("Received config from remote agent at %s" % self._base_url)
      log.debug("Detected response format: %s" %
                self.get_last_response_headers().get("Content-Type", "None"))
      # Convert raw data to appropriate format
      log.info("Parse and load received data...")
      # If API is set as UNIFY-based interface use XML-based Virtualizer format
      if self._unify_interface:
        # If content-type is set
        if self.get_last_response_headers().get("Content-Type",
                                                "") != "application/xml":
          log.error(
            "Content type of response message is not 'application/xml'!")
          return
        elif not data.startswith("<?xml version="):
          log.error("Received data is not started with XML declaration!")
          return
        log.debug("Converting from XML/Virtualizer to NFFG format...")
        # Covert from XML-based Virtualizer to NFFG
        nffg, virt = self.converter.parse_from_Virtualizer(vdata=data,
                                                           with_virt=True)
        log.log(VERBOSE,
                "Received message to 'get-config' request:\n%s" % virt.xml())
        log.log(VERBOSE,
                "Converted NFFG of 'get-config' response:\n%s" % nffg.dump())
        # Cache virtualizer
        self.virtualizer = virt
        if self._original_virtualizer is None:
          log.debug(
            "Store Virtualizer(id: %s, name: %s) as the original domain "
            "config for domain: %s..." % (
              virt.id.get_as_text(), virt.name.get_as_text(),
              self.domain_name))
          self._original_virtualizer = deepcopy(virt)
      else:
        log.debug("Converting to internal NFFG format...")
        nffg = NFFG.parse(data)
        # Store original config for domain resetting
        if self._original_nffg is None:
          log.debug(
            "Store %s as the original domain config for domain: %s..." % (
              nffg, self.domain_name))
          self._original_nffg = nffg.copy()
      log.debug("Set domain to %s" % self.domain_name)
      self.rewrite_domain(nffg)
      return nffg
    else:
      log.error("No data is received from remote agent at %s!" % self._base_url)
      return

  def edit_config (self, data, diff=False):
    log.debug(
      "Prepare edit-config request for remote agent at: %s" % self._base_url)
    if isinstance(data, NFFG):
      # convert NFFG --> Virtualizer
      if self._unify_interface:
        log.debug("Convert NFFG to XML/Virtualizer format...")
        virt_data = self.converter.adapt_mapping_into_Virtualizer(
          virtualizer=self.virtualizer, nffg=data)
        if diff:
          log.debug("Generating diff of mapping changes...")
          virt_data = self.virtualizer.diff(target=virt_data)
        else:
          log.debug("Using the full Virtualizer as mapping request")
        data = virt_data.xml()
      # non-UNIFY interface --> no conversion
      else:
        data = data.dump()
    elif isinstance(data, Virtualizer):
      # already in Virtualizer format
      if self._unify_interface:
        if diff:
          log.debug("Generating diff of mapping changes...")
          data = self.virtualizer.diff(target=data)
        else:
          log.debug("Using the full Virtualizer as mapping request")
        data = data.xml()
      # Unexpected case, try to convert anyway
      else:
        log.warning(
          "Unexpected case: convert Virtualizer data for a non-UNIFY "
          "interface!")
        converted = self.converter.parse_from_Virtualizer(vdata=data.xml())
        data = converted.dump()
    else:
      raise RuntimeError(
        "Not supported config format: %s for 'edit-config'!" % type(data))
    log.debug(
      "Send topology description to domain agent at %s..." % self._base_url)
    log.log(VERBOSE, "Generated Virtualizer for domain: %s:\n%s" % (
      data, self.domain_name))
    try:
      result = self.send_with_timeout(self.POST, 'edit-config', data)
      log.info("Topology description has been sent!")
      return result
    except Timeout:
      log.warning(
        "Reached timeout(%ss) while waiting for edit-config response! Ignore "
        "exception..." % self.CONNECTION_TIMEOUT)
      # Ignore exception - assume the request was successful -> return True
      return True

  def check_domain_reachable (self):
    return self.ping()

  def get_topology_resource (self):
    return self.get_config()

  def get_original_topology (self):
    """
    Return the original according to the Unify interface is enabled or not.

    :return: the original topology
    :rtype: :any:`NFFG` or Virtualizer
    """
    return self._original_virtualizer if self._unify_interface else \
      self._original_nffg


class UnifyRESTAdapter(AbstractRESTAdapter, AbstractESCAPEAdapter,
                       DefaultUnifyDomainAPI):
  """
  Implement the unified way to communicate with "Unify" domains which are
  using REST-API and the "Virtualizer" XML-based format.
  """
  # Set custom header
  custom_headers = {
    'User-Agent': "ESCAPE/" + __version__,
    # XML-based Virtualizer format
    'Accept': "application/xml"
  }
  # Adapter name used in CONFIG and ControllerAdapter class
  name = "UNIFY-REST"
  # type of the Adapter class - use this name for searching Adapter config
  type = AbstractESCAPEAdapter.TYPE_REMOTE

  def __init__ (self, url, prefix="", *args, **kwargs):
    """
    Init.

    :param url: url of RESTful API
    :type url: str
    """
    AbstractRESTAdapter.__init__(self, base_url=url, prefix=prefix, **kwargs)
    AbstractESCAPEAdapter.__init__(self, **kwargs)
    log.debug("Init UNIFYRESTAdapter - type: %s, domain: %s, URL: %s" % (
      self.type, self.domain_name, url))
    # Converter object
    self.converter = NFFGConverter(domain=self.domain_name, logger=log,
                                   ensure_unique_id=CONFIG.ensure_unique_id())
    # Cache for parsed virtualizer
    self.last_virtualizer = None
    self._original_virtualizer = None

  def ping (self):
    log.debug("Send ping request to remote agent: %s" % self._base_url)
    return self.send_no_error(self.GET, 'ping')

  def get_config (self, filter=None):
    """
    Queries the infrastructure view with a netconf-like "get-config" command.

    Remote domains always send full-config if ``filter`` is not set.

    :param filter: request a filtered description instead of full
    :type filter: str
    :return: infrastructure view as an :any:`NFFG`
    :rtype: :any::`NFFG`
    """
    log.debug("Send get-config request to remote agent: %s" % self._base_url)
    # Get topology from remote agent handling every exception
    data = self.send_no_error(self.POST, 'get-config')
    if data:
      # Got data
      log.debug("Received config from remote %s domain agent at %s" % (
        self.domain_name, self._base_url))
      log.debug("Detected response format: %s" %
                self.get_last_response_headers().get("Content-Type", "None"))
      log.info("Parse and load received data...")
      if not data.startswith("<?xml version="):
        log.error("Received data is not in XML format!")
        return
      # Covert from XML-based Virtualizer to NFFG
      nffg, virt = self.converter.parse_from_Virtualizer(vdata=data,
                                                         with_virt=True)
      log.log(VERBOSE,
              "Received message to 'get-config' request:\n%s" % virt.xml())
      log.log(VERBOSE,
              "Converted NFFG of 'get-config' response:\n%s" % nffg.dump())
      # Cache virtualizer
      self.last_virtualizer = virt
      if self._original_virtualizer is None:
        log.debug(
          "Store Virtualizer(id: %s, name: %s) as the original domain "
          "config..." % (virt.id.get_value(), virt.name.get_value()))
        self._original_virtualizer = deepcopy(virt)
      log.debug("Used domain for conversion: %s" % self.domain_name)
      return nffg
    else:
      log.error("No data is received from remote agent at %s!" % self._base_url)
      return

  def edit_config (self, data, diff=False):
    """
    Send the requested configuration with a netconf-like "edit-config" command.

    Remote domains always expect diff of mapping changes.

    :param data: whole domain view
    :type data: :any::`NFFG`
    :param diff: send the diff of the mapping request (default: False)
    :param diff: bool
    :return: status code
    :rtype: str
    """
    log.debug(
      "Prepare edit-config request for remote agent at: %s" % self._base_url)
    if isinstance(data, NFFG):
      log.debug("Convert NFFG to XML/Virtualizer format...")
      vdata = self.converter.adapt_mapping_into_Virtualizer(
        virtualizer=self.last_virtualizer, nffg=data)
    elif isinstance(data, Virtualizer):
      # Nothing to do
      vdata = data
    else:
      raise RuntimeError(
        "Not supported config format: %s for 'edit-config'!" % type(data))
    if diff:
      log.debug("Generating diff of mapping changes...")
      vdata = self.last_virtualizer.diff(target=vdata)
    else:
      log.debug("Using the full Virtualizer as mapping request")
    plain_data = vdata.xml()
    log.debug("Send NFFG to %s domain agent at %s..." % (
      self.domain_name, self._base_url))
    log.debug(
      "Send topology description to domain agent at %s..." % self._base_url)
    log.log(VERBOSE, "Generated Virtualizer:\n%s" % plain_data)
    try:
      result = self.send_with_timeout(self.POST, 'edit-config', plain_data)
      log.info("Topology description has been sent!")
      return result
    except Timeout:
      log.warning(
        "Reached timeout(%ss) while waiting for edit-config response! Ignore "
        "exception..." % self.CONNECTION_TIMEOUT)
      # Ignore exception - assume the request was successful -> return True
      return True

  def check_domain_reachable (self):
    return self.ping()

  def get_topology_resource (self):
    return self.get_config()


class OpenStackRESTAdapter(AbstractRESTAdapter, AbstractESCAPEAdapter,
                           OpenStackAPI):
  """
  This class is devoted to provide REST specific functions for OpenStack
  domain.

  .. warning::
    Not maintained anymore! Use general :any:`UnifyRESTAdapter` instead of
    this class.

  """
  # Set custom header
  custom_headers = {
    'User-Agent': "ESCAPE/" + __version__,
    # XML-based Virtualizer format
    'Accept': "application/xml"
  }
  # Adapter name used in CONFIG and ControllerAdapter class
  name = "OpenStack-REST"
  type = AbstractESCAPEAdapter.TYPE_REMOTE

  def __init__ (self, url, prefix="", *args, **kwargs):
    """
    Init.

    :param url: OpenStack RESTful API URL
    :type url: str
    """
    log.debug(
      "Init OpenStackRESTAdapter - type: %s, URL: %s" % (self.type, url))
    AbstractRESTAdapter.__init__(self, base_url=url, prefix=prefix)
    log.debug("base URL is set to %s" % url)
    AbstractESCAPEAdapter.__init__(self, *args, **kwargs)
    # Converter object
    self.converter = NFFGConverter(domain=self.domain_name, logger=log,
                                   ensure_unique_id=CONFIG.ensure_unique_id())
    # Cache for parsed virtualizer
    self.virtualizer = None
    self._original_virtualizer = None

  def ping (self):
    return self.send_no_error(self.GET, 'ping')

  def get_config (self, filter=None):
    data = self.send_no_error(self.POST, 'get-config')
    if data:
      log.info("Parse and load received data...")
      if not data.startswith("<?xml version="):
        log.error("Received data is not in XML!")
        return
      # Covert from XML-based Virtualizer to NFFG
      nffg, virt = self.converter.parse_from_Virtualizer(vdata=data,
                                                         with_virt=True)
      # Cache virtualizer
      self.virtualizer = virt
      if self._original_virtualizer is None:
        log.debug(
          "Store Virtualizer(id: %s, name: %s) as the original domain "
          "config..." % (
            virt.id.get_as_text(), virt.name.get_as_text()))
        self._original_virtualizer = deepcopy(virt)
      # print nffg.dump()
      return nffg

  def edit_config (self, data, diff=False):
    if isinstance(data, NFFG):
      log.debug("Convert NFFG to XML/Virtualizer format...")
      virt_data = self.converter.adapt_mapping_into_Virtualizer(
        virtualizer=self.virtualizer, nffg=data)
      data = self.virtualizer.diff(virt_data).xml()
    elif isinstance(data, Virtualizer):
      data = self.virtualizer.diff(data).xml()
    else:
      raise RuntimeError(
        "Not supported config format: %s for 'edit-config'!" % type(data))
    return self.send_no_error(self.POST, 'edit-config', data)

  def check_domain_reachable (self):
    return self.ping()

  def get_topology_resource (self):
    return self.get_config()


class UniversalNodeRESTAdapter(AbstractRESTAdapter, AbstractESCAPEAdapter,
                               UniversalNodeAPI):
  """
  This class is devoted to provide REST specific functions for UN domain.

  .. warning::
    Not maintained anymore! Use general :any:`UnifyRESTAdapter` instead of
    this class.
  """
  # Set custom header
  custom_headers = {
    'User-Agent': "ESCAPE/" + __version__,
    # XML-based Virtualizer format
    'Accept': "application/xml"
  }
  # Adapter name used in CONFIG and ControllerAdapter class
  name = "UN-REST"
  type = AbstractESCAPEAdapter.TYPE_REMOTE

  def __init__ (self, url, prefix="", *args, **kwargs):
    """
    Init.

    :param url: Universal Node RESTful API URL
    :type url: str
    """
    log.debug(
      "Init UniversalNodeRESTAdapter - type: %s, URL: %s" % (self.type, url))
    AbstractRESTAdapter.__init__(self, base_url=url, prefix=prefix)
    log.debug("base URL is set to %s" % url)
    AbstractESCAPEAdapter.__init__(self, *args, **kwargs)
    # Converter object
    self.converter = NFFGConverter(domain=self.domain_name, logger=log,
                                   ensure_unique_id=CONFIG.ensure_unique_id())
    # Cache for parsed virtualizer
    self.virtualizer = None
    self._original_virtualizer = None

  def ping (self):
    return self.send_no_error(self.GET, 'ping')

  def get_config (self, filter=None):
    data = self.send_no_error(self.POST, 'get-config')
    log.debug("Received config from remote agent at %s" % self._base_url)
    if data:
      log.info("Parse and load received data...")
      if not data.startswith("<?xml version="):
        log.error("Received data is not in XML!")
        return
      # Covert from XML-based Virtualizer to NFFG
      nffg, virt = self.converter.parse_from_Virtualizer(vdata=data,
                                                         with_virt=True)
      # Cache virtualizer
      self.virtualizer = virt
      if self._original_virtualizer is None:
        log.debug(
          "Store Virtualizer(id: %s, name: %s) as the original domain "
          "config..." % (
            virt.id.get_as_text(), virt.name.get_as_text()))
        self._original_virtualizer = deepcopy(virt)
      # print nffg.dump()
      return nffg

  def edit_config (self, data, diff=False):
    if isinstance(data, NFFG):
      log.debug("Convert NFFG to XML/Virtualizer format...")
      virt_data = self.converter.adapt_mapping_into_Virtualizer(
        virtualizer=self.virtualizer, nffg=data)
      data = self.virtualizer.diff(virt_data).xml()
    elif isinstance(data, Virtualizer):
      data = self.virtualizer.diff(data).xml()
    else:
      raise RuntimeError(
        "Not supported config format: %s for 'edit-config'!" % type(data))
    return self.send_no_error(self.POST, 'edit-config', data)

  def check_domain_reachable (self):
    return self.ping()

  def get_topology_resource (self):
    return self.get_config()
