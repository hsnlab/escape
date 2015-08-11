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
Wrapper module for handling emulated test topology based on Mininet.
"""

from mininet.clean import cleanup
from mininet.net import VERSION as MNVERSION, Mininet, MininetWithControlNet
from mininet.node import RemoteController, RemoteSwitch
from mininet.topo import Topo
from escape import CONFIG
from escape.infr import log, LAYER_NAME
from escape.util.nffg import NFFG
from escape.util.nffg_elements import NodeInfra
from escape.util.misc import quit_with_error, run_silent, call_as_coop_task, \
  run_cmd


class AbstractTopology(Topo):
  """
  Abstract class for representing emulated topology.

  Have the functions to build a ESCAPE-specific topology.

  Can be used to define reusable topology similar to Mininet's high-level API.
  Reusable, convenient and pre-defined way to define a topology, but less
  flexible and powerful.
  """
  # Default host options
  default_host_opts = None
  # Default switch options
  default_switch_opts = None
  # Default link options
  default_link_opts = None
  # Default EE options
  default_EE_opts = None
  # Type of the Topology class - NEED to be set
  # The construction and build of the network is different for the STATIC and
  # DYNAMIC way
  TYPE = None

  def __init__ (self, hopts=None, sopts=None, lopts=None, eopts=None):
    super(AbstractTopology, self).__init__(hopts, sopts, lopts, eopts)

  def construct (self, builder=None):
    """
    Base class for construct the topology.
    """
    raise NotImplementedError("Not implemented yet!")

  @staticmethod
  def get_topo_desc ():
    """
    Return the NFFG object represents the specific, constructed topology
    """
    raise NotImplementedError("Not implemented yet!")


class FallbackStaticTopology(AbstractTopology):
  """
  Topology class for testing purposes and serve as a fallback topology.

  Use the static way for topology compilation.

  .. raw:: ascii

    +----------+           +----------+
    |          |           |          |
    |    SW1   |           |    SW2   |
    |          |           |          |
    +----------+           +----------+
          |1                     |1
         1|                     1|
    +----------+           +----------+
    |          |2         2|          |
    |    SW3   +-----------+    SW4   |
    |          |           |          |
    +----------+           +----------+
          |3                    |3
         1|                    1|
        +----+               +----+
        |SAP1|               |SAP2|
        +----+               +----+
  """
  TYPE = "STATIC"

  def construct (self, builder=None):
    # nc1 = self.addEE(name='NC1', {})
    # nc2 = self.addEE(name='NC2', {})
    log.info("Start static topology creation...")
    log.debug("Create Switch with name: SW1")
    sw1 = self.addSwitch('SW1')
    log.debug("Create Switch with name: SW2")
    sw2 = self.addSwitch('SW2')
    log.debug("Create Switch with name: SW3")
    sw3 = self.addSwitch('SW3')
    log.debug("Create Switch with name: SW4")
    sw4 = self.addSwitch('SW4')
    log.debug("Create SAP with name: SAP1")
    sap1 = self.addHost('SAP1')
    log.debug("Create SAP with name: SAP2")
    sap2 = self.addHost('SAP2')
    log.debug("Create Link SW3 <--> SW1")
    self.addLink(sw3, sw1)
    log.debug("Create Link SW4 <--> SW2")
    self.addLink(sw4, sw2)
    log.debug("Create Link SW3 <--> SW4")
    self.addLink(sw3, sw4)
    log.debug("Create Link SAP1 <--> SW3")
    self.addLink(sap1, sw3)
    log.debug("Create Link SAP2 <--> SW4")
    self.addLink(sap2, sw4)
    log.info("Static topology creation has been finished!")
    return self

  @staticmethod
  def get_topo_desc ():
    # Create NFFG
    nffg = NFFG(id="STATIC-FALLBACK-TOPO", name="fallback-static")
    # Add switches
    sw1 = nffg.add_infra(id="sw1", name="SW1", domain=NFFG.DOMAIN_INTERNAL,
                         infra_type=NFFG.TYPE_INFRA_SDN_SW)
    sw2 = nffg.add_infra(id="sw2", name="SW2", domain=NFFG.DOMAIN_INTERNAL,
                         infra_type=NFFG.TYPE_INFRA_SDN_SW)
    sw3 = nffg.add_infra(id="sw3", name="SW3", domain=NFFG.DOMAIN_INTERNAL,
                         infra_type=NFFG.TYPE_INFRA_SDN_SW)
    sw4 = nffg.add_infra(id="sw4", name="SW4", domain=NFFG.DOMAIN_INTERNAL,
                         infra_type=NFFG.TYPE_INFRA_SDN_SW)
    # Add SAPs
    sap1 = nffg.add_sap(id="sap1", name="SAP1")
    sap2 = nffg.add_sap(id="sap2", name="SAP2")
    # Add links
    nffg.add_link(sw1.add_port(1), sw3.add_port(1), id="l1")
    nffg.add_link(sw2.add_port(1), sw4.add_port(1), id="l2")
    nffg.add_link(sw3.add_port(2), sw4.add_port(2), id="l3")
    nffg.add_link(sw3.add_port(3), sap1.add_port(1), id="l4")
    nffg.add_link(sw4.add_port(3), sap2.add_port(1), id="l5")
    # Duplicate one-way static links to become undirected in order to fit to
    # the orchestration algorithm
    nffg.duplicate_static_links()
    return nffg


class FallbackDynamicTopology(AbstractTopology):
  """
  Topology class for testing purposes and serve as a fallback topology.

  Use the dynamic way for topology compilation.

  .. raw:: ascii

    +----------+           +----------+
    |          |           |          |
    |    EE1   |           |    EE2   |
    |          |           |          |
    +----------+           +----------+
          |1                     |1
         1|                     1|
    +----------+           +----------+
    |          |2         2|          |
    |    S3    +-----------+    S4    |
    |          |           |          |
    +----------+           +----------+
          |3                    |3
         1|                    1|
        +----+               +----+
        |SAP1|               |SAP2|
        +----+               +----+
  """
  TYPE = "DYNAMIC"

  def construct (self, builder=None):
    """
    Set a topology with NETCONF capability for mostly testing.

    :return: None
    """
    log.info("Start dynamic topology creation...")
    builder.create_Controller("ESCAPE")
    agt1, nc_sw1 = builder.create_NETCONF_EE(name='NC1')
    agt2, nc_sw2 = builder.create_NETCONF_EE(name='NC2')
    sw3 = builder.create_Switch(name='SW3')
    sw4 = builder.create_Switch(name='SW4')
    sap1 = builder.create_SAP(name='SAP1')
    sap2 = builder.create_SAP(name='SAP2')
    builder.create_Link(sw3, nc_sw1)
    builder.create_Link(sw4, nc_sw2)
    builder.create_Link(sw3, sw4)
    builder.create_Link(sap1, sw3)
    builder.create_Link(sap2, sw4)
    log.info("Dynamic topology creation has been finished!")

  @staticmethod
  def get_topo_desc ():
    # Create NFFG
    nffg = NFFG(id="DYNAMIC-FALLBACK-TOPO", name="fallback-dynamic")
    # Add NETCONF capable containers a.k.a. Execution Environments
    nc1 = nffg.add_infra(id="nc1", name="NC1", domain=NFFG.DOMAIN_INTERNAL,
                         infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                         delay=0.9, bandwidth=5000)
    nc2 = nffg.add_infra(id="nc2", name="NC2", domain=NFFG.DOMAIN_INTERNAL,
                         infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                         delay=0.9, bandwidth=5000)
    nc1.add_supported_type(['A', 'B'])
    nc2.add_supported_type(['A', 'C'])
    # Add inter-EE switches
    sw3 = nffg.add_infra(id="sw3", name="SW3", domain=NFFG.DOMAIN_INTERNAL,
                         infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.2,
                         bandwidth=10000)
    sw4 = nffg.add_infra(id="sw4", name="SW4", domain=NFFG.DOMAIN_INTERNAL,
                         infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.2,
                         bandwidth=10000)
    # Add SAPs
    sap1 = nffg.add_sap(id="sap1", name="SAP1")
    sap2 = nffg.add_sap(id="sap2", name="SAP2")
    # Add links
    linkres = {'delay': 1.5, 'bandwidth': 2000}
    nffg.add_link(nc1.add_port(1), sw3.add_port(1), id="l1", **linkres)
    nffg.add_link(nc2.add_port(1), sw4.add_port(1), id="l2", **linkres)
    nffg.add_link(sw3.add_port(2), sw4.add_port(2), id="l3", **linkres)
    nffg.add_link(sw3.add_port(3), sap1.add_port(1), id="l4", **linkres)
    nffg.add_link(sw4.add_port(3), sap2.add_port(1), id="l5", **linkres)
    # Duplicate one-way static links to become undirected in order to fit to
    # the orchestration algorithm
    nffg.duplicate_static_links()
    return nffg


class InternalControllerProxy(RemoteController):
  """
  Controller class for emulated Mininet network. Making connection with
  internal controller initiated by InternalPOXAdapter.
  """

  def __init__ (self, name="InternalPOXController", ip='127.0.0.1', port=6653,
       **kwargs):
    """
    Init.

    :param name: name of the controller (default: InternalPOXController)
    :type name: str
    :param ip: IP address (default: 127.0.0.1)
    :type ip: str
    :param port: port number (default 6633)
    :type port: int
    """
    super(InternalControllerProxy, self).__init__(name, ip, port, **kwargs)

  def checkListening (self):
    """
    Check the controller port is open.
    """
    listening = self.cmd("echo A | telnet -e A %s %d" % (self.ip, self.port))
    if 'Connected' not in listening:
      log.debug(
        "Unable to contact with internal controller at %s:%d. Waiting..." % (
          self.ip, self.port))


class ESCAPENetworkBridge(object):
  """
  Internal class for representing the emulated topology.

  Represents a container class for network elements such as switches, nodes,
  execution environments, links etc. Contains network management functions
  similar to Mininet's mid-level API extended with ESCAPEv2 related capabilities

  Separate the interface using internally from original Mininet object to
  implement loose coupling and avoid changes caused by Mininet API changes
  e.g. 2.1.0 -> 2.2.0

  Follows Bridge design pattern.
  """

  def __init__ (self, network, topo_desc=None):
    """
    Initialize Mininet implementation with proper attributes.
    Use network as the hided Mininet topology if it's given.

    :param network: use this specific Mininet object for init (default: None)
    :type network: :class:`mininet.net.MininetWithControlNet`
    :param topo_desc: static topology description e.g. the related NFFG
    :type topo_desc: :any:`NFFG`
    :return: None
    """
    if network is not None:
      self.__mininet = network
    else:
      log.warning(
        "Network implementation object is missing! Use Builder class instead "
        "of direct initialization. Creating bare Mininet object anyway...")
      self.__mininet = MininetWithControlNet()
    # Topology description which is emulated by the Mininet
    self.topo_desc = topo_desc
    # Need to clean after shutdown
    self._need_clean = None
    # There is no such flag in the Mininet class so using this
    self.started = False

  @property
  def network (self):
    """
    Internal network representation.

    :return: network representation
    :rtype: :class:`mininet.net.MininetWithControlNet`
    """
    return self.__mininet

  def start_network (self):
    """
    Start network.
    """
    log.debug("Starting Mininet network...")
    if self.__mininet is not None:
      if not self.started:
        try:
          self.__mininet.start()
        except SystemExit:
          quit_with_error(msg="Mininet emulation requires root privileges!",
                          logger=LAYER_NAME)
        self.started = True
        log.debug("Mininet network has been started!")
      else:
        log.warning(
          "Mininet network has already started! Skipping start task...")
    else:
      log.error("Missing topology! Skipping emulation...")

  def stop_network (self):
    """
    Stop network.
    """
    log.debug("Shutting down Mininet network...")
    if self.__mininet is not None:
      if self.started:
        self.__mininet.stop()
        self.started = False
        log.debug("Mininet network has been stopped!")
      else:
        log.warning("Mininet network is not started yet! Skipping stop task...")
    if self._need_clean:
      self.cleanup()

  def cleanup (self):
    """
    Clean up junk which might be left over from old runs.

    ..seealso::
      :func:`mininet.clean.cleanup() <mininet.clean.cleanup>`
    """

    def remove_junks ():
      # Kill remained clickhelper.py/click
      log.debug("Cleanup still-running click process...")
      run_silent(r"sudo pkill click")
      log.debug("Cleanup any remained veth pair...")
      veths = run_cmd(r"ip link show | egrep -o '(uny_\w+)'").split('\n')
      # only need to del one end of the veth pair
      for veth in veths[::2]:
        if veth != '':
          run_silent(r"sudo ip link del %s" % veth)
      log.debug("Cleanup any Mininet-specific junk...")
      # Call Mininet's own cleanup stuff
      cleanup()

    if self.started:
      log.warning(
        "Mininet network is not stopped yet! Skipping cleanup task...")
    else:
      log.info("Schedule cleanup task after Mininet emulation...")
      # Schedule a cleanup as a coop task to aviod threading issues
      call_as_coop_task(remove_junks)

  def get_agent_to_switch (self, switch_name):
    """
    Return the agent to which the given switch is tided..

    :param switch_name: name of the switch
    :type switch_name: str
    :return: the agent
    :rtype: :class:`mininet.node.NetconfAgent`
    """
    for switch in self.__mininet.switches:
      if switch.name == switch_name:
        return switch.agent
    return None


class TopologyBuilderException(Exception):
  """
  Exception class for topology errors.
  """
  pass


class ESCAPENetworkBuilder(object):
  """
  Builder class for topology.

  Update the network object based on the parameters if it's given or create
  an empty instance.

  Always return with an ESCAPENetworkBridge instance which offer a generic
  interface for created :any::`Mininet` object and hide implementation's nature.

  Follows Builder design pattern.
  """
  # Default initial options for Mininet
  default_opts = {"controller": InternalControllerProxy,  # Use own Controller
                  'build': False,  # Not build during init
                  'inNamespace': False,  # Not start element in namespace
                  'autoSetMacs': True,  # Set simple MACs
                  'autoStaticArp': True,  # Set static ARP entries
                  'listenPort': None}
  # Default internal storing format for NFFG parsing/reading from file
  DEFAULT_NFFG_FORMAT = "NFFG"
  # Constants
  TYPE_EE_LOCAL = "LOCAL"
  TYPE_EE_REMOTE = "REMOTE"

  def __init__ (self, net=None, opts=None, fallback=True, run_dry=True):
    """
    Initialize NetworkBuilder.

    If the topology definition is not found, an exception will be raised or
    an empty :any::`Mininet` topology will be created if ``run_dry`` is set.

    :param net: update given Mininet object instead of creating a new one
    :type net: :any::`Mininet`
    :param opts: update default options with the given opts
    :type opts: dict
    :param fallback: search for fallback topology (default: True)
    :type fallback: bool
    :param run_dry: do not raise an Exception and return with bare Mininet obj.
    :type run_dry: bool
    :return: None
    """
    self.opts = dict(self.default_opts)
    if opts is not None:
      self.opts.update(opts)
    self.fallback = fallback
    self.run_dry = run_dry
    if net is not None:
      if isinstance(net, Mininet):
        # Initial settings - Create new Mininet object if necessary
        self.mn = net
      else:
        raise RuntimeError(
          "Network object's type must be a derived class of Mininet!")
    else:
      # self.mn = Mininet(**self.opts)
      self.mn = MininetWithControlNet(**self.opts)
    # Basically a wrapper for mn to offer helping functions
    self.mn_bridge = None
    # Cache of the topology description as an NFFG which is parsed during
    # initialization
    self.topo_desc = None

  ##############################################################################
  # Topology initializer functions
  ##############################################################################

  def __init_from_NFFG (self, nffg):
    """
    Initialize topology from an :any:`NFFG` representation.

    :param nffg: topology object structure
    :type nffg: :any:`NFFG`
    :return: None
    """
    log.info("Start topology creation from NFFG(name: %s)..." % nffg.name)
    created_nodes = {}  # created nodes as 'NFFG-id': <node>
    # If not set then cache the given NFFG as the topology description
    self.topo_desc = nffg
    # Create a Controller which will be the default internal POX controller
    self.create_Controller("ESCAPE")
    # Convert INFRAs
    for infra in nffg.infras:
      # Create EE
      if infra.infra_type == NodeInfra.TYPE_EE:
        if infra.domain == "INTERNAL":
          ee_type = self.TYPE_EE_LOCAL
        else:
          ee_type = self.TYPE_EE_REMOTE
          # FIXME - set resource info in MN EE if can - cpu,mem,delay,bandwidth?
        agt, sw = self.create_NETCONF_EE(name=infra.id, type=ee_type)
        created_nodes[infra.id] = sw
      # Create Switch
      elif infra.infra_type == NodeInfra.TYPE_SDN_SWITCH:
        switch = self.create_Switch(name=infra.id)
        created_nodes[infra.id] = switch
      elif infra.infra_type == NodeInfra.TYPE_STATIC_EE:
        static_ee = self.create_static_EE(name=infra.id)
        created_nodes[infra.id] = static_ee
      else:
        raise RuntimeError("Building of %s is not supported by %s!" % (
          infra.infra_type, self.__class__.__name__))
    # Create SAPs
    for sap in nffg.saps:
      # Create SAP
      sap_host = self.create_SAP(name=sap.id)
      created_nodes[sap.id] = sap_host
    # Convert VNFs
    # TODO - implement --> currently the default Mininet topology does not
    # TODO contain NFs but it could be possible
    # Convert connections
    for edge in nffg.links:
      # Create Links
      src = created_nodes[edge.src.node.id]
      dst = created_nodes[edge.dst.node.id]
      if src is None or dst is None:
        raise RuntimeError(
          "Created topology node is missing! Something really went wrong!")
      # FIXME - check how port come in the picture
      link = self.create_Link(src=src, dst=dst)
    log.info("Topology creation from NFFG has been finished!")

  def __init_from_AbstractTopology (self, topo_class):
    """
    Build topology from pre-defined Topology class.

    :param topo_class: topology
    :type topo_class: :any:`AbstractTopology`
    :return: None
    """
    log.info("Load topology from class: %s" % topo_class.__name__)
    if topo_class.TYPE == "STATIC":
      self.mn.topo = topo_class().construct()
      self.mn.build()
    elif topo_class.TYPE == "DYNAMIC":
      # self.mn = topo_class().construct()
      topo_class().construct(builder=self)
    else:
      raise RuntimeError("TYPE field of the Topology class need to be set!")
    self.topo_desc = topo_class.get_topo_desc()

  def __init_from_CONFIG (self, path=None, format=DEFAULT_NFFG_FORMAT):
    """
    Build a pre-defined topology from an NFFG stored in a file.
    The file path is searched in CONFIG with tha name ``TOPO``.

    :param path: additional file path
    :type path: str
    :param format: NF-FG storing format (default: internal NFFG representation)
    :type format: str
    :return: None
    """
    if path is None:
      path = CONFIG.get_mininet_topology()
    if path is None:
      log.warning("Topology is missing from CONFIG!")
      raise TopologyBuilderException("Missing Topology!")
    else:
      try:
        with open(path, 'r') as f:
          log.info("Load topology from file: %s" % path)
          if format == self.DEFAULT_NFFG_FORMAT:
            self.__init_from_NFFG(NFFG.parse(f.read()))
          else:
            raise RuntimeError("Unsupported file format: %s!" % format)
      except IOError:
        log.debug("Additional topology file not found: %s" % path)
        raise TopologyBuilderException("Missing topology file!")
      except ValueError as e:
        log.error(
          "An error occurred when load topology from file: %s" % e.message)
        raise TopologyBuilderException("File parsing error!")

  def get_network (self):
    """
    Return the bridge to the constructed network.

    :return: object representing the emulated network
    :rtype: :any:`ESCAPENetworkBridge`
    """
    if self.mn_bridge is None:
      # Create the Interface object and set the topology description as the
      # original NFFG
      self.mn_bridge = ESCAPENetworkBridge(network=self.mn,
                                           topo_desc=self.topo_desc)
      # Additional settings
      self.mn_bridge._need_clean = CONFIG.get_clean_after_shutdown()
    return self.mn_bridge

  ##############################################################################
  # Builder functions
  ##############################################################################

  def create_static_EE (self, name, cls=None, **params):
    """
    Create and add a new EE to Mininet in the static way.

    This function is for only backward compatibility.

    .. warning::
      Not tested yet!

    :param name: name of the Execution Environment
    :type name: str
    :param cls: custom EE class/constructor (optional)
    :type cls: :class:`mininet.node.EE`
    :param cores: Specify (real) cores that our cgroup can run on (optional)
    :type cores: list
    :param frac: Set overall CPU fraction for this EE (optional)
    :type frac: list
    :param vlanif: set vlan interfaces (optional)
    :type vlanif: list
    :return: newly created EE object
    :rtype: :class:`mininet.node.EE`
    """
    # create static EE
    log.debug("Create static EE with name: %s" % name)
    ee = self.mn.addEE(name=name, cls=cls, **params)
    if 'cores' in params:
      ee.setCPUs(**params['cores'])
    if 'frac' in params:
      ee.setCPUFrac(**params['frac'])
    if 'vlanif' in params:
      for vif in params['vlaninf']:
        ee.cmdPrint('vconfig add ' + name + '-eth0 ' + vif[1])
        ee.cmdPrint('ifconfig ' + name + '-eth0.' + vif[1] + ' ' + vif[0])
    return ee

  def create_NETCONF_EE (self, name, type=TYPE_EE_LOCAL, **params):
    """
    Create and add a new EE to Mininet network.

    The type of EE can be {local|remote} NETCONF-based.

    :param name: name of the EE: switch: name, agent: agt_+'name'
    :type name: str
    :param type: type of EE {local|remote}
    :type type: str
    :param opts: additional options for the switch in EE
    :type opts: str
    :param dpid: remote switch DPID (remote only)
    :param username: NETCONF username (remote only)
    :param passwd: NETCONF password (remote only)
    :param ip: control Interface for the agent (optional)
    :param agentPort: port to listen on for NETCONF connections, (else set \
    automatically)
    :param minPort: first VNF control port which can be used (else set \
    automatically)
    :param cPort: number of VNF control ports (and VNFs) which can be used ( \
    default: 10)
    :return: tuple of newly created :class:`mininet.node.Agent` and \
    :class:`mininet.node.Switch` object
    :rtype: tuple
    """
    type = type.upper()
    if type == self.TYPE_EE_LOCAL:
      # create local NETCONF-based
      log.debug("Create local NETCONF EE with name: %s" % name)
      sw = self.mn.addSwitch(name)
    elif type == self.TYPE_EE_REMOTE:
      # create remote NETCONF-based
      log.debug("Create remote NETCONF EE with name: %s" % name)
      params["inNamespace"] = False

      sw = self.mn.addRemoteSwitch(name, cls=None, **params)
    else:
      raise RuntimeError("Unsupported NETCONF-based EE type: %s!" % type)
    agt = self.mn.addAgent('agt_' + name, cls=None, **params)
    agt.setSwitch(sw)
    return agt, sw

  def create_Switch (self, name, cls=None, **params):
    """
    Create and add a new OF switch instance to Mininet network.

    Additional parameters are keyword arguments depend on and forwarded to
    the initiated Switch class type.

    :param name: name of switch
    :type name: str
    :param cls: custom switch class/constructor (optional)
    :type cls: :class:`mininet.node.Switch`
    :param dpid: DPID for switch (default: derived from name)
    :type dpid: str
    :param opts: additional switch options
    :type opts: str
    :param listenPort: custom listening port (optional)
    :type listenPort: int
    :param inNamespace: override the switch spawn in namespace (optional)
    :type inNamespace: bool
    :param of_ver: override OpenFlow version (optional)
    :type of_ver: int
    :param ip: set IP address for the switch (optional)
    :type ip:
    :return: newly created Switch object
    :rtype: :class:`mininet.node.Switch`
    """
    log.debug("Create Switch with name: %s" % name)
    sw = self.mn.addSwitch(name=name, cls=cls, **params)
    if 'of_ver' in params:
      sw.setOpenFlowVersion(params['of_ver'])
    if 'ip' in params:
      sw.setSwitchIP(params['ip'])
    return sw

  def create_Controller (self, name, controller=None, **params):
    """
    Create and add a new OF controller to Mininet network.

    Additional parameters are keyword arguments depend on and forwarded to
    the initiated Controller class type.

    .. warning::
      Should not call this function and use the default InternalControllerProxy!

    :param name: name of controller
    :type name: str
    :param controller: custom controller class/constructor (optional)
    :type controller: :class:`mininet.node.Controller`
    :param inNamespace: override the controller spawn in namespace (optional)
    :type inNamespace: bool
    :return: newly created Controller object
    :rtype: :class:`mininet.node.Controller`
    """
    log.debug("Create Controller with name: %s" % name)
    return self.mn.addController(name=name, controller=controller, **params)

  def create_SAP (self, name, cls=None, **params):
    """
    Create and add a new SAP to Mininet network.

    Additional parameters are keyword arguments depend on and forwarded to
    the initiated Host class type.

    :param name: name of SAP
    :type name: str
    :param cls: custom hosts class/constructor (optional)
    :type cls: :class:`mininet.node.Host`
    :return: newly created Host object as the SAP
    :rtype: :class:`mininet.node.Host`
    """
    log.debug("Create SAP with name: %s" % name)
    return self.mn.addHost(name=name, cls=cls, **params)

  def create_Link (self, src, dst, src_port=None, dst_port=None, **params):
    """
    Create an undirected connection between src and dst.

    Source and destination ports can be given optionally:

    :param src: source Node
    :param dst: destination Node
    :param src_port: source Port (optional)
    :param dst_port: destination Port (optional)
    :param params: additional link parameters
    :return:
    """
    log.debug("Create Link %s%s <--> %s%s" % (
      src, ":%s" % src_port if src_port is not None else "", dst,
      ":%s" % dst_port if dst_port is not None else ""))
    remote = filter(lambda n: isinstance(n, RemoteSwitch), [src, dst])
    local = filter(lambda n: not isinstance(n, RemoteSwitch), [src, dst])
    if not remote:
      self.mn.addLink(src, dst, src_port, dst_port, **params)
    else:
      # sw = local[0]  # one of the local Node
      # r = remote[0]  # other Node which is the remote
      # intfName = r.params['local_intf_name']
      # r_mac = None  # unknown, r.params['remote_mac']
      # r_port = r.params['remote_port']
      # # self._debug('\tadd hw interface (%s) to node (%s)' % (intfName,
      # # sw.name))
      # # This hack avoids calling __init__ which always makeIntfPair()
      # link = Link.__new__(Link)
      # i1 = Intf(intfName, node=sw, link=link)
      # i2 = Intf(intfName, node=r, mac=r_mac, port=r_port, link=link)
      # i2.mac = r_mac  # mn runs 'ifconfig', which resets mac to None
      # link.intf1, link.intf2 = i1, i2
      raise RuntimeError("Remote Link creation is not supported yet!")

  def build (self, topo=None):
    """
    Initialize network.

    1. If the additional ``topology`` is given then using that for init.
    2. If TOPO is not given, search topology description in CONFIG with the \
    name 'TOPO'.
    3. If TOPO not found or an Exception was raised, search for the fallback \
    topo with the name ``FALLBACK-TOPO``.
    4. If FALLBACK-TOPO not found raise an exception or run a bare Mininet \
    object if the run_dry attribute is set


    :param topo: optional topology representation
    :type topo: :any:`NFFG` or :any:`AbstractTopology` or ``None``
    :return: object representing the emulated network
    :rtype: :any:`ESCAPENetworkBridge`
    """
    log.debug("Init emulated topology based on Mininet v%s" % MNVERSION)
    # Load topology
    try:
      if topo is None:
        log.info("Load Topology description from CONFIG...")
        self.__init_from_CONFIG()
      elif isinstance(topo, NFFG):
        log.info("Load Topology description from given NFFG...")
        self.__init_from_NFFG(nffg=topo)
      elif isinstance(topo, AbstractTopology):
        log.info("Load Topology description based on Topology class...")
        self.__init_from_AbstractTopology(topo=topo)
      else:
        raise RuntimeError("Unsupported topology format: %s" % type(topo))
      return self.get_network()
    except TopologyBuilderException:
      if self.fallback:
        # Search for fallback topology
        fallback = CONFIG.get_fallback_topology()
        if fallback:
          log.info("Load topo from fallback topology description...")
          self.__init_from_AbstractTopology(fallback)
          return self.get_network()
      # fallback topo is not found or set
      if self.run_dry:
        # Return with the bare Mininet object
        log.warning("Topology description is not found! Running dry...")
        return self.get_network()
      else:
        # Re-raise the exception
        raise
