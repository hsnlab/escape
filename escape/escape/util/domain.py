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
import time
import urlparse

from requests import Session, ConnectionError, HTTPError, Timeout, \
  RequestException

import pox.openflow.libopenflow_01 as of
from escape import __version__
from escape.adapt import log
from escape.nffg_lib.nffg import NFFG
from escape.util.config import ConfigurationError
from escape.util.misc import enum, VERBOSE
from escape.util.pox_extension import OpenFlowBridge, \
  ExtendedOFConnectionArbiter
from pox.lib.addresses import EthAddr, IPAddr
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
  TYPE = enum('DOMAIN_UP',  # new domain has detected
              "DOMAIN_CHANGED",  # detected domain has changed
              'DOMAIN_DOWN',  # detected domain got down
              'NODE_UP',  # one Node/BiSBiS gone up
              'NODE_DOWN',  # one Node/BiSBiS got down
              'CONNECTION_UP',  # connection gone up
              'CONNECTION_DOWN')  # connection got down

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
  # DomainManager name- used more or less the type of the manager
  name = "UNDEFINED"
  # Default domain name
  DEFAULT_DOMAIN_NAME = "UNDEFINED"
  # Signal that the Manager class is for the Local Mininet-based topology
  IS_LOCAL_MANAGER = False

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, adapters=None, **kwargs):
    """
    Init.
    """
    super(AbstractDomainManager, self).__init__()
    # Name of the domain
    self.domain_name = domain_name
    self._detected = None  # Actual domain is detected or not
    self.internal_topo = None  # Description of the domain topology as an NFFG
    self.topoAdapter = None  # Special adapter which can handle the topology
    # description, request it, and install mapped NFs from internal NFFG
    self._adapters_cfg = adapters

  def __str__ (self):
    return "DomainManager(name: %s, domain: %s)" % (self.name, self.domain_name)

  @property
  def detected (self):
    """
    Return True if the Manager has detected the domain.

    :return: domain status
    :rtype: bool
    """
    return self._detected

  ##############################################################################
  # Abstract functions for component control
  ##############################################################################

  def _load_adapters (self, configurator, **kwargs):
    """
    Initiate Adapters using given configurator and predefined config.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :param kwargs: optional parameters
    :type kwargs: dict
    :return: None
    """
    log.info("Init DomainManager for %s domain!" % self.domain_name)
    if not self._adapters_cfg:
      log.fatal("Missing Adapter configurations from DomainManager: %s" %
                self.domain_name)
      raise ConfigurationError("Missing configuration for %s" %
                               self.domain_name)
    log.debug("Init Adapters for domain: %s - adapters: %s" % (
      self.domain_name,
      [a['class'] for a in self._adapters_cfg.itervalues()]))
    # Update Adapters's config with domain name
    for adapter in self._adapters_cfg.itervalues():
      adapter['domain_name'] = self.domain_name
    # Initiate Adapters
    self.initiate_adapters(configurator)

  def initiate_adapters (self, configurator):
    """
    Initiate Adapters for DomainManager.

    Must override in inherited classes.

    Follows the Factory Method design pattern.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :return: None
    """
    raise NotImplementedError(
      "Managers must override this function to initiate Adapters!")

  def init (self, configurator, **kwargs):
    """
    Abstract function for component initialization.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :param kwargs: optional parameters
    :type kwargs: dict
    :return: None
    """
    # Load and initiate adapters using the initiate_adapters() template func
    self._load_adapters(configurator=configurator, **kwargs)
    # Try to request/parse/update Mininet topology
    if not self._detect_topology():
      log.warning("%s domain not confirmed during init!" % self.domain_name)
    else:
      # Notify all components for topology change --> this event causes
      # the DoV updating
      self.raiseEventNoErrors(DomainChangedEvent,
                              domain=self.domain_name,
                              data=self.internal_topo,
                              cause=DomainChangedEvent.TYPE.DOMAIN_UP)

  def run (self):
    """
    Abstract function for starting component.

    :return: None
    """
    log.info("Start DomainManager for %s domain!" % self.domain_name)

  def finit (self):
    """
    Abstract function for stopping component.
    """
    log.info("Stop DomainManager for %s domain!" % self.domain_name)

  def suspend (self):
    """
    Abstract class for suspending a running component.

    .. note::
      Not used currently!

    :return: None
    """
    log.info("Suspend DomainManager for %s domain!" % self.domain_name)

  def resume (self):
    """
    Abstract function for resuming a suspended component.

    .. note::
      Not used currently!

    :return: None
    """
    log.info("Resume DomainManager for %s domain!" % self.domain_name)

  def info (self):
    """
    Abstract function for requesting information about the component.

    .. note::
      Not used currently!

    :return: None
    """
    return self.__class__.__name__

  ##############################################################################
  # ESCAPE specific functions
  ##############################################################################

  def _detect_topology (self):
    """
    Check the undetected topology is up or not.

    If the domain is confirmed and detected, the ``internal_topo`` attribute
    will be updated with the new topology.

    .. warning::

      No :any:`DomainChangedEvent` will be raised internally if the domain is
      confirmed!

    :return: detected or not
    :rtype: bool
    """
    if self.topoAdapter.check_domain_reachable():
      log.info(">>> %s domain confirmed!" % self.domain_name)
      self._detected = True
      log.info("Requesting resource information from %s domain..." %
               self.domain_name)
      topo_nffg = self.topoAdapter.get_topology_resource()
      if topo_nffg:
        log.debug("Save detected topology: %s..." % topo_nffg)
        # Update the received new topo
        self.internal_topo = topo_nffg
      else:
        log.warning("Resource info is missing!")
    return self._detected

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the specific domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: status if the install process was success
    :rtype: bool
    """
    raise NotImplementedError("Not implemented yet!")

  def clear_domain (self):
    """
    Clear the Domain according to the first received config.
    """
    raise NotImplementedError("Not implemented yet!")


class AbstractRemoteDomainManager(AbstractDomainManager):
  """
  Abstract class for different remote domain managers.

  Implement polling mechanism for remote domains.
  """
  # Polling interval
  POLL_INTERVAL = 3
  # Request formats
  DEFAULT_DIFF_VALUE = False

  def __init__ (self, domain_name=None, adapters=None, **kwargs):
    """
    Init.
    """
    super(AbstractRemoteDomainManager, self).__init__(domain_name=domain_name,
                                                      adapters=adapters,
                                                      **kwargs)
    # Timer for polling function
    self.__timer = None
    if 'poll' in kwargs:
      self._poll = bool(kwargs['poll'])
    else:
      self._poll = False
    if 'diff' in kwargs:
      self._diff = bool(kwargs['diff'])
    else:
      self._diff = self.DEFAULT_DIFF_VALUE
    log.debug("Enforced configuration for %s: poll: %s, diff: %s" % (
      self.__class__.__name__, self._poll, self._diff))

  @property
  def detected (self):
    """
    Return True if the Manager has detected the domain.

    :return: domain status
    :rtype: bool
    """
    return self._detected

  ##############################################################################
  # Abstract functions for component control
  ##############################################################################

  def init (self, configurator, **kwargs):
    """
    Abstract function for component initialization.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :param kwargs: optional parameters
    :type kwargs: dict
    :return: None
    """
    # Load and initiate adapters using the initiate_adapters() template func
    self._load_adapters(configurator=configurator, **kwargs)
    # Skip to start polling if it's set
    if not self._poll:
      # Try to request/parse/update Mininet topology
      if not self._detect_topology():
        log.warning("%s domain not confirmed during init!" % self.domain_name)
      else:
        # Notify all components for topology change --> this event causes
        # the DoV updating
        self.raiseEventNoErrors(DomainChangedEvent,
                                domain=self.domain_name,
                                data=self.internal_topo,
                                cause=DomainChangedEvent.TYPE.DOMAIN_UP)
    else:
      log.info("Start polling %s domain..." % self.domain_name)
      self.start_polling(self.POLL_INTERVAL)

  def initiate_adapters (self, configurator):
    """
    Initiate Adapters for DomainManager.

    Must override in inherited classes.
    Follows the Factory Method design pattern.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :return: None
    """
    raise NotImplementedError(
      "Managers must override this function to initiate Adapters!")

  def finit (self):
    """
    Abstract function for starting component.
    """
    self.stop_polling()
    super(AbstractRemoteDomainManager, self).finit()

  ##############################################################################
  # Common functions for polling
  ##############################################################################

  def start_polling (self, interval=1):
    """
    Initialize and start a Timer co-op task for polling.

    :param interval: polling period (default: 1)
    :type interval: int
    """
    if self.__timer:
      # Already timing
      return
    self.__timer = Timer(interval, self.poll, recurring=True, started=True,
                         selfStoppable=True)

  def restart_polling (self, interval=POLL_INTERVAL):
    """
    Reinitialize and start a Timer co-op task for polling.

    :param interval: polling period (default: 3)
    :type interval: int
    """
    if self.__timer:
      self.__timer.cancel()
    self.__timer = Timer(interval, self.poll, recurring=True, started=True,
                         selfStoppable=True)

  def stop_polling (self):
    """
    Stop timer.
    """
    if self.__timer:
      self.__timer.cancel()
    self.__timer = None

  def poll (self):
    """
    Poll the defined domain agent. Handle different connection errors and go
    to slow/rapid poll. When an agent is (re)detected update the current
    resource information.

    :return: None
    """
    # If domain is not detected
    if not self._detected:
      # Check the topology is reachable
      if self._detect_topology():
        # Domain is detected and topology is updated -> restart domain polling
        self.restart_polling()
        # Notify all components for topology change --> this event causes
        # the DoV updating
        self.raiseEventNoErrors(DomainChangedEvent,
                                domain=self.domain_name,
                                data=self.internal_topo,
                                cause=DomainChangedEvent.TYPE.DOMAIN_UP)
        return
    # If domain has already detected
    else:
      # Check the domain is still reachable
      changed = self.topoAdapter.check_topology_changed()
      # No changes
      if changed is False:
        # Nothing to do
        log.log(VERBOSE,
                "Remote domain: %s has not changed!" % self.domain_name)
        return
      # Domain has changed
      elif isinstance(changed, NFFG):
        log.info("Remote domain: %s has changed. Update global domain view..." %
                 self.domain_name)
        log.debug("Save changed topology: %s" % changed)
        # Update the received new topo
        self.internal_topo = changed
        # Notify all components for topology change --> this event causes
        # the DoV updating
        self.raiseEventNoErrors(DomainChangedEvent,
                                domain=self.domain_name,
                                data=self.internal_topo,
                                cause=DomainChangedEvent.TYPE.DOMAIN_CHANGED)
        return
      # If changed is None something went wrong, probably remote domain is not
      # reachable. Step to the other half of the function
      elif changed is None:
        log.warning("Lost connection with %s agent! Going to slow poll..." %
                    self.domain_name)
        # Clear internal topology
        log.debug("Clear topology from domain: %s" % self.domain_name)
        self.internal_topo = None
        self.raiseEventNoErrors(DomainChangedEvent,
                                domain=self.domain_name,
                                cause=DomainChangedEvent.TYPE.DOMAIN_DOWN)
      else:
        log.warning(
          "Got unexpected return value from check_topology_changed(): %s" %
          type(changed))
        return
    # If this is the first call of poll()
    if self._detected is None:
      log.warning("Local agent in domain: %s is not detected! Keep trying..." %
                  self.domain_name)
      self._detected = False
    elif self._detected:
      # Detected before -> lost connection = big Problem
      self._detected = False
      self.restart_polling()
    else:
      # No success but not for the first try -> keep trying silently
      pass

  ##############################################################################
  # ESCAPE specific functions
  ##############################################################################

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the specific domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: status if the install process was success
    :rtype: bool
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

  Polling mechanism of separate domains has moved to Manager classes.
  """
  # Adapter name used in POX's core or CONFIG, etc.
  name = None
  # Adapter type used in CONFIG under the specific DomainManager
  # Defines the general Adapter name in the CONFIG
  type = None
  # Pre-defined constants for type field
  TYPE_CONTROLLER = "CONTROLLER"
  TYPE_TOPOLOGY = "TOPOLOGY"
  TYPE_MANAGEMENT = "MANAGEMENT"
  TYPE_REMOTE = "REMOTE"

  def __init__ (self, domain_name='UNDEFINED', **kwargs):
    """
    Init.
    """
    super(AbstractESCAPEAdapter, self).__init__()
    self.domain_name = domain_name
    # Observed topology has been changed since the last query
    self.__dirty = False

  def rewrite_domain (self, nffg):
    """
    Rewrite the DOMAIN information in nodes of the given :any:`NFFG`.

    :param nffg: topology description
    :type nffg: :any:`NFFG`
    :return: the rewritten description
    :rtype: :any:`NFFG`
    """
    log.debug(
      "Rewrite domain of Infrastructure nodes to: %s" % self.domain_name)
    if self.domain_name == "UNDEFINED":
      log.warning(
        "Domain name is not set for Adapter(name: %s)! Skip domain rewrite "
        "for %s..." % (self.name, nffg))
    for infra in nffg.infras:
      infra.domain = self.domain_name
    return nffg

  def check_domain_reachable (self):
    """
    Checker function for domain polling. Check the remote domain agent is
    reachable.

    :return: the remote domain is detected or not
    :rtype: bool
    """
    raise NotImplementedError("Not implemented yet!")

  def get_topology_resource (self):
    """
    Return with the topology description as an :any:`NFFG`.

    :return: the topology description
    :rtype: :any:`NFFG`
    """
    raise NotImplementedError("Not implemented yet!")

  def check_topology_changed (self):
    """
    Return if the remote domain is changed.

    :return: the received topology is different from cached one
    :rtype: bool or None
    """
    # Implement a very simple change detection based on dirty flag
    tmp = self.__dirty
    self.__dirty = False
    return tmp

  def finit (self):
    """
    Finish the remained connections and release the reserved resources.

    Called by the DomainManager.

    :return: None
    """
    log.debug("Finit ESCAPEAdapter name: %s, type: %s" % (self.name, self.type))


