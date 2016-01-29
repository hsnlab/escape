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
import traceback
import weakref

import escape.adapt.managers as mgrs
from escape import CONFIG
from escape.adapt import log as log, LAYER_NAME
from escape.orchest.virtualization_mgmt import AbstractVirtualizer
from escape.util.config import ConfigurationError
from escape.util.domain import DomainChangedEvent
from escape.util.misc import notify_remote_visualizer
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

  def get_mgr (self, name):
    """
    Return the DomainManager with given name and create+start if needed.

    :param name: name of domain manager
    :type name: str
    :return: None
    """
    try:
      return self.__repository[name]
    except KeyError:
      if self._lazy_load:
        return self.start_mgr(name)
      else:
        raise AttributeError(
           "No component is registered with the name: %s" % name)

  def start_mgr (self, name, autostart=True):
    """
    Create, initialize and start a DomainManager with given name and start
    the manager by default.

    :param name: name of domain manager
    :type name: str
    :param autostart: also start the domain manager (default: True)
    :type autostart: bool
    :return: domain manager
    :rtype: :any:`AbstractDomainManager`
    """
    # If not started
    if not self.is_started(name):
      # Load from CONFIG
      mgr = self.load_component(name)
      if mgr is not None:
        # Call init - give self for the DomainManager to initiate the
        # necessary DomainAdapters itself
        mgr.init(self)
        # Autostart if needed
        if autostart:
          mgr.run()
          # Save into repository
        self.__repository[name] = mgr
    else:
      log.warning("%s domain component has been already started! Skip "
                  "reinitialization..." % name)
    # Return with manager
    return self.__repository[name]

  def stop_mgr (self, name):
    """
    Stop and derefer a DomainManager with given name and remove from the
    repository also.

    :param name: name of domain manager
    :type name: str
    :return: None
    """
    # If started
    if self.is_started(name):
      # Call finalize
      self.__repository[name].finit()
      # Remove from repository
      # del self.__repository[domain_name]
    else:
      log.warning(
         "Missing domain component: %s! Skipping stop task..." % name)

  def is_started (self, name):
    """
    Return with the value the given domain manager is started or not.

    :param name: name of domain manager
    :type name: str
    :return: is loaded or not
    :rtype: bool
    """
    return name in self.__repository

  @property
  def components (self):
    """
    Return the dict of initiated Domain managers.

    :return: container of initiated DomainManagers
    :rtype: dict
    """
    return self.__repository

  @property
  def domains (self):
    """
    Return the list of domain_names which have been managed by DomainManagers.

    :return: list of already managed domains
    :rtype: list
    """
    return [mgr.domain_name for mgr in self.__repository.itervalues()]

  @property
  def initiated (self):
    return self.__repository.iterkeys()

  def get_component_by_domain (self, domain_name):
    """
    Return with the initiated Domain Manager configured with the given
    domain_name.

    :param domain_name: name of the domain used in :any:`NFFG` descriptions
    :type domain_name: str
    :return: the initiated domain Manager
    :rtype: any:`AbstractDomainManager`
    """
    for component in self.__repository.itervalues():
      if component.domain_name == domain_name:
        return component

  def __iter__ (self):
    """
    Return with an iterator over the (name, DomainManager) items.
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

  def load_component (self, component_name, parent=None):
    """
    Load given component (DomainAdapter/DomainManager) from config.
    Initiate the given component class, pass the additional attributes,
    register the event listeners and return with the newly created object.

    :param component_name: component's config name
    :type component_name: str
    :param parent: define the parent of the actual component's configuration
    :type parent: dict
    :return: initiated component
    :rtype: :any:`AbstractESCAPEAdapter` or :any:`AbstractDomainManager`
    """
    try:
      # Get component class
      component_class = CONFIG.get_component(component=component_name,
                                             parent=parent)
      # If it's found
      if component_class is not None:
        # Get optional parameters of this component
        params = CONFIG.get_component_params(component=component_name,
                                             parent=parent)
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
        raise ConfigurationError("Missing component configuration!")
    except AttributeError:
      log.error(
         "%s is not found. Skip component initialization!" % component_name)
      raise
    except ImportError:
      log.error(
         "Could not import module: %s. Skip component initialization!" %
         component_name)
      raise

  def load_default_mgrs (self):
    """
    Initiate and start default DomainManagers defined in CONFIG.

    :return: None
    """
    log.info("Initialize DomainManagers from config...")
    # very dummy initialization
    mgrs = CONFIG.get_managers()
    if not mgrs:
      log.info("No DomainManager has been configured!")
      return
    for mgr_name in mgrs:
      mgr_cfg = CONFIG.get_component_params(component=mgr_name)
      if 'domain_name' in mgr_cfg and mgr_cfg['domain_name'] in self.domains:
        log.warning(
           "Domain name collision: Domain Manager: %s has already initiated "
           "with the domain name: %s" % (
             self.get_component_by_domain(domain_name=mgr_cfg['domain_name']),
             mgr_cfg['domain_name']))
      log.debug("Init DomainManager based on config: %s" % mgr_name)
      self.start_mgr(name=mgr_name)

  def load_internal_mgr (self):
    """
    Initiate the DomainManager for the internal domain.

    :return: None
    """
    log.debug(
       "Init DomainManager for internally emulated network based on config: "
       "%s" % mgrs.InternalDomainManager.name)
    # Internal domain is hard coded with the name: INTERNAL
    self.start_mgr(name=mgrs.InternalDomainManager.name)

  def clear_initiated_mgrs (self):
    """
    Clear initiated DomainManagers based on the first received config.

    :return: None
    """
    log.info("Resetting detected domains before shutdown...")
    for name, mgr in self:
      try:
        mgr.clear_domain()
      except:
        log.error("Got exception during domain resetting!")
        traceback.print_exc()

  def stop_initiated_mgrs (self):
    """
    Stop initiated DomainManagers.

    :return: None
    """
    for name, mgr in self:
      log.debug("Shutdown %s DomainManager..." % name)
      try:
        self.stop_mgr(name=name)
      except:
        log.error("Got exception during domain resetting!")
        traceback.print_exc()
    # Do not del mgr in for loop because of the iterator use
    self.__repository.clear()


class ControllerAdapter(object):
  """
  Higher-level class for :any:`NFFG` adaptation between multiple domains.
  """

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
    try:
      if with_infr:
        # Init internal domain manager if Infrastructure Layer is started
        self.domains.load_internal_mgr()
      # Init default domain managers
      self.domains.load_default_mgrs()
    except (ImportError, AttributeError, ConfigurationError) as e:
      from escape.util.misc import quit_with_error
      quit_with_error(msg="Shutting down ESCAPEv2! Cause: %s" % e,
                      logger=log)
    # Here every domainManager is up and running
    # Notify the remote visualizer about collected data if it's needed
    notify_remote_visualizer(
       data=self.domainResManager.get_global_view().get_resource_info(),
       id=LAYER_NAME)

  def shutdown (self):
    """
    Shutdown ControllerAdapter, related components and stop DomainManagers.

    :return: None
    """
    # Clear DomainManagers config if needed
    if CONFIG.clear_domains_after_shutdown() is True:
      self.domains.clear_initiated_mgrs()
    # Stop initiated DomainManagers
    self.domains.stop_initiated_mgrs()

  @staticmethod
  def _split_into_domains (nffg):
    """
    Split given :any:`NFFG` into separate parts self._global_nffg on
    original domains.

    .. warning::
      Not implemented yet!

    :param nffg: mapped NFFG object
    :type nffg: NFFG
    :return: sliced parts as a list of (domain_name, nffg_part) tuples
    :rtype: list
    """
    # with open('pox/merged-global.nffg', 'r') as f:
    #   nffg = NFFG.parse(f.read())
    splitted_parts = []

    log.info("Splitting mapped NFFG: %s according to detected domains" % nffg)
    # Define DOMAIN names
    domains = set()
    for infra in nffg.infras:
      domains.add(infra.domain)
    log.debug("Detected domains for splitting: %s" % domains)

    if len(domains) == 0:
      log.warning("No domain has been detected!")
      return

    # Checks every domain
    for domain in domains:
      log.info("Create slice for domain: %s" % domain)
      # Collect every node which not in the domain
      deletable = set()
      for infra in nffg.infras:
        # Domains representations based on infras
        if infra.domain == domain:
          # Skip current domains infra
          continue
        # Mark the infra as deletable
        deletable.add(infra.id)
        # Look for orphan NF ans SAP nodes which connected to this deletable
        # infra
        for u, v, link in nffg.network.out_edges_iter([infra.id], data=True):
          # Skip Requirement and SG links
          if link.type != NFFG.TYPE_LINK_STATIC and link.type != \
             NFFG.TYPE_LINK_DYNAMIC:
            continue
          if nffg.network.node[v].type == NFFG.TYPE_NF or nffg.network.node[
            v].type == NFFG.TYPE_SAP:
            deletable.add(v)
      log.debug("Nodes marked for deletion: %s" % deletable)

      log.debug("Clone NFFG...")
      # Copy the NFFG
      nffg_part = nffg.copy()
      # Set metadata
      nffg_part.id = domain
      nffg_part.name = domain + "-splitted"
      # Delete needless nodes --> and as a side effect the connected links too
      log.debug("Delete marked nodes...")
      nffg_part.network.remove_nodes_from(deletable)
      log.debug("Remained nodes: %s" % [n for n in nffg_part])
      splitted_parts.append((domain, nffg_part))

      log.debug(
         "Search for inter-domain SAP ports and recreate associated SAPs...")
      # Recreate inter-domain SAP
      for infra in nffg_part.infras:
        for port in infra.ports:
          # Check ports of remained Infra's for SAP ports
          if "type:inter-domain" in port.properties:
            # Found inter-domain SAP port
            log.debug("Found inter-domain SAP port: %s" % port)
            # Create default SAP object attributes
            sap_id, sap_name = None, None
            # Copy optional SAP metadata as special id or name
            for property in port.properties:
              if str(property).startswith("sap:"):
                sap_id = property.split(":", 1)[1]
              if str(property).startswith("name:"):
                sap_name = property.split(":", 1)[1]
            # Add SAP to splitted NFFG
            if sap_id in nffg_part:
              log.warning("%s is already in the splitted NFFG. Skip adding..." %
                          nffg_part[sap_id])
              continue
            sap = nffg_part.add_sap(id=sap_id, name=sap_name)
            # Add port to SAP port number(id) is identical with the Infra's port
            sap_port = sap.add_port(id=port.id, properties=port.properties[:])
            # Connect SAP to Infra
            nffg_part.add_undirected_link(port1=port, port2=sap_port)
            log.debug(
               "Add inter-domain SAP: %s with port: %s" % (sap, sap_port))

      # Check orphaned or not connected nodes and remove them
      for node_id in nffg_part.network.nodes():
        if len(nffg_part.network.neighbors(node_id)) > 0:
          continue
        log.warning("Found orphaned node: %s! Remove from sliced part." %
                    nffg_part.network.node[node_id])
        nffg_part.network.remove_node(node_id)

    # Return with the splitted parts
    # for s in splitted_parts:
    #   print s[0], s[1].dump()
    return splitted_parts

  def install_nffg (self, mapped_nffg):
    """
    Start NF-FG installation.

    Process given :any:`NFFG`, slice information self.__global_nffg on
    domains an invoke
    DomainManagers to install domain specific parts.

    :param mapped_nffg: mapped NF-FG instance which need to be installed
    :type mapped_nffg: NFFG
    :return: None or internal domain NFFG part
    """
    log.debug("Invoke %s to install NF-FG(%s)" % (
      self.__class__.__name__, mapped_nffg.name))
    # # Notify remote visualizer about the deployable NFFG if it's needed
    # notify_remote_visualizer(data=mapped_nffg, id=LAYER_NAME)
    print mapped_nffg.dump()
    slices = self._split_into_domains(nffg=mapped_nffg)
    if slices is None:
      log.warning(
         "Given mapped NFFG: %s can not be sliced! Skip domain notification "
         "steps" % mapped_nffg)
      return
    log.debug(
       "Notify initiated domains: %s" % [d for d in self.domains.initiated])
    # TODO - end-to-end requirement recreation
    # TODO - abstract/inter-domain tag rewrite
    mapping_result = True
    for domain, part in slices:
      domain_mgr = self.domains.get_component_by_domain(domain_name=domain)
      if domain_mgr is None:
        log.warning(
           "No DomainManager has been initialized for domain: %s! Skip install "
           "domain part..." % domain)
        continue
      log.debug("Delegate splitted part: %s to %s" % (part, domain_mgr))
      # Check if need to reset domain before install
      reset = CONFIG.reset_domains_before_install()
      if reset:
        log.info(
           "Reset %s domain before deploying mapped NFFG..." %
           domain_mgr.domain_name)
        domain_mgr.clear_domain()
      # Invoke DomainAdapter's install
      res = domain_mgr.install_nffg(part)
      if not res:
        log.warning(
           "Installation of %s in %s was unsuccessful!" % (part, domain))
      # Note result according to others before
      mapping_result = mapping_result and res
    log.debug("NF-FG installation is finished by %s" % self.__class__.__name__)
    # FIXME - hardcoded, you can do it better
    if mapping_result:
      log.info("All installation process has been finished with success! ")
      log.debug(
         "Update Global view (DoV) with the mapped NFFG: %s..." % mapped_nffg)
      # Update global view (DoV) with the installed components
      self.domainResManager.get_global_view().update_global_view(mapped_nffg)
      # Notify remote visualizer about the installation result if it's needed
      notify_remote_visualizer(
         data=self.domainResManager.get_global_view().get_resource_info(),
         id=LAYER_NAME)
    else:
      log.error("%s installation was not successful!" % mapped_nffg)
    return mapping_result

  def _handle_DomainChangedEvent (self, event):
    """
    Handle DomainChangedEvents, process changes and store relevant information
    in DomainResourceManager.
    """
    log.info("Received DomainChange event from domain: %s, cause: %s" % (
      event.domain, DomainChangedEvent.TYPE.reversed[event.cause]))
    if event.data is not None and isinstance(event.data, NFFG):
      self.domainResManager.update_domain_resource(nffg=event.data,
                                                   domain=event.domain)

  def update_dov (self, nffg_part):
    """
    Update the global view with installed Nfs/Flowrules.

    :param nffg_part: nffg part need to be updated with
    :type: :any:`NFFG`
    """
    pass


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
    self._global_nffg = None
    if global_res is not None:
      self.set_domain_as_global_view(domain=NFFG.DEFAULT_DOMAIN,
                                     nffg=global_res)

  @property
  def name (self):
    if self._global_nffg is not None and hasattr(self._global_nffg, 'name'):
      return self._global_nffg.name
    else:
      return DoV + "-uninitialized"

  def __str__ (self):
    return "DomainVirtualizer(name=%s)" % self.name

  def __repr__ (self):
    return super(DomainVirtualizer, self).__repr__()

  def get_resource_info (self):
    """
    Return the global resource info represented this class.

    :return: global resource info
    :rtype: :any:`NFFG`
    """
    return self._global_nffg

  def set_domain_as_global_view (self, domain, nffg):
    """
    Set the copy of given NFFG as the global view of DoV.

    :param nffg: NFFG instance intended to use as the global view
    :type nffg: :any:`NFFG`
    :param domain: name of the merging domain
    :type domain: str
    :return: None
    """
    log.debug("Set domain: %s as the global view!" % domain)
    self._global_nffg = nffg.copy()
    self._global_nffg.name = "dov-" + self._global_nffg.generate_id()
    self._global_nffg.id = DoV

  def merge_domain_into_dov (self, nffg, domain):
    """
    Add a newly detected domain to DoV.

    Based on the feature: escape.util.nffg.NFFGToolBox#merge_domains

    :param nffg: NFFG object need to be merged into DoV
    :type nffg: :any:`NFFG`
    :param domain: name of the merging domain
    :type domain: str
    :return: Dov
    :rtype: :any:`NFFG`
    """
    from copy import deepcopy

    # Copy infras
    log.debug("Merge domain: %s resource info into DoV..." % domain)

    for infra in nffg.infras:
      if infra.id not in self._global_nffg:
        c_infra = self._global_nffg.add_infra(infra=deepcopy(infra))
        log.debug("Copy infra node: %s" % c_infra)
      else:
        log.warning(
           "Infra node: %s does already exist in DoV. Skip adding..." % infra)

    # Copy NFs
    for nf in nffg.nfs:
      if nf.id not in self._global_nffg:
        c_nf = self._global_nffg.add_nf(nf=deepcopy(nf))
        log.debug("Copy NF node: %s" % c_nf)
      else:
        log.warning(
           "NF node: %s does already exist in DoV. Skip adding..." % nf)

    # Copy SAPs
    for sap_id in [s.id for s in nffg.saps]:
      if sap_id in [s.id for s in self._global_nffg.saps]:
        # Found inter-domain SAP
        log.debug("Found Inter-domain SAP: %s" % sap_id)
        # Search outgoing links from SAP, should be only one
        b_links = [l for u, v, l in
                   self._global_nffg.network.out_edges_iter([sap_id],
                                                            data=True)]
        if len(b_links) < 1:
          log.warning(
             "SAP is not connected to any node! Maybe you forgot to call "
             "duplicate_static_links?")
          return
        if 2 < len(b_links):
          log.warning(
             "Inter-domain SAP should have one and only one connection to the "
             "domain! Using only the first connection.")
          continue

        # Get inter-domain port in self._global_nffg NFFG
        domain_port_dov = b_links[0].dst
        log.debug("Found inter-domain port: %s" % domain_port_dov)
        # Search outgoing links from SAP, should be only one
        n_links = [l for u, v, l in
                   nffg.network.out_edges_iter([sap_id], data=True)]

        if len(n_links) < 1:
          log.warning(
             "SAP is not connected to any node! Maybe you forgot to call "
             "duplicate_static_links?")
          return
        if 2 < len(n_links):
          log.warning(
             "Inter-domain SAP should have one and only one connection to the "
             "domain! Using only the first connection.")
          continue

        # Get port and Infra id's in nffg NFFG
        p_id = n_links[0].dst.id
        n_id = n_links[0].dst.node.id
        # Get the inter-domain port from already copied Infra
        domain_port_nffg = self._global_nffg.network.node[n_id].ports[p_id]
        log.debug("Found inter-domain port: %s" % domain_port_nffg)

        # Copy inter-domain port properties for redundant storing
        # FIXME - do it better
        if len(domain_port_nffg.properties) > 0:
          domain_port_dov.properties.update(domain_port_nffg.properties)
          log.debug(
             "Copy inter-domain port properties: %s" %
             domain_port_dov.properties)
        elif len(domain_port_dov.properties) > 0:
          domain_port_nffg.properties.update(domain_port_dov.properties)
          log.debug(
             "Copy inter-domain port properties: %s" %
             domain_port_nffg.properties)
        else:
          domain_port_dov.add_property("sap", sap_id)
          domain_port_nffg.add_property("sap", sap_id)

        # Signal Inter-domain port
        domain_port_dov.add_property("type", "inter-domain")
        domain_port_nffg.add_property("type", "inter-domain")

        # Delete both inter-domain SAP and links connected to them
        self._global_nffg.del_node(sap_id)
        nffg.del_node(sap_id)
        log.debug(
           "Add inter-domain connection with delay: %s, bandwidth: %s" % (
             b_links[0].delay, b_links[0].bandwidth))

        # Add the inter-domain links for both ways
        self._global_nffg.add_undirected_link(
           p1p2id="inter-domain-link-%s" % sap_id,
           p2p1id="inter-domain-link-%s-back" % sap_id,
           port1=domain_port_dov,
           port2=domain_port_nffg,
           delay=b_links[0].delay,
           bandwidth=b_links[0].bandwidth)
      else:
        # Normal SAP --> copy SAP
        c_sap = self._global_nffg.add_sap(
           sap=deepcopy(nffg.network.node[sap_id]))
        log.debug("Copy SAP: %s" % c_sap)

    # Copy remaining links which should be valid
    for u, v, link in nffg.network.edges_iter(data=True):
      src_port = self._global_nffg.network.node[u].ports[link.src.id]
      dst_port = self._global_nffg.network.node[v].ports[link.dst.id]
      c_link = deepcopy(link)
      c_link.src = src_port
      c_link.dst = dst_port
      self._global_nffg.add_link(src_port=src_port, dst_port=dst_port,
                                 link=c_link)
      log.debug("Copy Link: %s" % c_link)
    # print self._global_nffg.dump()
    # from pprint import pprint
    # pprint(self._global_nffg.network.__dict__)

    # Return the updated NFFG
    return self._global_nffg

  def update_global_view (self, global_nffg):
    """
    Update the merged Global view with the given probably modified global view.

    :param global_nffg: updated global view which replace the stored one
    :type global_nffg: :any:`NFFG`
    """
    self._global_nffg = global_nffg.copy()
    self._global_nffg.name = "dov-" + self._global_nffg.generate_id()
    self._global_nffg.id = DoV

  def update_domain_view (self, domain, nffg):
    """
    Update the existing domain in the merged Global view.

    :param nffg: NFFG object need to be updated with
    :type nffg: :any:`NFFG`
    :param domain: name of the merging domain
    :type domain: str
    """
    # TODO
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
    self._dov = DomainVirtualizer(self)  # Domain Virtualizer
    # with open('pox/dov.nffg', 'r') as f:
    #   nffg = NFFG.parse(f.read())
    # self._dov = DomainVirtualizer(self, global_res=nffg)  # Domain Virtualizer
    self._tracked_domains = set()  # Cache for detected and stored domains

  def get_global_view (self):
    """
    Getter for :class:`DomainVirtualizer`.

    :return: global infrastructure view as the Domain Virtualizer
    :rtype: :any:`DomainVirtualizer`
    """
    return self._dov

  def update_domain_resource (self, domain, nffg):
    """
    Update the global view data with the specific domain info.

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
        self._dov.merge_domain_into_dov(nffg=nffg, domain=domain)
      else:
        # No other domain detected, set NFFG as the whole global view
        log.debug(
           "DoV is empty! Add new domain: %s as the global view!" % domain)
        self._dov.set_domain_as_global_view(domain=domain, nffg=nffg)
      # Add detected domain to cached domains
      self._tracked_domains.add(domain)
    else:
      log.info("Updating <Global Resource View> from %s domain..." % domain)
      # FIXME - only support INTERNAL domain ---> extend & improve !!!
      if domain == 'INTERNAL':
        self._dov.update_domain_view(domain=domain, nffg=nffg)
        # FIXME - SIGCOMM
        # print self.__dov.get_resource_info().dump()
