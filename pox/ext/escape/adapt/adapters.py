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
from requests.exceptions import ConnectionError, HTTPError, Timeout

from ncclient.operations import OperationError
from ncclient.operations.rpc import RPCError

from ncclient.transport import TransportError

from escape.infr.il_API import InfrastructureLayerAPI
from escape.util.conversion import NFFGConverter
from escape.util.domain import *
from escape.util.netconf import AbstractNETCONFAdapter
from escape import CONFIG


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

  # Static mapping of infra IDs and DPIDs
  infra_to_dpid = {'EE1': 0x1,
                   'EE2': 0x2,
                   'SW3': 0x3,
                   'SW4': 0x4, }
  dpid_to_infra = {0x1: 'EE1',
                   0x2: 'EE2',
                   0x3: 'SW3',
                   0x4: 'SW4'}
  saps = {'SW3': {'port': '3',
                  'dl_dst': '00:00:00:00:00:01',
                  'dl_src': '00:00:00:00:00:02'},
          'SW4': {'port': '3',
                  'dl_dst': '00:00:00:00:00:02',
                  'dl_src': '00:00:00:00:00:01'}}
  
  def __init__ (self, name=None, address="127.0.0.1", port=6653,
                keepalive=False):
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
    log.debug("Init %s with address %s:%s, optional name: %s" % (
      self.__class__.__name__, address, port, name))
    super(InternalPOXAdapter, self).__init__(name=name, address=address,
                                             port=port, keepalive=keepalive)
  
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


class SDNDomainPOXAdapter(InternalPOXAdapter):
  """
  Adapter class to handle communication with external SDN switches.
  """
  name = "SDN-POX"

  # Static mapping of infra IDs and DPIDs
  infra_to_dpid = {'MT1': 0x11,  # 0x14c5e0c376e24,
                   'MT2': 0x12,  # 0x14c5e0c376fc6,
                   }
  dpid_to_infra = {0x11: 'MT1',  # 0x14c5e0c376e24: 'MT1',
                   0x12: 'MT2',  # 0x14c5e0c376fc6: 'MT2',
                   }
  
  def __init__ (self, name=None, address="0.0.0.0", port=6653, keepalive=False):
    super(SDNDomainPOXAdapter, self).__init__(name=name, address=address,
                                              port=port, keepalive=keepalive)
    # Currently static initialization from a config file
    # TODO: discover SDN topology and create the NFFG
    self.topo = None  # SDN domain topology stored in NFFG

  def get_topology_resource (self):
    super(SDNDomainPOXAdapter, self).get_topology_resource()

  def check_domain_reachable (self):
    super(SDNDomainPOXAdapter, self).check_domain_reachable()


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


class SDNDomainTopoAdapter(AbstractESCAPEAdapter):
  """
  Adapter class to return the topology description of the SDN domain.

  Currently it just read the static description from file, and not discover it.
  """
  name = "SDN-topo"

  def __init__ (self, path=None):
    log.debug("Init SDNDomainTopoAdapter with optional path: %s" % path)
    super(SDNDomainTopoAdapter, self).__init__()
    self.topo = None
    self.__init_from_CONFIG(path=path)

  def check_domain_reachable (self):
    """
    Checker function for domain. Naively return True.

    :return: the domain is detected or not
    :rtype: bool
    """
    return True

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
          self.topo = NFFG.parse(f.read())
          self.topo.duplicate_static_links()
          # print self.topo.dump()
      except IOError:
        log.debug("SDN topology file not found: %s" % path)
        raise TopologyLoadException("Missing topology file!")
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
      log.error("Failed to invoke NETCONF based RPC! Cause: %s", e)
  
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
        log.error("Got Error during deployVNF through NETCONF:")
        # from pprint import pprint
        # pprint(e.to_dict())
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
        # return adapter.stopVNF(vnf_id=vnf_id)
        reply = adapter.stopVNF(vnf_id=vnf_id)
        from pprint import pprint
        pprint(adapter.getVNFInfo())
        return reply
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
  
  def __init__ (self, url):
    """
    Init.

    :param url: remote ESCAPEv2 RESTful API URL
    :type url: str
    """
    log.debug("Init RemoteESCAPEv2RESTAdapter with URL: %s" % url)
    AbstractRESTAdapter.__init__(self, base_url=url)
    log.debug("RemoteESCAPEv2 base URL is set to %s" % self._base_url)
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
  
  def get_config (self):
    try:
      data = self.send_request(self.POST, 'get-config')
      log.debug("Received config from remote agent at %s" % self._base_url)
    except ConnectionError:
      log.warning(
        "Remote ESCAPEv2 agent (%s) is not reachable!" % self._base_url)
      return None
    except Timeout:
      log.warning("Remote ESCAPEv2 agent (%s) not responding!" % self._base_url)
      return None
    except HTTPError as e:
      log.warning("Remote ESCAPEv2 agent responded with an error during "
                  "'get-config': %s" % e.message)
      return None
    if data:
      log.info("Parse and load received data...")
      log.debug("Converting to NFFG format...")
      nffg = NFFG.parse(data)
      log.debug("Set Domain type to %s" % NFFG.DOMAIN_REMOTE)
      for infra in nffg.infras:
        infra.domain = NFFG.DOMAIN_REMOTE
      return nffg
  
  def edit_config (self, config):
    if not isinstance(config, (str, unicode, NFFG)):
      raise RuntimeError("Not supported config format for 'edit-config'!")
    try:
      log.debug("Send NFFG to domain agent at %s..." % self._base_url)
      self.send_request(self.POST, 'edit-config', config)
    except ConnectionError:
      log.warning(
        "Remote ESCAPEv2 agent (%s) is not reachable!" % self._base_url)
      return None
    except HTTPError as e:
      log.warning(
        "Remote ESCAPEv2 responded with an error during 'edit-config': %s" %
        e.message)
      return None
    return self._response.status_code
  
  def check_domain_reachable (self):
    return self.ping()
  
  def get_topology_resource (self):
    return self.get_config()


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
    # Converter object
    self.converter = NFFGConverter(domain=NFFG.DOMAIN_OS, logger=log)
    # Cache for parsed virtualizer
    self.virtualizer = None
    self.original_virtualizer = None
  
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
      log.debug("Received config from remote agent at %s" % self._base_url)
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
    if data:
      log.info("Parse and load received data...")
      # Covert from XML-based Virtualizer to NFFG
      nffg, virt = self.converter.parse_from_Virtualizer3(xml_data=data)
      # Cache virtualizer
      self.virtualizer = virt
      if self.original_virtualizer is None:
        log.debug(
          "Store Virtualizer(id: %s, name: %s) as the original domain "
          "config..." % (
            virt.id.get_as_text(), virt.name.get_as_text()))
        self.original_virtualizer = deepcopy(virt)
      # print nffg.dump()
      return nffg
  
  def edit_config (self, data):
    if isinstance(data, NFFG):
      # virtualizer, nffg = self.converter.dump_to_Virtualizer3(nffg=data)
      # data = self.converter.unescape_output_hack(str(virtualizer))
      virt_data = self.converter.adapt_mapping_into_Virtualizer(
        virtualizer=self.virtualizer, nffg=data)
      # virt_data.bind(relative=True)
      data = virt_data.xml()
    elif not isinstance(data, (str, unicode)):
      raise RuntimeError("Not supported config format for 'edit-config'!")
    try:
      log.debug("Send NFFG to domain agent at %s..." % self._base_url)
      self.send_request(self.POST, 'edit-config', data)
    except ConnectionError:
      log.warning("OpenStack agent (%s) is not reachable!" % self._base_url)
      return None
    except HTTPError as e:
      log.warning(
        "OpenStack agent responded with an error during 'edit-config': %s" %
        e.message)
      return None
    return self._response.status_code
  
  def check_domain_reachable (self):
    return self.ping()
  
  def get_topology_resource (self):
    return self.get_config()


