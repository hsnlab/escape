# Copyright 2017 Janos Czentye
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
Contains Manager class which contains the higher-level logic for complete
domain management.
"""
import pprint
import re

from ncclient import NCClientError
from ncclient.operations import OperationError
from ncclient.operations.rpc import RPCError
from ncclient.transport import TransportError

from escape.adapt import log
from escape.infr.il_API import InfrastructureLayerAPI
from escape.nffg_lib import NFFG
from escape.util.conversion import NFFGConverter
from escape.util.domain import AbstractESCAPEAdapter, VNFStarterAPI, \
  AbstractDomainManager, DomainChangedEvent
from escape.util.misc import VERBOSE
from escape.util.netconf import AbstractNETCONFAdapter
from pox.lib.util import dpid_to_str


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
    :return: None
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
    Return with the topology description as an :class:`NFFG`.

    :return: the emulated topology description
    :rtype: :class:`NFFG`
    """
    raise RuntimeError("VNFStarterAdapter does not support this function: "
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

    :return: None
    """
    try:
      return super(VNFStarterAdapter, self)._invoke_rpc(request_data)
    except NCClientError as e:
      log.error("Failed to invoke NETCONF based RPC! Cause: %s", e)
      raise

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
    :rtype: dict
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
    :rtype: dict
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
    :rtype: dict
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
    :rtype: dict
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
    :rtype: dict
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
      except RPCError:
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

    :return: reply data
    :rtype: dict
    """
    with self as adapter:
      try:
        # Stop and remove VNF
        return adapter.stopVNF(vnf_id=vnf_id)
      except RPCError:
        log.error("Got Error during removeVNF through NETCONF:")
        raise
      except KeyError as e:
        log.warning(
          "Missing required attribute from NETCONF-based RPC reply: %s! Skip "
          "VNF initiation." % e.args[0])
      except (TransportError, OperationError) as e:
        log.error(
          "Failed to remove NF due to a connection error! Cause: %s" % e)


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
    Return with the topology description as an :class:`NFFG`.

    :return: the emulated topology description
    :rtype: :class:`NFFG`
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
    return {"server": "127.0.0.1", "port": agent.agentPort,
            "username": agent.username,
            "password": agent.passwd} if agent is not None else {}


class InternalDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with internally emulated network.

  .. note::
    Uses :class:`InternalMininetAdapter` for managing the emulated network and
    :class:`InternalPOXAdapter` for controlling the network.
  """
  # DomainManager name
  name = "INTERNAL"
  # Default domain name
  DEFAULT_DOMAIN_NAME = "INTERNAL"
  # Set the internal manager status
  IS_INTERNAL_MANAGER = True

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, *args, **kwargs):
    """
    Init.

    :param domain_name: the domain name
    :type domain_name: str
    :param args: optional param list
    :type args: list
    :param kwargs: optional keywords
    :type kwargs: dict
    :return: None
    """
    log.debug("Create InternalDomainManager with domain name: %s" % domain_name)
    super(InternalDomainManager, self).__init__(domain_name=domain_name,
                                                *args, **kwargs)
    self.controlAdapter = None  # DomainAdapter for POX-InternalPOXAdapter
    self.topoAdapter = None  # DomainAdapter for Mininet-InternalMininetAdapter
    self.remoteAdapter = None  # NETCONF communication - VNFStarterAdapter
    self.portmap = {}  # Map (unique) dynamic ports to physical ports in EEs
    self.deployed_vnfs = {}  # container for replied NETCONF messages of
    # deployNF, key: (infra_id, nf_id), value: initiated_vnf part of the
    # parsed reply in JSON
    self.sapinfos = {}
    # Mapper structure for non-integer link id
    self.vlan_register = {}

  def init (self, configurator, **kwargs):
    """
    Initialize Internal domain manager.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :param kwargs: optional parameters
    :type kwargs: dict
    :return: None
    """
    # Call abstract init to execute common operations
    super(InternalDomainManager, self).init(configurator, **kwargs)
    self._collect_SAP_infos()
    self._setup_sap_hostnames()
    self.log.info("DomainManager for %s domain has been initialized!" %
                  self.domain_name)

  def initiate_adapters (self, configurator):
    """
    Initiate adapters.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :return: None
    """
    # Initiate Adapters
    self.topoAdapter = configurator.load_component(
      component_name=AbstractESCAPEAdapter.TYPE_TOPOLOGY,
      parent=self._adapters_cfg)
    # Init adapter for internal controller: POX
    self.controlAdapter = configurator.load_component(
      component_name=AbstractESCAPEAdapter.TYPE_CONTROLLER,
      parent=self._adapters_cfg)
    self.log.debug("Set %s as the topology Adapter for %s" % (
      self.topoAdapter.__class__.__name__,
      self.controlAdapter.__class__.__name__))
    # Init default NETCONF adapter
    self.remoteAdapter = configurator.load_component(
      component_name=AbstractESCAPEAdapter.TYPE_MANAGEMENT,
      parent=self._adapters_cfg)

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(InternalDomainManager, self).finit()
    self.remoteAdapter.finit()
    self.controlAdapter.finit()
    self.topoAdapter.finit()

  @property
  def controller_name (self):
    """
    Return with the name of the controller name.

    :return: controller name
    :rtype: str
    """
    return self.controlAdapter.task_name

  def _setup_sap_hostnames (self):
    """
    Setup hostnames in /etc/hosts for SAPs.

    :return: None
    """
    # Update /etc/hosts with hostname - IP address mapping
    import os
    os.system("sed '/# BEGIN ESCAPE SAPS/,/# END ESCAPE SAPS/d' "
              "/etc/hosts > /etc/hosts2")
    os.system("mv /etc/hosts2 /etc/hosts")
    hosts = "# BEGIN ESCAPE SAPS \n"
    for sap, info in self.sapinfos.iteritems():
      hosts += "%s %s \n" % (info['nw_dst'], sap)
    hosts += "# END ESCAPE SAPS \n"
    with open('/etc/hosts', 'a') as f:
      f.write(hosts)
    self.log.debug("Setup SAP hostnames: %s" % "; ".join(
      ["%s --> %s" % (sap, info['nw_dst']) for sap, info in
       self.sapinfos.iteritems()]))

  def _collect_SAP_infos (self):
    """
    Collect necessary information from SAPs for traffic steering.

    :return: None
    """
    log.debug("Collect SAP info...")
    mn = self.topoAdapter.get_mn_wrapper().network
    topo = self.topoAdapter.get_topology_resource()
    if topo is None or mn is None:
      self.log.error("Missing topology description from topology Adapter! "
                     "Skip SAP data discovery.")
    for sap in topo.saps:
      # skip inter-domain SAPs
      if sap.binding is not None:
        continue
      connected_node = [(v, link.dst.id) for u, v, link in
                        topo.real_out_edges_iter(sap.id)]
      if len(connected_node) > 1:
        self.log.warning("%s is connection to multiple nodes (%s)!" % (
          sap, [n[0] for n in connected_node]))
      for node in connected_node:
        mac = mn.getNodeByName(sap.id).MAC()
        ip = mn.getNodeByName(sap.id).IP()
        self.log.debug("Detected IP(%s) | MAC(%s) for %s connected to Node(%s) "
                       "on port: %s" % (ip, mac, sap, node[0], node[1]))
        if node[0] not in self.controlAdapter.saps:
          self.controlAdapter.saps[node[0]] = {}
        sapinfo = {'dl_src': "ff:ff:ff:ff:ff:ff",
                   'dl_dst': str(mac),
                   'nw_dst': str(ip)}
        self.controlAdapter.saps[node[0]][str(node[1])] = sapinfo
        self.sapinfos[str(sap.id)] = sapinfo

  def install_nffg (self, nffg_part):
    """
    Install an :class:`NFFG` related to the internal domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :class:`NFFG`
    :return: installation was success or not
    :rtype: bool
    """
    self.log.info(">>> Install %s domain part..." % self.domain_name)
    try:
      # Mininet domain does not support NF migration directly -->
      # Remove unnecessary and moved NFs first
      result = [
        self._delete_running_nfs(nffg=nffg_part),
        # then (re)initiate mapped NFs
        self._deploy_new_nfs(nffg=nffg_part)
      ]
      if not all(result):
        self.log.warning("Skip traffic steering due to NF initiation error(s)!")
        return all(result)
      self.log.info(
        "Perform traffic steering according to mapped tunnels/labels...")
      # OpenFlow flowrule deletion/addition is fairly cheap operations
      # The most robust solution is to delete every flowrule
      result.extend((self._delete_flowrules(nffg=nffg_part),
                     # and (re)add the new ones
                     self._deploy_flowrules(nffg_part=nffg_part)))
      return all(result)
    except:
      self.log.exception("Got exception during NFFG installation into: %s." %
                         self.domain_name)
      return False

  def clear_domain (self):
    """
    Infrastructure Layer has already been stopped and probably cleared.

    Skip cleanup process here.

    :return: cleanup result
    :rtype: bool
    """
    if not self.topoAdapter.check_domain_reachable():
      # This would be the normal behaviour if ESCAPEv2 is shutting down -->
      # Infrastructure layer has been cleared.
      self.log.debug("%s domain has already been cleared!" % self.domain_name)
      return True
    result = (self._delete_running_nfs(),  # Just for sure remove NFs
              self._delete_flowrules())  # and flowrules
    return all(result)

  def reset_domain (self):
    self.clear_domain()

  def _delete_running_nfs (self, nffg=None):
    """
    Stop and delete deployed NFs which are not existed the new mapped request.
    Mininet domain does not support NF migration and assume stateless network
    functions.

    Detect if an NF was moved during the previous mapping and
    remove that gracefully.

    If the ``nffg`` parameter is not given, skip the NF migration detection
    and remove all non-existent NF by default.

    :param nffg: the last mapped NFFG part
    :type nffg: :class:`NFFG`
    :return: deletion was successful or not
    :rtype: bool
    """
    result = True
    topo = self.topoAdapter.get_topology_resource()
    if topo is None:
      self.log.warning("Missing topology description from %s domain! "
                       "Skip deleting NFs..." % self.domain_name)
      return False
    self.log.debug("Check for removable NFs...")
    # Skip non-execution environments
    infras = [i.id for i in topo.infras if
              i.infra_type in (NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE)]
    for infra_id in infras:
      # Generate list of newly mapped NF on the infra
      old_running_nfs = [n.id for n in topo.running_nfs(infra_id)]
      # Detect non-moved NF if new mapping was given and skip deletion
      for nf_id in old_running_nfs:
        # If NF exist in the new mapping
        if nffg is not None and nf_id in nffg:
          new_running_nfs = [n.id for n in nffg.running_nfs(infra_id)]
          # And connected to the same infra
          if nf_id in new_running_nfs:
            # NF was not moved, Skip deletion
            self.log.debug('Unchanged NF: %s' % nf_id)
            continue
          # If the NF exists in the new mapping, but moved to another infra
          else:
            self.log.info("Found moved NF: %s")
            self.log.debug(
              "NF migration is not supported! Stop and remove already "
              "deployed NF and reinitialize later...")
        else:
          self.log.debug("Found removable NF: %s" % nf_id)
        # Create connection Adapter to EE agent
        connection_params = self.topoAdapter.get_agent_connection_params(
          infra_id)
        if connection_params is None:
          self.log.error("Missing connection params for communication with the "
                         "agent of Node: %s" % infra_id)
          result = False
          continue
        updated = self.remoteAdapter.update_connection_params(
          **connection_params)
        if updated:
          self.log.debug("Update connection params in %s: %s" % (
            self.remoteAdapter.__class__.__name__, updated))
        self.log.debug("Stop deployed NF: %s" % nf_id)
        try:
          vnf_id = self.deployed_vnfs[(infra_id, nf_id)]['vnf_id']
          reply = self.remoteAdapter.removeNF(vnf_id=vnf_id)
          self.log.log(VERBOSE,
                       "Removed NF status:\n%s" % pprint.pformat(reply))
          # Remove NF from deployed cache
          del self.deployed_vnfs[(infra_id, nf_id)]
          # Delete infra ports connected to the deletable NF
          for u, v, link in topo.network.out_edges([nf_id], data=True):
            topo[v].del_port(id=link.dst.id)
          # Delete NF
          topo.del_node(nf_id)
        except KeyError:
          self.log.error("Deployed VNF data for NF: %s is not found! "
                         "Skip deletion..." % nf_id)
          result = False
          continue
        except NCClientError as e:
          self.log.error("Got NETCONF RPC communication error during NF: %s "
                         "deletion! Skip deletion..." % nf_id)
          self.log.error(VERBOSE, "Exception: %s" % e)
          result = False
          continue
    self.log.debug("NF deletion result: %s" %
                   ("SUCCESS" if result else "FAILURE"))
    return result

  def _deploy_new_nfs (self, nffg):
    """
    Install the NFs mapped in the given NFFG.

    If an NF is already defined in the topology and it's state is up and
    running then the actual NF's initiation will be skipped!

    :param nffg: container NF-FG part need to be deployed
    :type nffg: :class:`NFFG`
    :return: deploy was successful or not
    :rtype: bool
    """
    self.log.info("Deploy mapped NFs into the domain: %s..." % self.domain_name)
    result = True
    self.portmap.clear()
    # Remove unnecessary SG and Requirement links to avoid mess up port
    # definition of NFs
    nffg.clear_links(NFFG.TYPE_LINK_SG)
    nffg.clear_links(NFFG.TYPE_LINK_REQUIREMENT)
    # Get physical topology description from Mininet
    mn_topo = self.topoAdapter.get_topology_resource()
    if mn_topo is None:
      self.log.warning("Missing topology description from %s domain! "
                       "Skip deploying NFs..." % self.domain_name)
      return False
    # Iter through the container INFRAs in the given mapped NFFG part
    # print mn_topo.dump()
    for infra in nffg.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE):
        self.log.debug(
          "Infrastructure Node: %s (type: %s) is not Container type! "
          "Continue to next Node..." % (infra.id, infra.infra_type))
        continue
      else:
        self.log.debug("Check NFs mapped on Node: %s" % infra.id)
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in self.internal_topo.infras):
        self.log.error("Infrastructure Node: %s is not found in the %s domain! "
                       "Skip NF initiation on this Node..." %
                       (infra.id, self.domain_name))
        result = False
        continue
      # Iter over the NFs connected the actual INFRA
      for nf in nffg.running_nfs(infra.id):
        # NF with id is already deployed --> change the dynamic port to
        # static and continue
        if nf.id in (nf.id for nf in self.internal_topo.nfs):
          self.log.debug("NF: %s has already been initiated! "
                         "Continue to next NF..." % nf.id)
          for u, v, link in nffg.real_out_edges_iter(nf.id):
            dyn_port = nffg[v].ports[link.dst.id]
            for x, y, l in mn_topo.real_out_edges_iter(nf.id):
              if l.src.id == link.src.id:
                self.portmap[dyn_port.id] = l.dst.id
                dyn_port.id = l.dst.id
                break
          continue
        # Extract the initiation params
        params = {'nf_type': nf.functional_type,
                  'nf_ports': [link.src.id for u, v, link in
                               nffg.real_out_edges_iter(nf.id)],
                  'infra_id': infra.id}
        # Check if every param is not None or empty
        if not all(params.values()):
          self.log.error("Missing arguments for initiation of NF: %s! "
                         "Extracted params: %s" % (nf.id, params))
          result = False
          continue
        # Create connection Adapter to EE agent
        connection_params = self.topoAdapter.get_agent_connection_params(
          infra.id)
        if connection_params is None:
          self.log.error("Missing connection params for communication with the "
                         "agent of Node: %s" % infra.id)
          result = False
          continue
        # Save last used adapter --> and last RPC result
        self.log.info("Initiating NF: %s ..." % nf.id)
        self.log.debug("NF parameters: %s" % params)
        updated = self.remoteAdapter.update_connection_params(
          **connection_params)
        if updated:
          self.log.debug("Update connection params in %s: %s" % (
            self.remoteAdapter.__class__.__name__, updated))
        try:
          vnf = self.remoteAdapter.deployNF(**params)
        except NCClientError as e:
          self.log.error("Got NETCONF RPC communication error during NF: %s "
                         "deploy! Skip deploy..." % nf.id)
          self.log.error(VERBOSE, "Exception: %s" % e)
          result = False
          continue
        except BaseException:
          self.log.error("Got unexpected error during NF: %s "
                         "initiation! Skip initiation..." % nf.name)
          result = False
          continue
        self.log.log(VERBOSE, "Initiated VNF:\n%s" % pprint.pformat(vnf))
        # Check if NETCONF communication was OK
        if vnf and 'initiated_vnfs' in vnf and vnf['initiated_vnfs']['pid'] \
           and vnf['initiated_vnfs']['status'] == \
              VNFStarterAPI.VNFStatus.s_UP_AND_RUNNING:
          self.log.info("NF: %s initiation has been verified on Node: %s" % (
            nf.id, infra.id))
          self.log.debug("Initiated VNF id: %s, PID: %s, status: %s" % (
            vnf['initiated_vnfs']['vnf_id'], vnf['initiated_vnfs']['pid'],
            vnf['initiated_vnfs']['status']))
        else:
          self.log.error("Initiated NF: %s is not verified. Initiation was "
                         "unsuccessful!" % nf.id)
          result = False
          continue
        # Store NETCONF related info of deployed NF
        self.deployed_vnfs[(infra.id, nf.id)] = vnf['initiated_vnfs']
        # Add initiated NF to topo description
        self.log.debug("Update Infrastructure layer topology description...")
        deployed_nf = nf.copy()
        deployed_nf.ports.clear()
        mn_topo.add_nf(nf=deployed_nf)
        self.log.debug("Add deployed NFs to topology...")
        # Add Link between actual NF and INFRA
        for nf_id, infra_id, link in nffg.real_out_edges_iter(nf.id):
          # Get Link's src ref to new NF's port
          nf_port = deployed_nf.ports.append(nf.ports[link.src.id].copy())

          def get_sw_port (vnf):
            """
            Return the switch port parsed from result of getVNFInfo

            :param vnf: VNF description returned by NETCONF server
            :type vnf: dict
            :return: port id
            :rtype: int
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
            self.log.warning("Can't get Container port from RPC result! Set "
                             "generated port number...")
          # Create INFRA side Port
          infra_port = mn_topo.network.node[infra_id].add_port(
            id=infra_port_num)
          self.log.debug("%s - detected physical %s" %
                         (deployed_nf, infra_port))
          # Add Links to mn topo
          mn_topo.add_undirected_link(port1=nf_port, port2=infra_port,
                                      dynamic=True, delay=link.delay,
                                      bandwidth=link.bandwidth)
          # Port mapping
          dynamic_port = nffg.network.node[infra_id].ports[link.dst.id].id
          self.portmap[dynamic_port] = infra_port_num
          # Update port in nffg_part
          nffg.network.node[infra_id].ports[
            link.dst.id].id = infra_port_num

        self.log.debug("%s topology description is updated with NF: %s" % (
          self.domain_name, deployed_nf.name))

    self.log.debug("Rewrite dynamically generated port numbers in flowrules...")
    # Update port numbers in flowrules
    for infra in nffg.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
         NFFG.TYPE_INFRA_SDN_SW):
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in mn_topo.infras):
        continue
      for port in infra.ports:
        for flowrule in port.flowrules:
          _match = flowrule.match.split(';')
          if not _match[0].startswith("in_port="):
            self.log.warning("Missing 'in_port' from match field: %s" %
                             flowrule.match)
            continue
          _action = flowrule.action.split(';')
          if not _action[0].startswith("output="):
            self.log.warning("Missing 'output' from action field: %s" %
                             flowrule.action)
            continue
          for dyn, phy in self.portmap.iteritems():
            _match[0] = _match[0].replace(str(dyn), str(phy))
            _action[0] = _action[0].replace(str(dyn), str(phy))
          flowrule.match = ";".join(_match)
          flowrule.action = ";".join(_action)
    if result:
      self.log.info("Initiation of NFs in NFFG part: %s has been finished! "
                    "Result: SUCCESS" % nffg)
    else:
      self.log.info("Initiation of NFs in NFFG part: %s has been finished! "
                    "Result: FAILURE" % nffg)
    return result

  def _delete_flowrules (self, nffg=None):
    """
    Delete all flowrules from the first (default) table of all infras.

    :param nffg: last mapped NFFG part
    :type nffg: :class:`NFFG`
    :return: deletion was successful or not
    :rtype: bool
    """
    self.log.debug("Reset domain steering and delete installed flowrules...")
    result = True
    # Get topology NFFG to detect corresponding infras and skip needless infras
    topo = self.topoAdapter.get_topology_resource()
    if topo is None:
      self.log.warning("Missing topology description from %s domain! "
                       "Skip flowrule deletions..." % self.domain_name)
      return False
    # If nffg is not given or is a bare topology, which is probably a cleanup
    # topo, all the flowrules in physical topology will be removed
    if nffg is None or nffg.is_bare():
      self.log.debug("Detected empty request NFFG! "
                     "Remove all the installed flowrules...")
      nffg = topo
    topo_infras = [n.id for n in topo.infras]
    # Iter through the container INFRAs in the given mapped NFFG part
    self.log.debug("Managed topo infras: %s" % topo_infras)
    for infra in nffg.infras:
      self.log.debug("Process flowrules in infra: %s" % infra.id)
      if infra.infra_type not in (NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
                                  NFFG.TYPE_INFRA_SDN_SW):
        self.log.warning("Detected virtual Infrastructure Node type: %s! "
                         "Skip infra node processing..." % infra.infra_type)
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in topo_infras:
        self.log.error("Infrastructure Node: %s is not found in the %s domain! "
                       "Skip flowrule deletion on this Node..." %
                       (infra.id, self.domain_name))
        result = False
        continue
      try:
        dpid = self.controlAdapter.infra_to_dpid[infra.id]
      except KeyError as e:
        self.log.warning("Missing DPID for Infra(id: %s)! Skip deletion of "
                         "flowrules" % e)
        result = False
        continue
      # Check the OF connection is alive
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        self.log.warning("Skipping DELETE flowrules! Cause: connection for %s -"
                         " DPID: %s is not found!" % (infra, dpid_to_str(dpid)))
        result = False
        continue
      self.controlAdapter.delete_flowrules(infra.id)
    self.log.debug("Flowrule deletion result: %s" %
                   ("SUCCESS" if result else "FAILURE"))
    return result

  def _deploy_flowrules (self, nffg_part):
    """
    Install the flowrules given in the NFFG.

    If a flowrule is already defined it will be updated.

    :param nffg_part: NF-FG part need to be deployed
    :type nffg_part: :class:`NFFG`
    :return: deploy was successful or not
    :rtype: bool
    """
    self.log.debug("Deploy flowrules into the domain: %s..." % self.domain_name)
    result = True
    # Remove unnecessary SG and Requirement links to avoid mess up port
    # definition of NFs
    nffg_part.clear_links(NFFG.TYPE_LINK_SG)
    nffg_part.clear_links(NFFG.TYPE_LINK_REQUIREMENT)

    # # Get physical topology description from POX adapter
    # topo = self.controlAdapter.get_topology_resource()
    topo = self.topoAdapter.get_topology_resource()
    if topo is None:
      self.log.warning("Missing topology description from %s domain! "
                       "Skip deploying flowrules..." % self.domain_name)
      return False
    # Iter through the container INFRAs in the given mapped NFFG part
    for infra in nffg_part.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
         NFFG.TYPE_INFRA_SDN_SW):
        self.log.debug("Infrastructure Node: %s (type: %s) is not Switch or "
                       "Container type! Continue to next Node..." %
                       (infra.id, infra.infra_type))
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in topo.infras):
        self.log.error("Infrastructure Node: %s is not found in the %s domain! "
                       "Skip flowrule install on this Node..." % (
                         infra.id, self.domain_name))
        result = False
        continue
      try:
        dpid = self.controlAdapter.infra_to_dpid[infra.id]
      except KeyError as e:
        self.log.warning("Missing DPID for Infra(id: %s)! "
                         "Skip deploying flowrules for Infra" % e)
        result = False
        continue
      # Check the OF connection is alive
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        self.log.warning("Skipping INSTALL flowrule! "
                         "Cause: connection for %s - DPID: %s is not found!" %
                         (infra, dpid_to_str(dpid)))
        result = False
        continue
      for port in infra.ports:
        for flowrule in port.flowrules:
          try:
            match = NFFGConverter.field_splitter(
              type=NFFGConverter.TYPE_MATCH,
              field=flowrule.match)
            if "in_port" not in match:
              self.log.warning("Missing in_port field from match field! "
                               "Using container port number...")
              match["in_port"] = port.id
            action = NFFGConverter.field_splitter(
              type=NFFGConverter.TYPE_ACTION,
              field=flowrule.action)
          except RuntimeError as e:
            self.log.warning("Wrong format in match/action field: %s" % e)
            result = False
            continue
          # Process the abstract TAG in match
          if 'vlan_id' in match:
            self.log.debug("Process TAG: %s in match field" % match['vlan_id'])
            vlan = self.__process_tag(abstract_id=match['vlan_id'])
            if vlan is not None:
              match['vlan_id'] = vlan
            else:
              self.log.error("Abort Flowrule deployment...")
              return
          # Process the abstract TAG in action
          if 'vlan_push' in action:
            self.log.debug("Process TAG: %s in action field" %
                           action['vlan_push'])
            vlan = self.__process_tag(abstract_id=action['vlan_push'])
            if vlan is not None:
              action['vlan_push'] = vlan
            else:
              self.log.error("Abort Flowrule deployment...")
              return
          self.log.debug("Assemble OpenFlow flowrule from: %s" % flowrule)
          self.controlAdapter.install_flowrule(infra.id, match, action)
    self.log.info("Flowrule deploy result: %s" %
                  ("SUCCESS" if result else "FAILURE"))
    self.log.log(VERBOSE,
                 "Registered VLAN IDs: %s" % pprint.pformat(self.vlan_register))
    return result

  def __process_tag (self, abstract_id):
    """
    Generate a valid VLAN id from the raw_id data which derived from directly
    an SG hop link id.

    :param abstract_id: raw link id
    :type abstract_id: str or int
    :return: valid VLAN id
    :rtype: int
    """
    # Check if the abstract tag has already processed
    if abstract_id in self.vlan_register:
      self.log.debug("Found already register TAG ID: %s ==> %s" % (
        abstract_id, self.vlan_register[abstract_id]))
      return self.vlan_register[abstract_id]
    # Check if the raw_id is a valid number
    try:
      vlan_id = int(abstract_id)
      # Check if the raw_id is free
      if 0 < vlan_id < 4095 and vlan_id not in self.vlan_register.itervalues():
        self.vlan_register[abstract_id] = vlan_id
        self.log.debug("Abstract ID is a valid not-taken VLAN ID! "
                       "Register %s ==> %s" % (abstract_id, vlan_id))
        return vlan_id
    except ValueError:
      # Cant be converted to int, continue with raw_id processing
      pass
    trailer_num = re.search(r'\d+$', abstract_id)
    # If the raw_id ends with number
    if trailer_num is not None:
      # Check if the trailing number is a valid VLAN id (0 and 4095 are
      # reserved)
      trailer_num = int(trailer_num.group())  # Get matched data from Match obj
      # Check if the VLAN candidate is free
      if 0 < trailer_num < 4095 and \
            trailer_num not in self.vlan_register.itervalues():
        self.vlan_register[abstract_id] = trailer_num
        self.log.debug("Trailing number is a valid non-taken VLAN ID! "
                       "Register %s ==> %s..." % (abstract_id, trailer_num))
        return trailer_num
        # else Try to find a free VLAN
      else:
        self.log.debug("Detected trailing number: %s is not a valid VLAN "
                       "or already taken!" % trailer_num)
    # No valid VLAN number has found from abstract_id, try to find a free VLAN
    for vlan in xrange(1, 4094):
      if vlan not in self.vlan_register.itervalues():
        self.vlan_register[abstract_id] = vlan
        self.log.debug("Generated and registered VLAN id %s ==> %s" %
                       (abstract_id, vlan))
        return vlan
    # For loop is exhausted
    else:
      log.error("No available VLAN id found!")
      return None