class AbstractOFControllerAdapter(AbstractESCAPEAdapter):
  """
  Abstract class for different domain adapters which need SDN/OF controller
  capability.
  """
  # Events raised by this class
  _eventMixin_events = {DomainChangedEvent}
  # Keepalive constants
  _interval = 20
  _switch_timeout = 5
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
    #   'dl_src': 'ff:ff:ff:ff:ff:ff'  # '00:00:00:00:00:02'
    # },
    # 'SW4': {
    #   'port': '3',
    #   'dl_dst': '00:00:00:00:00:02',
    #   'dl_src': 'ff:ff:ff:ff:ff:ff'  # '00:00:00:00:00:02'
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
    name = name if name is not None else self.name
    super(AbstractOFControllerAdapter, self).__init__(*args, **kwargs)
    # Set an OpenFlow nexus as a source of OpenFlow events
    self.openflow = OpenFlowBridge()
    self.controller_address = (address, port)
    # Initiate our specific connection Arbiter
    arbiter = ExtendedOFConnectionArbiter.activate()
    # Register our OpenFlow event source
    arbiter.add_connection_listener(self.controller_address, self.openflow)
    # Launch OpenFlow connection handler if not started before with given name
    # launch() return the registered openflow module which is a coop Task
    log.debug("Setup OF interface and initiate handler object for connection: "
              "(%s, %i)" % (address, port))
    from pox.openflow.of_01 import launch
    of = launch(name=name, address=address, port=port)
    # Start listening for OpenFlow connections
    of.start()
    self.task_name = name if name else "of_01"
    of.name = self.task_name
    # register OpenFlow event listeners
    self.openflow.addListeners(self)
    log.debug(
      "%s adapter: Start listening incoming OF connections..." % self.name)
    # initiate keepalive if needed
    if keepalive:
      log.debug(
        "Initiate keepalive functionality - Echo Request interval: %ss, "
        "timeout: %ss" % (self._interval, self._switch_timeout))
      Timer(self._interval, self._handle_keepalive_handler, recurring=True,
            args=(self.openflow,))

  @classmethod
  def _handle_keepalive_handler (cls, ofnexus):
    # Construct OF Echo Request packet
    er = of.ofp_echo_request().pack()
    t = time.time()
    dead = []
    for dpid, conn in ofnexus.connections.iteritems():
      if t - conn.idle_time > (cls._interval + cls._switch_timeout):
        dead.append(conn)
        continue
      conn.send(er)
    for conn in dead:
      conn.disconnect(
        "Connection: %s has reached timeout: %s!" % (conn, cls._switch_timeout))

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

  def get_topology_resource (self):
    raise NotImplementedError("Not implemented yet!")

  def check_domain_reachable (self):
    raise NotImplementedError("Not implemented yet!")

  def delete_flowrules (self, id):
    """
    Delete all flowrules from the first (default) table of an OpenFlow switch.

    :param id: ID of the infra element stored in the NFFG
    :type id: str
    :return: None
    """
    conn = self.openflow.getConnection(dpid=self.infra_to_dpid[id])
    if not conn:
      log.warning("Missing connection for node element: %s! "
                  "Skip deletion of flowrules..." % id)
      return
    log.debug("Delete flow entries from INFRA %s on connection: %s ..." %
              (id, conn))
    msg = of.ofp_flow_mod(command=of.OFPFC_DELETE)
    conn.send(msg)

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
    conn = self.openflow.getConnection(dpid=self.infra_to_dpid[id])
    if not conn:
      log.warning("Missing connection for node element: %s! Skip flowrule "
                  "installation..." % id)
    msg = of.ofp_flow_mod()
    msg.match.in_port = match['in_port']
    if 'vlan_id' in match:
      try:
        vlan_id = int(match['vlan_id'])
      except ValueError:
        log.warning("VLAN_ID: %s in match field is not a valid number! "
                    "Skip flowrule installation..." % match['vlan_id'])
        return
      msg.match.dl_vlan = vlan_id
    # Append explicit matching parameters to OF flowrule
    if 'flowclass' in match:
      for ovs_match_entry in match['flowclass'].split(','):
        kv = ovs_match_entry.split('=')
        # kv = [field, value] ~ ['dl_src', '00:0A:E4:25:6B:B6']
        # msg.match.dl_src = "00:00:00:00:00:01"
        if kv[0] in ('dl_src', 'dl_dst'):
          setattr(msg.match, kv[0], EthAddr(kv[1]))
        elif kv[0] in ('in_port', 'dl_vlan', 'dl_type', 'ip_proto', 'nw_proto',
                       'nw_tos', 'nw_ttl', 'tp_src', 'tp_dst'):
          msg.match.dl_type = int(kv[1])
        elif kv[0] in ('nw_src', 'nw_dst'):
          setattr(msg.match, kv[0], IPAddr(kv[1]))
        else:
          setattr(msg.match, kv[0], kv[1])

    if 'vlan_push' in action:
      try:
        vlan_push = int(action['vlan_push'])
      except ValueError:
        log.warning("VLAN_ID: %s in action field is not a valid number! "
                    "Skip flowrule installation..." % match['vlan_id'])
        return
      msg.actions.append(of.ofp_action_vlan_vid(vlan_vid=vlan_push))
      # msg.actions.append(of.ofp_action_vlan_vid())
    out = action['out']
    # If out is in the detected saps --> always remove the VLAN tags
    if 'vlan_pop' in action:
      msg.actions.append(of.ofp_action_strip_vlan())
    else:
      try:
        # If next node is a SAP we need to setup the MAC addresses and
        # strip VLAN from the frame explicitly
        if out in self.saps[id]:
          msg.actions.append(of.ofp_action_strip_vlan())
      except KeyError:
        pass
    try:
      if out in self.saps[id]:
        dl_dst = self.saps[id][str(out)]['dl_dst']
        dl_src = self.saps[id][str(out)]['dl_src']
        msg.actions.append(of.ofp_action_dl_addr.set_dst(EthAddr(dl_dst)))
        msg.actions.append(of.ofp_action_dl_addr.set_src(EthAddr(dl_src)))
    except KeyError:
      pass
    try:
      out_port = int(action['out'])
    except ValueError:
      log.warning("Output port: %s is not a valid port in flowrule action: %s! "
                  "Skip flowrule installation..." % (action['out'], action))
      return
    msg.actions.append(of.ofp_action_output(port=out_port))
    log.debug(
      "Install flow entry into INFRA: %s on connection: %s ..." % (id, conn))
    conn.send(msg)
    log.log(VERBOSE, "Sent OpenFlow flowrule:\n%s" % msg)


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


