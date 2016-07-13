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

import escape.adapt.managers as mgrs
from escape import CONFIG
from escape.adapt import log as log, LAYER_NAME
from escape.adapt.virtualization import DomainVirtualizer
from escape.nffg_lib.nffg import NFFG, NFFGToolBox
from escape.util.config import ConfigurationError
from escape.util.domain import DomainChangedEvent, AbstractRemoteDomainManager
from escape.util.misc import notify_remote_visualizer, VERBOSE


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
      Adapter classes must be subclass of AbstractESCAPEAdapter!

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

  def __len__ (self):
    """
    Return the number of initiated components.

    :return: number of initiated components:
    :rtype: int
    """
    return len(self.__repository)

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

  def start_mgr (self, name, mgr_params=None, autostart=True):
    """
    Create, initialize and start a DomainManager with given name and start
    the manager by default.

    :param name: name of domain manager
    :type name: str
    :param mgr_params: mgr parameters
    :type mgr_params: dict
    :param autostart: also start the domain manager (default: True)
    :type autostart: bool
    :return: domain manager
    :rtype: :any:`AbstractDomainManager`
    """
    # If not started
    if not self.is_started(name):
      # Load from CONFIG
      mgr = self.load_component(name, params=mgr_params)
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

  def load_component (self, component_name, params=None, parent=None):
    """
    Load given component (DomainAdapter/DomainManager) from config.
    Initiate the given component class, pass the additional attributes,
    register the event listeners and return with the newly created object.

    :param component_name: component's config name
    :type component_name: str
    :param params: component parameters
    :type params: dict
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
        if not params:
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
        log.error("Configuration of '%s' is missing. Skip initialization!" %
                  component_name)
        raise ConfigurationError("Missing component configuration!")
    except AttributeError:
      log.error("%s is not found. Skip component initialization!" %
                component_name)
      raise
    except ImportError:
      log.error("Could not import module: %s. Skip component initialization!" %
                component_name)
      raise

  def load_default_mgrs (self):
    """
    Initiate and start default DomainManagers defined in CONFIG.

    :return: None
    """
    log.info("Initialize additional DomainManagers from config...")
    # very dummy initialization
    mgrs = CONFIG.get_managers()
    if not mgrs:
      log.info("No DomainManager has been configured!")
      return
    for mgr_name in mgrs:
      # Get manager parameters from config
      mgr_cfg = CONFIG.get_component_params(component=mgr_name)
      if 'domain_name' in mgr_cfg:
        if mgr_cfg['domain_name'] in self.domains:
          log.warning("Domain name collision! Domain Manager: %s has already "
                      "initiated with the domain name: %s" % (
                        self.get_component_by_domain(
                          domain_name=mgr_cfg['domain_name']),
                        mgr_cfg['domain_name']))
      else:
        # If no domain name was given, use the manager config name by default
        mgr_cfg['domain_name'] = mgr_name
      # Get manager class
      mgr_class = CONFIG.get_component(component=mgr_name)
      if mgr_class.IS_LOCAL_MANAGER:
        loaded_local_mgr = [name for name, mgr in self.__repository.iteritems()
                            if mgr.IS_LOCAL_MANAGER]
        if loaded_local_mgr:
          log.warning("A local DomainManager has already been initiated with "
                      "the name: %s! Skip initiating DomainManager: %s" %
                      (loaded_local_mgr, mgr_name))
          return
      log.debug("Load DomainManager based on config: %s" % mgr_name)
      # Start domain manager
      self.start_mgr(name=mgr_name, mgr_params=mgr_cfg)

  def load_local_domain_mgr (self):
    """
    Initiate the DomainManager for the internal domain.

    :return: None
    """
    loaded_local_mgr = [name for name, mgr in self.__repository.iteritems() if
                        mgr.IS_LOCAL_MANAGER]
    if loaded_local_mgr:
      log.warning("A local DomainManager has already been initiated with the "
                  "name: %s! Skip initiation of default local DomainManager: %s"
                  % (loaded_local_mgr, mgrs.InternalDomainManager.name))
      return
    log.debug("Init DomainManager for local domain based on config: %s" %
              mgrs.InternalDomainManager.name)
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
        log.exception("Got exception during domain resetting!")

  def stop_initiated_mgrs (self):
    """
    Stop initiated DomainManagers.

    :return: None
    """
    log.info("Shutdown initiated DomainManagers...")
    for name, mgr in self:
      try:
        self.stop_mgr(name=name)
      except:
        log.exception("Got exception during domain resetting!")
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
    self.DoVManager = GlobalResourceManager()
    self.domains = ComponentConfigurator(self)
    try:
      if with_infr:
        # Init internal domain manager if Infrastructure Layer is started
        self.domains.load_local_domain_mgr()
      # Init default domain managers
      self.domains.load_default_mgrs()
    except (ImportError, AttributeError, ConfigurationError) as e:
      from escape.util.misc import quit_with_error
      quit_with_error(msg="Shutting down ESCAPEv2 due to an unexpected error!",
                      logger=log, exception=e)
    # Here every domainManager is up and running
    # Notify the remote visualizer about collected data if it's needed
    notify_remote_visualizer(
      data=self.DoVManager.dov.get_resource_info(),
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

  def install_nffg (self, mapped_nffg):
    """
    Start NF-FG installation.

    Process given :any:`NFFG`, slice information self.__global_nffg on
    domains and invoke DomainManagers to install domain specific parts.

    :param mapped_nffg: mapped NF-FG instance which need to be installed
    :type mapped_nffg: NFFG
    :return: mapping result
    :rtype: bool
    """
    log.debug("Invoke %s to install NF-FG(%s)" % (
      self.__class__.__name__, mapped_nffg.name))
    # # Notify remote visualizer about the deployable NFFG if it's needed
    # notify_remote_visualizer(data=mapped_nffg, id=LAYER_NAME)
    slices = NFFGToolBox.split_into_domains(nffg=mapped_nffg, log=log)
    if slices is None:
      log.warning("Given mapped NFFG: %s can not be sliced! "
                  "Skip domain notification steps" % mapped_nffg)
      return
    log.debug("Notify initiated domains: %s" %
              [d for d in self.domains.initiated])
    # TODO - abstract/inter-domain tag rewrite
    # NFFGToolBox.rewrite_interdomain_tags(slices)
    mapping_result = True
    for domain, part in slices:
      log.debug(
        "Recreate missing TAG matching fields in domain part: %s..." % domain)
      # Temporarily rewrite/recreate TAGs here
      NFFGToolBox.recreate_match_TAGs(nffg=part, log=log)
      # Get Domain Manager
      domain_mgr = self.domains.get_component_by_domain(domain_name=domain)
      if domain_mgr is None:
        log.warning("No DomainManager has been initialized for domain: %s! "
                    "Skip install domain part..." % domain)
        continue
      log.log(VERBOSE, "Splitted domain: %s part:\n%s" % (domain, part.dump()))
      log.info("Delegate splitted part: %s to %s" % (part, domain_mgr))
      # Rebind requirement link fragments as e2e reqs
      part = NFFGToolBox.rebind_e2e_req_links(nffg=part, log=log)
      # Check if need to reset domain before install
      if CONFIG.reset_domains_before_install():
        log.debug("Reset %s domain before deploying mapped NFFG..." %
                  domain_mgr.domain_name)
        domain_mgr.clear_domain()
      # Invoke DomainAdapter's install
      res = domain_mgr.install_nffg(part)
      # Update the DoV based on the mapping result covering some corner case
      if not res:
        log.error("Installation of %s in %s was unsuccessful!" %
                  (part, domain))
      # Note result according to others before
      mapping_result = mapping_result and res
      # If installation of the domain was performed without error
      if not res:
        log.warning("Skip DoV update with domain: %s! Cause: "
                    "Domain installation was unsuccessful!" % domain)
        continue
      # If the domain manager does not poll the domain update here
      # else polling takes care of domain updating
      if isinstance(domain_mgr,
                    AbstractRemoteDomainManager) and domain_mgr._poll:
        log.info("Skip explicit DoV update for domain: %s. "
                 "Cause: polling enabled!" % domain)
        continue
      # If the internalDM is the only initiated mgr, we can override the
      # whole DoV
      if domain_mgr.IS_LOCAL_MANAGER:
        if mapped_nffg.is_SBB():
          # If the request was a cleanup request, we can simply clean the DOV
          if mapped_nffg.is_bare():
            log.debug(
              "Detected cleanup topology (no NF/Flowrule/SG_hop)! Clean DoV...")
            self.DoVManager.clean_domain(domain=domain)
          # If the reset contains some VNF, cannot clean or override
          else:
            log.warning(
              "Detected SingleBiSBiS topology! Local domain has been already "
              "cleared, skip DoV update...")
        # If the the topology was a GLOBAL view, just override the whole DoV
        elif not mapped_nffg.is_virtualized():
          self.DoVManager.set_global_view(nffg=mapped_nffg)
        else:
          log.warning(
            "Detected virtualized Infrastructure node in mapped NFFG! Skip "
            "DoV update...")
        # In case of Local manager skip the rest of the update
        continue
      # Explicit domain update
      self.DoVManager.update_domain(domain=domain, nffg=part)
    log.debug("NF-FG installation is finished by %s" % self.__class__.__name__)
    # Post-mapping steps
    if mapping_result:
      log.info("All installation process has been finished with success! ")
      # Notify remote visualizer about the installation result if it's needed
      notify_remote_visualizer(
        data=self.DoVManager.dov.get_resource_info(),
        id=LAYER_NAME)
    else:
      log.error("%s installation was not successful!" % mapped_nffg)
    return mapping_result

  def _handle_DomainChangedEvent (self, event):
    """
    Handle DomainChangedEvents, dispatch event according to the cause to
    store and enfore changes into DoV.

    :param event: event object
    :type event: :any:`DomainChangedEvent`
    :return: None
    """
    log.debug("Received DomainChange event from domain: %s, cause: %s"
              % (event.domain, DomainChangedEvent.TYPE.reversed[event.cause]))
    # If new domain detected
    if event.cause == DomainChangedEvent.TYPE.DOMAIN_UP:
      self.DoVManager.add_domain(domain=event.domain,
                                 nffg=event.data)
    # If domain has changed
    elif event.cause == DomainChangedEvent.TYPE.DOMAIN_CHANGED:
      self.DoVManager.update_domain(domain=event.domain,
                                    nffg=event.data)
    # If domain has got down
    elif event.cause == DomainChangedEvent.TYPE.DOMAIN_DOWN:
      self.DoVManager.remove_domain(domain=event.domain)


class GlobalResourceManager(object):
  """
  Handle and store the global resources view as known as the DoV.
  """

  def __init__ (self):
    """
    Init.
    """
    super(GlobalResourceManager, self).__init__()
    log.debug("Init DomainResourceManager")
    self.__dov = DomainVirtualizer(self)  # Domain Virtualizer
    self.__tracked_domains = set()  # Cache for detected and stored domains
    self._remerge = CONFIG.use_remerge_update_strategy()

  @property
  def dov (self):
    """
    Getter for :class:`DomainVirtualizer`.

    :return: global infrastructure view as the Domain Virtualizer
    :rtype: :any:`DomainVirtualizer`
    """
    return self.__dov

  @property
  def tracked (self):
    """
    Getter for tuple of detected domains.

    :return: detected domains
    :rtype: tuple
    """
    return tuple(self.tracked)

  def set_global_view (self, nffg):
    """
    Replace the global view with the given topology.

    :param nffg: new global topology
    :type nffg: :any:`NFFG`
    :return: None
    """
    log.debug("Update the whole Global view (DoV) with the NFFG: %s..." % nffg)
    self.dov.update_full_global_view(nffg=nffg)
    self.__tracked_domains.clear()
    self.__tracked_domains.update(NFFGToolBox.detect_domains(nffg))

  def add_domain (self, domain, nffg):
    """
    Update the global view data with the specific domain info.

    :param domain: domain name
    :type domain: str
    :param nffg: infrastructure info collected from the domain
    :type nffg: :any:`NFFG`
    :return: None
    """
    # If the domain is not tracked
    if domain not in self.__tracked_domains:
      if not nffg:
        log.warning("Got empty data. Skip domain addition...")
        return
      log.info("Append %s domain to DoV..." % domain)
      # If DoV is empty
      if not self.__dov.is_empty():
        # Merge domain topo into global view
        self.__dov.merge_new_domain_into_dov(nffg=nffg)
      else:
        # No other domain detected, set NFFG as the whole Global view
        log.debug(
          "DoV is empty! Add new domain: %s as the global view!" % domain)
        self.__dov.set_domain_as_global_view(domain=domain, nffg=nffg)
      # Add detected domain to cached domains
      self.__tracked_domains.add(domain)
    else:
      log.error("New domain: %s has already tracked: %s! Abort adding..."
                % (domain, self.__tracked_domains))

  def update_domain (self, domain, nffg):
    """
    Update the detected domain in the global view with the given info.

    :param domain: domain name
    :type domain: str
    :param nffg: changed infrastructure info
    :type nffg: :any:`NFFG`
    :return: None
    """
    if domain in self.__tracked_domains:
      log.info("Update domain: %s in DoV..." % domain)
      if self._remerge:
        log.debug("Using REMERGE strategy for DoV update...")
        self.__dov.remerge_domain_in_dov(domain=domain, nffg=nffg)
      else:
        log.debug("Using UPDATE strategy for DoV update...")
        self.__dov.update_domain_in_dov(domain=domain, nffg=nffg)
    else:
      log.error(
        "Detected domain: %s is not included in tracked domains: %s! Abort "
        "updating..." % (domain, self.__tracked_domains))

  def remove_domain (self, domain):
    """
    Remove the detected domain from the global view.

    :param domain: domain name
    :type domain: str
    :return: None
    """
    if domain in self.__tracked_domains:
      log.info("Remove domain: %s from DoV..." % domain)
      self.__dov.remove_domain_from_dov(domain=domain)
      self.__tracked_domains.remove(domain)
    else:
      log.warning("Removing domain: %s is not included in tracked domains: %s! "
                  "Skip removing..." % (domain, self.__tracked_domains))

  def clean_domain (self, domain):
    """
    Clean given domain.

    :param domain: domain name
    :type domain: str
    :return: None
    """
    if domain in self.__tracked_domains:
      log.info(
        "Remove initiated VNFs and flowrules from the domain: %s" % domain)
      self.__dov.clean_domain_from_dov(domain=domain)
    else:
      log.error(
        "Detected domain: %s is not included in tracked domains: %s! Abort "
        "cleaning..." % (domain, self.__tracked_domains))