class UniversalNodeRESTAdapter(AbstractRESTAdapter, AbstractESCAPEAdapter,
                               UniversalNodeAPI):
  """
  This class is devoted to provide REST specific functions for UN domain.
  """
  # Adapter name used in CONFIG and ControllerAdapter class
  name = "UN-REST"
  
  def __init__ (self, url):
    """
    Init.

    :param url: Universal Node RESTful API URL
    :type url: str
    """
    log.debug("Init UniversalNodeRESTAdapter with URL: %s" % url)
    AbstractRESTAdapter.__init__(self, base_url=url)
    log.debug("Universal Node base URL is set to %s" % url)
    AbstractESCAPEAdapter.__init__(self)
    # Converter object
    self.converter = NFFGConverter(domain=NFFG.DOMAIN_UN, logger=log)
    # Cache for parsed virtualizer
    self.virtualizer = None
    self.original_virtualizer = None
  
  def ping (self):
    try:
      return self.send_request(self.GET, 'ping')
    except ConnectionError:
      log.warning(
        "Universal Node agent (%s) is not reachable!" % self._base_url)
    except Timeout:
      log.warning("Universal Node agent (%s) not responding!" % self._base_url)
    except HTTPError as e:
      log.warning(
        "Universal Node agent responded with an error during 'ping': %s" %
        e.message)
  
  def get_config (self):
    try:
      data = self.send_request(self.POST, 'get-config')
      log.debug("Received config from remote agent at %s" % self._base_url)
    except ConnectionError:
      log.warning(
        "Universal Node agent (%s) is not reachable!" % self._base_url)
      return None
    except Timeout:
      log.warning("Universal Node agent (%s) not responding!" % self._base_url)
      return None
    except HTTPError as e:
      log.warning(
        "Universal Node agent responded with an error during 'get-config': %s"
        % e.message)
      return None
    if data:
      log.info("Parse and load received data...")
      # Covert from XML-based Virtualizer to NFFG
      nffg, virt = self.converter.parse_from_Virtualizer3(xml_data=data)
      # Cache virtualizer
      self.virtualizer = virt
      if self.original_virtualizer is None:
        log.debug(
          "Store Virtualizer(id: %s, name: %s) as the original domain "
          "config..." % (
            virt.id.get_as_text(), virt.name.get_as_text()))
        self.original_virtualizer = deepcopy(virt)
      # print nffg.dump()
      return nffg
  
  def edit_config (self, data):
    if isinstance(data, NFFG):
      # virtualizer, nffg = self.converter.dump_to_Virtualizer3(nffg=data)
      # data = self.converter.unescape_output_hack(str(virtualizer))
      virt_data = self.converter.adapt_mapping_into_Virtualizer(
        virtualizer=self.virtualizer, nffg=data)
      # virt_data.bind(relative=True)
      data = virt_data.xml()
    elif not isinstance(data, (str, unicode)):
      raise RuntimeError("Not supported config format for 'edit-config'!")
    try:
      log.debug("Send NFFG to domain agent at %s..." % self._base_url)
      self.send_request(self.POST, 'edit-config', data)
    except ConnectionError:
      log.warning(
        "Universal Node agent (%s) is not reachable!" % self._base_url)
      return None
    except HTTPError as e:
      log.warning(
        "Universal Node agent responded with an error during 'edit-config': %s"
        % e.message)
      return None
    return self._response.status_code
  
  def check_domain_reachable (self):
    return self.ping()
  
  def get_topology_resource (self):
    return self.get_config()