class DefaultUnifyDomainAPI(object):
  """
  Define unified interface for managing UNIFY domains with REST-API.

  Follows the MixIn design pattern approach to support OpenStack functionality.
  """

  def ping (self):
    """
    Call the ping RPC.

    :return: response text (should be: 'OK')
    :rtype: str
    """
    raise NotImplementedError("Not implemented yet!")

  def get_config (self, filter=None):
    """
    Queries the infrastructure view with a netconf-like "get-config" command.

    Remote domains always send full-config if ``filter`` is not set.

    Return topology description in the original format.

    :param filter: request a filtered description instead of full
    :type filter: str
    :return: infrastructure view in the original format
    """
    raise NotImplementedError("Not implemented yet!")

  def edit_config (self, data, diff=False):
    """
    Send the requested configuration with a netconf-like "edit-config" command.

    :param data: whole domain view
    :type data: :any::`NFFG`
    :param diff: send the diff of the mapping request (default: False)
    :param diff: bool
    :return: status code
    :rtype: str
    """
    raise NotImplementedError("Not implemented yet!")


class OpenStackAPI(DefaultUnifyDomainAPI):
  """
  Define interface for managing OpenStack domain.

  .. note::
    Fitted to the API of ETH REST-like server which rely on virtualizer3!

  Follows the MixIn design pattern approach to support OpenStack functionality.
  """


