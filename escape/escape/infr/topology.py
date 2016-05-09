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
from escape import CONFIG
from escape.infr import log, LAYER_NAME
from escape.nffg_lib.nffg import NFFG
from escape.nffg_lib.nffg_elements import NodeInfra
from escape.util.misc import quit_with_error, get_ifaces
from mininet.link import TCLink, Intf
from mininet.net import VERSION as MNVERSION, Mininet, MininetWithControlNet
from mininet.node import RemoteController, RemoteSwitch
from mininet.term import makeTerms
from mininet.topo import Topo


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
    # Topo is Old-style class
    Topo.__init__(self, hopts, sopts, lopts, eopts)

  def construct (self, builder=None):
    """
    Base class for construct the topology.

    :param builder: builder object
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
    sw1 = nffg.add_infra(id="sw1", name="SW1", domain="INTERNAL",
                         infra_type=NFFG.TYPE_INFRA_SDN_SW)
    sw2 = nffg.add_infra(id="sw2", name="SW2", domain="INTERNAL",
                         infra_type=NFFG.TYPE_INFRA_SDN_SW)
    sw3 = nffg.add_infra(id="sw3", name="SW3", domain="INTERNAL",
                         infra_type=NFFG.TYPE_INFRA_SDN_SW)
    sw4 = nffg.add_infra(id="sw4", name="SW4", domain="INTERNAL",
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
    # nffg.duplicate_static_links()
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

    :param builder: builder object
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
    nc1 = nffg.add_infra(id="nc1", name="NC1", domain="INTERNAL",
                         infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                         delay=0.9, bandwidth=5000)
    nc2 = nffg.add_infra(id="nc2", name="NC2", domain="INTERNAL",
                         infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                         delay=0.9, bandwidth=5000)
    nc1.add_supported_type(['A', 'B'])
    nc2.add_supported_type(['A', 'C'])
    # Add inter-EE switches
    sw3 = nffg.add_infra(id="sw3", name="SW3", domain="INTERNAL",
                         infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.2,
                         bandwidth=10000)
    sw4 = nffg.add_infra(id="sw4", name="SW4", domain="INTERNAL",
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
    # No need for that, ESCAPENetworkBridge do this later
    # nffg.duplicate_static_links()
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
    # Using old-style class because of MN's RemoteController class
    RemoteController.__init__(self, name, ip, port, **kwargs)

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
  e.g. 2.1.0 -> 2.2.0.

  Follows Bridge design pattern.
  """

  def __init__ (self, network=None, topo_desc=None):
    """
    Initialize Mininet implementation with proper attributes.
    Use network as the hided Mininet topology if it's given.

    :param topo_desc: static topology description e.g. the related NFFG
    :type topo_desc: :any:`NFFG`
    :param network: use this specific Mininet object for init (default: None)
    :type network: :class:`mininet.net.MininetWithControlNet`
    :return: None
    """
    log.debug("Init ESCAPENetworkBridge with topo description: %s" % topo_desc)
    if network is not None:
      self.__mininet = network
    else:
      log.warning(
        "Network implementation object is missing! Use Builder class instead "
        "of direct initialization. Creating bare Mininet object anyway...")
      self.__mininet = MininetWithControlNet()
    # Topology description which is emulated by the Mininet
    self.topo_desc = topo_desc
    # Duplicate static links for ensure undirected neighbour relationship
    if self.topo_desc is not None:
      back_links = [l.id for u, v, l in
                    self.topo_desc.network.edges_iter(data=True) if
                    l.backward is True]
      if len(back_links) == 0:
        log.debug("No backward link has been detected! Duplicate STATIC links "
                  "to ensure undirected relationship for mapping...")
      self.topo_desc.duplicate_static_links()
    # Need to clean after shutdown
    self._need_clean = None
    # There is no such flag in the Mininet class so using this
    self.started = False
    self.xterms = []

  @property
  def network (self):
    """
    Internal network representation.

    :return: network representation
    :rtype: :class:`mininet.net.MininetWithControlNet`
    """
    return self.__mininet

  def runXTerms (self):
    """
    Start an xterm to every SAP if it's enabled in the global config. SAP are
    stored as hosts in the Mininet class.

    :return: None
    """
    if CONFIG.get_SAP_xterms():
      log.debug("Starting xterm on SAPS...")
      terms = makeTerms(nodes=self.__mininet.hosts, title='SAP', term="xterm")
      self.xterms.extend(terms)
    else:
      log.warning("Skip starting xterms on SAPS according to global config")

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
        except KeyboardInterrupt:
          quit_with_error(
            msg="Initiation of Mininet network was interrupted by user!",
            logger=log)
        self.started = True
        log.debug("Mininet network has been started!")
        self.runXTerms()
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
    if self.started:
      log.warning(
        "Mininet network is not stopped yet! Skipping cleanup task...")
    else:
      log.info("Schedule cleanup task after Mininet emulation...")
      # Kill remained xterms
      log.debug("Close SAP xterms...")
      import os
      import signal
      for term in self.xterms:
        os.killpg(term.pid, signal.SIGTERM)
      # Schedule a cleanup as a coop task to avoid threading issues
      from escape.util.misc import remove_junks
      # call_as_coop_task(remove_junks, log=log)
      # threading.Thread(target=remove_junks, name="cleanup", args=(log,
      # )).start()
      # multiprocessing.Process(target=remove_junks, name="cleanup",
      #                         args=(log,)).start()
      remove_junks(log=log)

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
  interface for created :class:`mininet.net.Mininet` object and hide
  implementation's nature.

  Follows Builder design pattern.
  """
  # Default initial options for Mininet
  default_opts = {
    "controller": InternalControllerProxy,
    # Use own Controller
    'build': False,  # Not build during init
    'inNamespace': False,  # Not start element in namespace
    'autoSetMacs': False,  # Set simple MACs
    'autoStaticArp': True,  # Set static ARP entries
    'listenPort': None,  # Add listen port to OVS switches
    'link': TCLink  # Add default link
  }
  # Default internal storing format for NFFG parsing/reading from file
  DEFAULT_NFFG_FORMAT = "NFFG"
  # Constants
  TYPE_EE_LOCAL = "LOCAL"
  TYPE_EE_REMOTE = "REMOTE"
  # Constants for DPID generation
  dpidBase = 1  # Switches start with port 1 in OpenFlow
  dpidLen = 16  # digits in dpid passed to switch

  def __init__ (self, net=None, opts=None, fallback=True, run_dry=True):
    """
    Initialize NetworkBuilder.

    If the topology definition is not found, an exception will be raised or
    an empty :class:`mininet.net.Mininet` topology will be created if
    ``run_dry`` is set.

    :param net: update given Mininet object instead of creating a new one
    :type net: :class:`mininet.net.Mininet`
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
        raise TopologyBuilderException(
          "Network object's type must be a derived class of Mininet!")
    else:
      # self.mn = Mininet(**self.opts)
      try:
        self.mn = MininetWithControlNet(**self.opts)
      except KeyboardInterrupt:
        quit_with_error(
          msg="Assembly of Mininet network was interrupted by user!",
          logger=log)
    # Basically a wrapper for mn to offer helping functions
    self.mn_bridge = None
    # Cache of the topology description as an NFFG which is parsed during
    # initialization
    self.topo_desc = None
    self.__dpid_cntr = self.dpidBase

  def __get_new_dpid (self):
    """
    Generate a new DPID and return the valid format for Mininet/OVS.

    :return: new DPID
    :rtype: str
    """
    dpid = hex(int(self.__dpid_cntr))[2:]
    dpid = '0' * (self.dpidLen - len(dpid)) + dpid
    self.__dpid_cntr += 1
    return dpid

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
    # pprint(nffg.network.__dict__)
    log.info("Start topology creation from NFFG(name: %s)..." % nffg.name)
    created_mn_nodes = {}  # created nodes as 'NFFG-id': <node>
    created_mn_links = {}  # created links as 'NFFG-id': <link>
    # If not set then cache the given NFFG as the topology description
    self.topo_desc = nffg
    # Create a Controller which will be the default internal POX controller
    try:
      self.create_Controller("ESCAPE")
    except SystemExit:
      raise TopologyBuilderException("Controller creations was unsuccessful!")
    # Convert INFRAs
    for infra in nffg.infras:
      # Create EE
      if infra.infra_type == NodeInfra.TYPE_EE:
        if infra.domain == "INTERNAL":
          ee_type = self.TYPE_EE_LOCAL
        else:
          log.warning(
            "Detected domain of infra: %s is not INTERNAL! Remote EE creation "
            "for domains other than INTERNAL is not supported yet!" % infra)
          # ee_type = self.TYPE_EE_REMOTE
          ee_type = self.TYPE_EE_LOCAL
          # FIXME - set resource info in MN EE if can - cpu,mem,delay,bandwidth?
        agt, sw = self.create_NETCONF_EE(name=infra.id, type=ee_type)
        created_mn_nodes[infra.id] = sw
      # Create Switch
      elif infra.infra_type == NodeInfra.TYPE_SDN_SWITCH:
        switch = self.create_Switch(name=infra.id)
        created_mn_nodes[infra.id] = switch
      elif infra.infra_type == NodeInfra.TYPE_STATIC_EE:
        static_ee = self.create_static_EE(name=infra.id)
        created_mn_nodes[infra.id] = static_ee
      else:
        quit_with_error(
          msg="Type: %s in %s is not supported by the topology creation "
              "process in %s!" % (
                infra.infra_type, infra, self.__class__.__name__), logger=log)
    # Create SAPs - skip the temporary, inter-domain SAPs
    for sap in {s for s in nffg.saps if not s.domain}:
      # Create SAP
      sap_host = self.create_SAP(name=sap.id)
      created_mn_nodes[sap.id] = sap_host
    # Convert VNFs
    # TODO - implement --> currently the default Mininet topology does not
    # TODO contain NFs but it could be possible
    # Convert connections - copy link ref in a list and iter over it
    for edge in [l for l in nffg.links]:
      # Skip initiation of links which connected to an inter-domain SAP
      if (edge.src.node.type == NFFG.TYPE_SAP and
              edge.src.node.domain is not None) or (
             edge.dst.node.type == NFFG.TYPE_SAP and
             edge.dst.node.domain is not None):
        continue
      # Create Links
      mn_src_node = created_mn_nodes.get(edge.src.node.id)
      mn_dst_node = created_mn_nodes.get(edge.dst.node.id)
      if mn_src_node is None or mn_dst_node is None:
        raise TopologyBuilderException(
          "Created topology node is missing! Something really went wrong!")
      src_port = int(edge.src.id) if int(edge.src.id) < 65535 else None
      if src_port is None:
        log.warning(
          "Source port id of Link: %s is generated dynamically! Using "
          "automatic port assignment based on internal Mininet "
          "implementation!" % edge)
      dst_port = int(edge.dst.id) if int(edge.dst.id) < 65535 else None
      if dst_port is None:
        log.warning(
          "Destination port id of Link: %s is generated dynamically! Using "
          "automatic port assignment based on internal Mininet "
          "implementation!" % edge)
      link = self.create_Link(src=mn_src_node, src_port=src_port,
                              dst=mn_dst_node, dst_port=dst_port,
                              bw=edge.bandwidth, delay=str(edge.delay) + 'ms')
      created_mn_links[edge.id] = link

    # Set port properties of SAP nodes.
    #  A possible excerpt from a escape-mn-topo.nffg file:
    #  "ports": [{ "id": 1,
    #              "property": ["ip:10.0.10.1/24"] }]
    #
    for n in {s for s in nffg.saps if not s.domain}:
      mn_node = self.mn.getNodeByName(n.id)
      for port in n.ports:
        # ip should be something like '10.0.123.1/24'.
        ip = port.get_property('ip')
        mac = port.get_property('mac')
        intf = mn_node.intfs.get(port.id)
        if intf is None:
          log.warn(("Port %s of node %s is not connected,"
                    "it will remain unconfigured!") % (port.id, n.name))
          continue
        if intf == mn_node.defaultIntf():
          # Workaround a bug in Mininet
          mn_node.params.update({'ip': ip})
          mn_node.params.update({'mac': mac})
        if ip is not None:
          mn_node.setIP(ip, intf=intf)
        if mac is not None:
          mn_node.setMAC(mac, intf=intf)

    # For inter-domain SAPs no need to create host/xterm just add the SAP as
    # a port to the border Node
    # Iterate inter-domain SAPs
    self.bind_inter_domain_SAPs(nffg=nffg)
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
      raise TopologyBuilderException(
        "TYPE field of the Topology class need to be set!")
    self.topo_desc = topo_class.get_topo_desc()

  def __init_from_CONFIG (self, format=DEFAULT_NFFG_FORMAT):
    """
    Build a pre-defined topology from an NFFG stored in a file.
    The file path is searched in CONFIG with tha name ``TOPO``.

    :param format: NF-FG storing format (default: internal NFFG representation)
    :type format: str
    :return: None
    """
    path = CONFIG.get_mininet_topology()
    if path is None:
      raise TopologyBuilderException("Missing Topology!")
    self.__init_from_file(path=path, format=format)

  def __init_from_file (self, path, format=DEFAULT_NFFG_FORMAT):
    """
    Build a pre-defined topology from an NFFG stored in a file.
    The file path is searched in CONFIG with tha name ``TOPO``.

    :param path: file path
    :type path: str
    :param format: NF-FG storing format (default: internal NFFG representation)
    :type format: str
    :return: None
    """
    if path is None:
      log.error("Missing file path of Topology description")
      return
    try:
      with open(path, 'r') as f:
        log.info("Load topology from file: %s" % path)
        if format == self.DEFAULT_NFFG_FORMAT:
          log.info("Using file format: %s" % format)
          self.__init_from_NFFG(nffg=NFFG.parse(f.read()))
        else:
          raise TopologyBuilderException("Unsupported file format: %s!" %
                                         format)
    except IOError:
      log.warning("Additional topology file not found: %s" % path)
      raise TopologyBuilderException("Missing topology file!")
    except ValueError as e:
      log.error("An error occurred when load topology from file: %s" %
                e.message)
      raise TopologyBuilderException("File parsing error!")
      # except SystemExit:
      #   raise TopologyBuilderException("Got exit exception from Mininet!")

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
    cfg = CONFIG.get_EE_params()
    cfg.update(params)
    cfg['dpid'] = self.__get_new_dpid()
    log.debug("Create static EE with name: %s" % name)
    ee = self.mn.addEE(name=name, cls=cls, **cfg)
    if 'cores' in cfg:
      ee.setCPUs(**cfg['cores'])
    if 'frac' in cfg:
      ee.setCPUFrac(**cfg['frac'])
    if 'vlanif' in cfg:
      for vif in cfg['vlaninf']:
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
    cfg = CONFIG.get_EE_params()
    cfg.update(params)
    cfg['dpid'] = self.__get_new_dpid()
    if type == self.TYPE_EE_LOCAL:
      # create local NETCONF-based
      log.debug("Create local NETCONF EE with name: %s" % name)
      sw = self.mn.addSwitch(name, **cfg)
    elif type == self.TYPE_EE_REMOTE:
      # create remote NETCONF-based
      log.debug("Create remote NETCONF EE with name: %s" % name)
      cfg["inNamespace"] = False
      sw = self.mn.addRemoteSwitch(name, cls=None, **cfg)
    else:
      raise TopologyBuilderException(
        "Unsupported NETCONF-based EE type: %s!" % type)
    agt = self.mn.addAgent('agt_' + name, cls=None, **cfg)
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
    cfg = CONFIG.get_Switch_params()
    cfg.update(params)
    cfg['dpid'] = self.__get_new_dpid()
    sw = self.mn.addSwitch(name=name, cls=cls, **cfg)
    if 'of_ver' in cfg:
      sw.setOpenFlowVersion(cfg['of_ver'])
    if 'ip' in cfg:
      sw.setSwitchIP(cfg['ip'])
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
    cfg = CONFIG.get_Controller_params()
    cfg.update(params)
    return self.mn.addController(name=name, controller=controller, **cfg)

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
    cfg = CONFIG.get_SAP_params()
    cfg.update(params)
    return self.mn.addHost(name=name, cls=cls, **cfg)

  def bind_inter_domain_SAPs (self, nffg):
    """
    Search for inter-domain SAPs in given :any:`NFFG`, create them as a
    switch port and bind them to a physical interface given in sap.domain
    attribute.

    :param nffg: topology description
    :type nffg: :any:`NFFG`
    :return: None
    """
    log.debug("Search for inter-domain SAPs...")
    # Create the inter-domain SAP ports
    for sap in {s for s in nffg.saps if s.domain is not None}:
      # NFFG is the raw NFFG without link duplication --> iterate over every
      # edges in or out there should be only one link in this case
      # e = (u, v, data)
      sap_switch_links = [e for e in
                          nffg.network.edges_iter(data=True) if sap.id in e]
      try:
        if sap_switch_links[0][0] == sap.id:
          border_node = sap_switch_links[0][1]
        else:
          border_node = sap_switch_links[0][0]
      except IndexError:
        log.error("Link for inter-domain SAP: %s is not found. "
                  "Skip SAP creation..." % sap)
        continue
      log.debug("Detected inter-domain SAP: %s connected to border Node: %s" %
                (sap, border_node))
      if sap.delay or sap.bandwidth:
        log.debug("Detected resource values for inter-domain connection: "
                  "delay: %s, bandwidth: %s" % (sap.delay, sap.bandwidth))
      sw_name = nffg.network.node[border_node].id
      for sw in self.mn.switches:
        # print sw.name
        if sw.name == sw_name:
          if sap.domain not in get_ifaces():
            log.warning(
              "Physical interface: %s is not found! Skip binding..."
              % sap.domain)
            continue
          log.debug("Add physical port as inter-domain SAP: %s -> %s" %
                    (sap.domain, sap.id))
          # Add interface to border switch in Mininet
          # os.system('ovs-vsctl add-port %s %s' % (sw_name, sap.domain))
          sw.addIntf(intf=Intf(name=sap.domain, node=sw))

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
    cfg = CONFIG.get_Link_params()
    cfg.update(params)
    if not remote:
      self.mn.addLink(src, dst, src_port, dst_port, **cfg)
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
      raise TopologyBuilderException(
        "Remote Link creation is not supported yet!")

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
        log.info("Get Topology description from CONFIG...")
        self.__init_from_CONFIG()
      elif isinstance(topo, NFFG):
        log.info("Get Topology description from given NFFG...")
        self.__init_from_NFFG(nffg=topo)
      elif isinstance(topo, basestring) and topo.startswith('/'):
        log.info("Get Topology description from given file...")
        self.__init_from_file(path=topo)
      elif isinstance(topo, AbstractTopology):
        log.info("Get Topology description based on Topology class...")
        self.__init_from_AbstractTopology(topo_class=topo)
      else:
        raise TopologyBuilderException(
          "Unsupported topology format: %s - %s" % (type(topo), topo))
      return self.get_network()
    except SystemExit as e:
      quit_with_error(msg="Mininet exited unexpectedly!", logger=log,
                      exception=e)
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
    except KeyboardInterrupt:
      quit_with_error(
        msg="Assembly of Mininet network was interrupted by user!",
        logger=log)
