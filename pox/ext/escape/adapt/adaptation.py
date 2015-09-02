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
Contains classes relevant to the main adaptation function of the Controller
Adaptation Sublayer
"""
import weakref

from escape import CONFIG
from escape.orchest.virtualization_mgmt import AbstractVirtualizer
from escape.adapt import log as log
from escape.adapt.components import InternalDomainManager
from escape.util.domain import DomainChangedEvent
from escape.util.nffg import NFFG


class ComponentConfigurator(object):
  """
  Initialize, configure and store DomainManager objects.
  Use global config to create managers and adapters.

  Follows Component Configurator design pattern.
  """

  def __init__ (self, ca, lazy_load=True):
    """
    For domain adapters the configurator checks the CONFIG first.

    .. warning::
      Adapter classes must be subclass of AbstractESCAPEAdapter

    .. note::
      Arbitrary domain adapters is searched in
      :mod:`escape.adapt.domain_adapters`

    :param ca: ControllerAdapter instance
    :type ca: :any:`ControllerAdapter`
    :param lazy_load: load adapters only at first reference (default: True)
    :type lazy_load: bool
    """
    log.debug("Init DomainConfigurator - lazy load: %s" % lazy_load)
    super(ComponentConfigurator, self).__init__()
    self.__repository = dict()
    self._lazy_load = lazy_load
    self._ca = ca
    if not lazy_load:
      # Initiate adapters from CONFIG
      self.load_default_mgrs()

  # General DomainManager handling functions: create/start/stop/get

  def get_mgr (self, domain_name):
    """
    Return the DomainManager with given name and create+start if needed.

    :param domain_name: name of domain manager
    :type domain_name: str
    :return: None
    """
    try:
      return self.__repository[domain_name]
    except KeyError:
      if self._lazy_load:
        return self.start_mgr(domain_name)
      else:
        raise AttributeError(
          "No adapter is defined with the name: %s" % domain_name)

  def start_mgr (self, domain_name, autostart=True):
    """
    Create, initialize and start a DomainManager with given name and start
    the manager by default.

    :param domain_name: name of domain manager
    :type domain_name: str
    :param autostart: also start the domain manager (default: True)
    :type autostart: bool
    :return: domain manager
    :rtype: :any:`AbstractDomainManager`
    """
    # If not started
    if not self.is_started(domain_name):
      # Load from CONFIG
      mgr = self.load_component(domain_name)
      if mgr is not None:
        # Call init - give self for the DomainManager to initiate the
        # necessary DomainAdapters itself
        mgr.init(self)
        # Autostart if needed
        if autostart:
          mgr.run()
          # Save into repository
        self.__repository[domain_name] = mgr
    else:
      log.warning("%s domain component has been already started! Skip "
                  "reinitialization..." % domain_name)
    # Return with manager
    return self.__repository[domain_name]

  def stop_mgr (self, domain_name):
    """
    Stop and derefer a DomainManager with given name and remove from the
    repository also.

    :param domain_name: name of domain manager
    :type domain_name: str
    :return: None
    """
    # If started
    if self.is_started(domain_name):
      # Call finalize
      self.__repository[domain_name].finit()
      # Remove from repository
      del self.__repository[domain_name]
    else:
      log.warning(
        "Missing domain component: %s! Skipping stop task..." % domain_name)

  def is_started (self, domain_name):
    """
    Return with the value the given domain manager is started or not.

    :param domain_name: name of domain manager
    :type domain_name: str
    :return: is loaded or not
    :rtype: bool
    """
    return domain_name in self.__repository

  @property
  def components (self):
    """
    Return the dict of initiated Domain managers.

    :return: container of initiated DomainManagers
    :rtype: dict
    """
    return self.__repository

  @property
  def initiated (self):
    return self.__repository.iterkeys()

  def __iter__ (self):
    """
    Return with an iterator over the (domain_name, DomainManager) items.
    """
    return self.__repository.iteritems()

  def __getitem__ (self, item):
    """
    Return with the DomainManager given by name: ``item``.

    :param item: component name
    :type item: str
    :return: component
    :rtype: :any:`AbstractDomainManager`
    """
    return self.get_mgr(item)

  # Configuration related functions

  def load_component (self, component_name):
    """
    Load given component (DomainAdapter/DomainManager) from config.
    Initiate the given component class, pass the additional attributes,
    register the event listeners and return with the newly created object.

    :param component_name: component's name
    :type component_name: str
    :return: initiated component
    :rtype: :any:`AbstractESCAPEAdapter` or :any:`AbstractDomainManager`
    """
    try:
      # Get component class
      component_class = CONFIG.get_component(component_name)
      # If it's found
      if component_class is not None:
        # Get optional parameters of this component
        params = CONFIG.get_component_params(component_name)
        # Initialize component
        component = component_class(**params)
        # Set up listeners for e.g. DomainChangedEvents
        component.addListeners(self._ca)
        # Set up listeners for DeployNFFGEvent
        component.addListeners(self._ca._layer_API)
        # Return the newly created object
        return component
      else:
        log.error(
          "Configuration of '%s' is missing. Skip initialization!" %
          component_name)
        raise RuntimeError("Missing component configuration!")
    except AttributeError:
      log.error(
        "%s is not found. Skip component initialization!" % component_name)
      raise

  def load_default_mgrs (self):
    """
    Initiate and start default DomainManagers defined in CONFIG.

    :return: None
    """
    # very dummy initialization
    for mgr in CONFIG.get_default_mgrs():
      self.start_mgr(domain_name=mgr)

  def load_internal_mgr (self):
    """
    Initiate the DomainManager for the internal domain.

    :return: None
    """
    self.start_mgr(InternalDomainManager.name)


class ControllerAdapter(object):
  """
  Higher-level class for :any:`NFFG` adaptation between multiple domains.
  """
  # DomainManager <-> NFFG domain name mapping
  DOMAIN_MAPPING = {"INTERNAL": NFFG.DOMAIN_INTERNAL,  # InternalDomainManager
                    "OPENSTACK": NFFG.DOMAIN_OS,  # for OpenStackDomainManager
                    "UN": NFFG.DOMAIN_UN,  # for UnifiedNodeDomainManager
                    "SDN": NFFG.DOMAIN_SDN,  # for SDNDomainManager
                    "REMOTE-ESCAPE": NFFG.DOMAIN_REMOTE}  # RemoteESCAPEDomain

  def __init__ (self, layer_API, with_infr=False):
    """
    Initialize Controller adapter.

    For domain components the ControllerAdapter checks the CONFIG first.

    :param layer_API: layer API instance
    :type layer_API: :any:`ControllerAdaptationAPI`
    :param with_infr: using emulated infrastructure (default: False)
    :type with_infr: bool
    """
    log.debug("Init ControllerAdapter - with IL: %s" % with_infr)
    super(ControllerAdapter, self).__init__()
    # Set a weak reference to avoid circular dependencies
    self._layer_API = weakref.proxy(layer_API)
    self._with_infr = with_infr
    # Set virtualizer-related components
    self.domainResManager = DomainResourceManager()
    self.domains = ComponentConfigurator(self)
    log.info("Initializing Domain Managers...")
    if with_infr:
      # Init internal domain manager if Infrastructure Layer is started
      self.domains.load_internal_mgr()
    # Init default domain managers
    self.domains.load_default_mgrs()
    # print "create test - VNFStarterAdapter"
    # from escape.adapt.components import VNFStarterAdapter
    # starter = VNFStarterAdapter(server='localhost', port=830,
    #                             username='mininet', password='mininet',
    #                             debug=True)
    # from pprint import pprint
    # with starter as s:
    #   reply = s.getVNFInfo()
    #   pprint(reply)
    #   reply = s.initiateVNF(vnf_type=s.VNF_HEADER_COMP)
    #   pprint(reply)
    #   vnf_id = reply['access_info']['vnf_id']
    #   reply = s.connectVNF(vnf_id=vnf_id, vnf_port=1, switch_id="EE1")
    #   reply = s.connectVNF(vnf_id=vnf_id, vnf_port=2, switch_id="EE1")
    #   pprint(reply)
    #   reply = s.startVNF(vnf_id=vnf_id)
    #   pprint(reply)
    #   reply = s.getVNFInfo()
    #   pprint(reply)

  def install_nffg (self, mapped_nffg):
    """
    Start NF-FG installation.

    Process given :any:`NFFG`, slice information based on domains an invoke
    DomainManagers to install domain specific parts.

    :param mapped_nffg: mapped NF-FG instance which need to be installed
    :type mapped_nffg: NFFG
    :return: None or internal domain NFFG part
    """
    # # TEST - VNF initiation start
    # import escape.util.nffg
    #
    # nffg = escape.util.nffg.generate_mn_topo()
    # nf1 = nffg.add_nf(id='nf1', name="NF1", func_type="headerCompressor",
    #                   cpu=10, mem=20, storage=30)
    # nf2 = nffg.add_nf(id='nf2', name="NF2", func_type="headerDecompressor",
    #                   mem=30, storage=40, delay=50)
    # nffg.add_undirected_link(nf1.add_port(1),
    #                          nffg.network.node['EE1'].add_port(),
    # dynamic=True,
    #                          delay=60, bandwidth=70)
    # nffg.add_undirected_link(nf2.add_port(1),
    #                          nffg.network.node['EE2'].add_port(),
    # dynamic=True,
    #                          delay=80, bandwidth=90)
    # mapped_nffg = nffg
    # # TEST - VNF initiation end
    # print "Test mapped NFFG:\n", mapped_nffg.dump()
    log.debug("Invoke %s to install NF-FG(%s)" % (
      self.__class__.__name__, mapped_nffg.name))
    for domain, part in self._slice_into_domains(mapped_nffg):
      log.debug(
        "Delegate splitted part: %s to %s domain manager..." % (part, domain))
      self.domains[domain].install_nffg(part)
    log.debug("NF-FG installation is finished by %s" % self.__class__.__name__)

  def _handle_DomainChangedEvent (self, event):
    """
    Handle DomainChangedEvents, process changes and store relevant information
    in DomainResourceManager.
    """
    log.info("Received DomainChange event from domain: %s, cause: %s" % (
      event.domain, DomainChangedEvent.TYPE.reversed[event.cause]))
    if event.data is not None and isinstance(event.data, NFFG):
      self.domainResManager.update_domain_resource(event.domain, event.data)

  def _slice_into_domains (self, nffg):
    """
    Slice given :any:`NFFG` into separate parts based on original domains.

    .. warning::
      Not implemented yet!

    :param nffg: mapped NFFG object
    :type nffg: NFFG
    :return: sliced parts as a list of (domain_name, nffg_part) tuples
    :rtype: list
    """
    # TODO - implement slicing, replace dummy 'all in' solution

    with open('pox/global-mapped.nffg', 'r') as f:
      nffg = NFFG.parse(f.read())
    sliced_parts = []
    for infra in nffg.infras:
      if infra.domain not in [NFFG.DOMAIN_OS, NFFG.DOMAIN_UN]:
        continue
      nffg_part = NFFG(id=infra.id, name=infra.domain)
      nffg_part.add_infra(infra=infra)
      for u, v, l in nffg.network.out_edges_iter((infra.id,), data=True):
        if l.dst.node.type == NFFG.TYPE_NF:
          nf = l.dst.node
          if nf not in [n for n in nffg_part.nfs]:
            nffg_part.add_nf(nf=nf)
          nffg_part.add_undirected_link(l.src, l.dst, dynamic=True)
      log.debug("Store splitted NFFG...")
      if infra.domain == NFFG.DOMAIN_OS:
        dom = 'OPENSTACK'
      elif infra.domain == NFFG.DOMAIN_UN:
        dom = 'UN'
      sliced_parts.append((dom, nffg_part))
    # for n in sliced_parts:
    #   print n[1].dump()

    return ((domain, nffg) for domain in self.domains.components)
    # return sliced_parts

    # for domain in self.domains.initiated:
    #   log.debug("Slicing mapped NFFG: %s for domain: %s" % (nffg, domain))
    #   # Make copy for all domains
    #   nffg_part = nffg.copy()
    #   # Iter over the Infra Nodes and remove the one's in other domains
    #   for infra in nffg.infras:
    #     # If the infra's domain not the domain of the splitting
    #     if infra.domain != self.DOMAIN_MAPPING[domain]:
    #       # Remove the infra's
    #       nffg_part.del_node(infra)
    #   # Remove orphaned NFs and SAPs
    #   for node in {n for id, n in nffg_part.network.nodes_iter(data=True) if
    #                n.type == NFFG.TYPE_NF or n.type == NFFG.TYPE_SAP}:
    #     if len({l for u, v, l in
    #             nffg_part.network.out_edges_iter((node.id,), data=True)}) == 0:
    #       nffg_part.del_node(node)
    #   # Recreate inter-domain SAP from port
    #   for infra in nffg.infras:
    #     for port in infra.ports:
    #       for property in port.properties:
    #         if property.statswith("inter-domain"):
    #           # Got inter-domain port
    #           _id = property.split(':')[1]
    #           _name = _id
    #           # Create SAP object
    #           sap = nffg_part.add_sap(id=_id, name=_name)
    #           sap_port = sap.add_port(id=port.id)
    #           # Connect SAP to Infra
    #           nffg_part.add_undirected_link(port1=port, port2=sap_port)
    #   # Add splitted NFFG to returned structure
    #   log.debug("Store splitted NFFG...")
    #   sliced_parts.append((domain, nffg_part))
    #   print nffg_part.dump()
    # return sliced_parts


# Common reference name for the DomainVirtualizer
DoV = "DoV"


class DomainVirtualizer(AbstractVirtualizer):
  """
  Specific Virtualizer class for global domain virtualization.

  Implement the same interface as :class:`AbstractVirtualizer
  <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`

  Use :any:`NFFG` format to store the global infrastructure info.
  """

  def __init__ (self, domainResManager, global_res=None):
    """
    Init.

    :param domainResManager: domain resource manager
    :type domainResManager: DomainResourceManager
    :param global_res: initial global resource (optional)
    :type global_res: :any:`NFFG`
    :return: None
    """
    super(DomainVirtualizer, self).__init__(id=None)
    log.debug("Init DomainVirtualizer with name: %s - initial resource: %s" % (
      DoV, global_res))
    # Garbage-collector safe
    self.domainResManager = weakref.proxy(domainResManager)
    if global_res is not None:
      self.set_global_view(domain=NFFG.DOMAIN_VIRTUAL, nffg=global_res)
    else:
      self.__global_nffg = None
      """:type: NFFG"""

  @property
  def name (self):
    return self.__global_nffg.name if self.__global_nffg.name is not None \
      else DoV + "-uninitialized"

  def __str__ (self):
    return "DoV(name=%s)" % self.name

  def __repr__ (self):
    return super(DomainVirtualizer, self).__repr__()

  def get_resource_info (self):
    """
    Return the global resource info represented this class.

    :return: global resource info
    :rtype: :any:`NFFG`
    """
    return self.__global_nffg

  def set_global_view (self, domain, nffg):
    """
    Set the copy of given NFFG as the global view of DoV.

    :param nffg: NFFG instance intended to use as the global view
    :type nffg: :any:`NFFG`
    :return: None
    """
    log.debug("Set domain: %s as the global view!" % domain)
    self.__global_nffg = nffg.copy()
    self.__global_nffg.id = "dov-" + self.__global_nffg.generate_id()
    self.__global_nffg.name = "DoV"

  def merge_domain_into_dov (self, domain, nffg):
    """
    Add a newly detected domain to DoV.
    """
    # Create full copy
    nffg = nffg.copy()
    from pprint import pprint
    # pprint(self.__global_nffg.network.__dict__)
    # pprint(nffg.network.__dict__)
    # Copy infras
    log.debug("Merge domain: %s resource info into DoV..." % domain)
    for infra in nffg.infras:
      pprint(self.__global_nffg.network.__dict__)
      inf = self.__global_nffg.add_infra(infra=infra)
      log.debug("Copy infra node: %s" % inf)
    # Copy SAPs
    saps_to_del = []
    for sap in [s for s in nffg.saps]:
      # If inter-domain connection is found -> merge saps into a link
      if sap.id in [s.id for s in self.__global_nffg.saps]:
        log.debug("Detected inter-domain SAP: %s" % sap)
        # Get DoV side infra port of inter domain SAP
        link_dov = [link for u, v, link in
                    self.__global_nffg.network.out_edges_iter([sap.id],
                                                              data=True) if
                    link.type == NFFG.TYPE_LINK_STATIC]
        if len(link_dov) > 1:
          log.warning(
            "Inter-domain SAP should be only one connection to it's domain!")
        dov_port = link_dov[0].dst
        # Add property to save inter-domain information in merged NFFG
        dov_port.add_property("inter-domain:%s" % sap.id)
        # Get new domain side infra port
        link_nffg = [link for u, v, link in
                     nffg.network.out_edges_iter([sap.id], data=True) if
                     link.type == NFFG.TYPE_LINK_STATIC]
        if len(link_nffg) > 1:
          log.warning(
            "Inter-domain SAP should be only one connection to it's domain!")
        # Add property to save inter-domain information in merged NFFG
        nffg_port = link_nffg[0].dst
        nffg_port.add_property("inter-domain:%s" % sap.id)
        # Add inter-domain link here, because it's not in any of the two NFFG
        self.__global_nffg.add_undirected_link(port1=dov_port, port2=nffg_port,
                                               delay=link_dov[0].delay,
                                               bandwidth=link_dov[0].bandwidth)
        # Remove original inter-domain SAP (and the connection as well)
        self.__global_nffg.del_node(sap.id)
        # Remove new domain SAP to skip founding it the further
        saps_to_del.append(sap.id)
        nffg.del_node(sap.id)
      else:
        # Not inter-domain SAP -> just copy
        log.debug("Copy SAP: %s" % sap)
        self.__global_nffg.add_sap(sap=sap)
      # pprint(self.__global_nffg.network.__dict__)
      for link in {l for l in nffg.links if l.type == NFFG.TYPE_LINK_STATIC}:
        log.debug("Copy connection: %s" % link)
        self.__global_nffg.add_link(src_port=link.src, dst_port=link.dst,
                                    link=link)
        # pprint(self.__global_nffg.network.__dict__)
    for sap in saps_to_del:
      nffg.del_node(sap)
      self.__global_nffg.del_node(sap)

  def update_domain_view (self, domain, nffg):
    """
    """
    pass


class DomainResourceManager(object):
  """
  Handle and store the global resources view.
  """

  def __init__ (self):
    """
    Init.
    """
    super(DomainResourceManager, self).__init__()
    log.debug("Init DomainResourceManager")
    # FIXME - SIGCOMM
    # self.__dov = DomainVirtualizer(self)  # Domain Virtualizer
    with open('pox/dov.nffg', 'r') as f:
      nffg = NFFG.parse(f.read())
    self.__dov = DomainVirtualizer(self, global_res=nffg)  # Domain Virtualizer
    self._tracked_domains = set()  # Cache for detected and stored domains

  def get_global_view (self):
    """
    Getter for :class:`DomainVirtualizer`.

    :return: global infrastructure view as the Domain Virtualizer
    :rtype: :any:`DomainVirtualizer`
    """
    return self.__dov

  def update_domain_resource (self, domain, nffg):
    """
    Update the global view database with the specific domain info.

    :param domain: domain name
    :type domain: str
    :param nffg: infrastructure info collected from the domain
    :type nffg: :any:`NFFG`
    :return: None
    """
    if domain == "INTERNAL-POX":
      # skip POX events currently
      pass
    if domain not in self._tracked_domains:
      log.info("Append %s domain to <Global Resource View> (DoV)..." % domain)
      if self._tracked_domains:
        # Merge domain topo into global view
        self.__dov.merge_domain_into_dov(domain, nffg)
      else:
        # No other domain detected, set NFFG as the whole global view
        log.debug(
          "DoV is empty! Add new domain: %s as the global view!" % domain)
        self.__dov.set_global_view(domain, nffg)
      # Add detected domain to cached domains
      self._tracked_domains.add(domain)
    else:
      log.info("Updating <Global Resource View> from %s domain..." % domain)
      # FIXME - only support INTERNAL domain ---> extend & improve !!!
      if domain == 'INTERNAL':
        self.__dov.update_domain_view(domain, nffg)
        # FIXME - SIGCOMM
        # print self.__dov.get_resource_info().dump()