class UniversalNodeAPI(DefaultUnifyDomainAPI):
  """
  Define interface for managing Universal Node domain.

  .. note::
    Fitted to the API of ETH REST-like server which rely on virtualizer3!

  Follows the MixIn design pattern approach to support UN functionality.
  """


class RemoteESCAPEv2API(DefaultUnifyDomainAPI):
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
  custom_headers = {
    'User-Agent': "ESCAPE/" + __version__,
  }
  # Connection timeout (sec)
  CONNECTION_TIMEOUT = 5
  # HTTP methods
  GET = "GET"
  POST = "POST"

  def __init__ (self, base_url, prefix="", auth=None, **kwargs):
    super(AbstractRESTAdapter, self).__init__()
    if base_url.endswith('/'):
      self._base_url = urlparse.urljoin(base_url, prefix + "/")
    else:
      self._base_url = urlparse.urljoin(base_url + '/', prefix + "/")
    self.auth = auth
    # Store the last request
    self._response = None
    if 'timeout' in kwargs:
      self.CONNECTION_TIMEOUT = kwargs['timeout']
      log.debug("Setup explicit timeout for REST responses: %ss" %
                self.CONNECTION_TIMEOUT)
    # Suppress low level logging
    self.__suppress_requests_logging()

  @property
  def URL (self):
    return self._base_url

  @staticmethod
  def __suppress_requests_logging (level=None):
    """
    Suppress annoying and detailed logging of `requests` and `urllib3` packages.

    :param level: level of logging (default: WARNING)
    :type level: str
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
      elif isinstance(body, basestring) and body.startswith("<?xml version="):
        kwargs['headers']['Content-Type'] = "application/xml"
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

  def send_no_error (self, method, url=None, body=None, **kwargs):
    """
    Send REST request with handling exceptions.

    :param method: HTTP method
    :type method: str
    :param url: valid URL or relevant part follows ``self.base_url``
    :type url: str
    :param body: request body
    :type body: :any:`NFFG` or dict or bytes or str
    :return: raw response data
    :rtype: str
    """
    try:
      return self.send_with_timeout(method, url, body, **kwargs)
    except Timeout:
      log.warning("Remote agent(adapter: %s, url: %s) reached timeout limit!"
                  % (self.name, self._base_url))
      return None

  def send_with_timeout (self, method, url=None, body=None, timeout=None,
                         **kwargs):
    """
    Send REST request with handling exceptions except the TimeoutError.

    :param method: HTTP method
    :type method: str
    :param url: valid URL or relevant part follows ``self.base_url``
    :type url: str
    :param body: request body
    :type body: :any:`NFFG` or dict or bytes or str
    :param timeout: optional timeout param can be given also here
    :type timeout: int
    :raises: :any:`requests.Timeout`
    :return: raw response data
    :rtype: str
    """
    try:
      if timeout is not None:
        kwargs['timeout'] = timeout
      self.send_request(method, url, body, **kwargs)
      # return self._response.status_code if self._response is not None else
      # None
      return self._response.text if self._response is not None else None
    except ConnectionError:
      log.error("Remote agent(adapter: %s, url: %s) is not reachable!"
                % (self.name, self._base_url))
      return None
    except HTTPError as e:
      log.error("Remote agent(adapter: %s, url: %s) responded with an error: %s"
                % (self.name, self._base_url, e.message))
      return None
    except Timeout:
      raise
    except RequestException as e:
      log.error("Got unexpected exception: %s" % e)
      return None
    except KeyboardInterrupt:
      log.warning("Request to remote agent(adapter: %s, url: %s) is "
                  "interrupted by user!" % (self.name, self._base_url))
      return None

  def is_content_type (self, ctype):
    """
    Return True is the content type of the last request contains the given
    type.

    :param ctype: content type
    :type ctype: str
    :return: the content type contains the given type or not
    :rtype: bool
    """
    content_type = self._response.headers.get('Content-Type', "")
    if not content_type:
      return False
    else:
      return ctype in content_type

  def get_last_response_body (self):
    """
    Return with the body of the last response.
    Wrapper function to hide requests library.

    :return: raw response body
    :rtype: str
    """
    return self._response.text if self._response is not None else None

  def get_last_response_status (self):
    """
    Return the status of the last response.

    :return: response status
    :rtype: int
    """
    return self._response.status_code if self._response is not None else None

  def get_last_response_headers (self):
    """
    Return with the headers of the last response.

    :return: response headers
    :rtype: dict
    """
    return self._response.headers if self._response is not None else {}
