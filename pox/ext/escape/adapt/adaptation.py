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
from escape.nffg_lib.nffg import NFFG, NFFGToolBox
from escape.orchest.virtualization_mgmt import AbstractVirtualizer
from escape.util.config import ConfigurationError
from escape.util.domain import DomainChangedEvent
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
        log.exception("Got exception during domain resetting!")

  def stop_initiated_mgrs (self):
    """
    Stop initiated DomainManagers.

    :return: None
    """
    log.debug("Shutdown DomainManagers...")
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
        self.domains.load_internal_mgr()
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
    :return: None or internal domain NFFG part
    """
    log.debug("Invoke %s to install NF-FG(%s)" % (
      self.__class__.__name__, mapped_nffg.name))
    # # Notify remote visualizer about the deployable NFFG if it's needed
    # notify_remote_visualizer(data=mapped_nffg, id=LAYER_NAME)
    # print mapped_nffg.dump()
    slices = NFFGToolBox.split_into_domains(nffg=mapped_nffg, log=log)
    if slices is None:
      log.warning(
        "Given mapped NFFG: %s can not be sliced! Skip domain notification "
        "steps" % mapped_nffg)
      return
    log.debug(
      "Notify initiated domains: %s" % [d for d in self.domains.initiated])
    # TODO - abstract/inter-domain tag rewrite
    mapping_result = True
    for domain, part in slices:
      # Rebind requirement link fragments as e2e reqs
      part = NFFGToolBox.rebind_e2e_req_links(nffg=part, log=log)
      # Get Domain Manager
      domain_mgr = self.domains.get_component_by_domain(domain_name=domain)
      if domain_mgr is None:
        log.warning(
          "No DomainManager has been initialized for domain: %s! Skip install "
          "domain part..." % domain)
        continue
      log.log(VERBOSE,
              "Splitted domain: %s part:\n%s" % (domain, part.dump()))
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
      self.DoVManager.dov.update_full_global_view(
        mapped_nffg)
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
    log.info("Received DomainChange event from domain: %s, cause: %s"
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


# Common reference name for the DomainVirtualizer
DoV = "DoV"


class DomainVirtualizer(AbstractVirtualizer):
  """
  Specific Virtualizer class for global domain virtualization.

  Implement the same interface as :class:`AbstractVirtualizer
  <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`

  Use :any:`NFFG` format to store the global infrastructure info.
  """

  def __init__ (self, mgr, global_res=None):
    """
    Init.

    :param mgr: global domain resource manager
    :type mgr: :any:`GlobalResourceManager`
    :param global_res: initial global resource (optional)
    :type global_res: :any:`NFFG`
    :return: None
    """
    super(DomainVirtualizer, self).__init__(id=None,
                                            type=self.DOMAIN_VIRTUALIZER)
    log.debug("Init DomainVirtualizer with name: %s - initial resource: %s" % (
      DoV, global_res))
    # Garbage-collector safe
    self._mgr = weakref.proxy(mgr)
    # Define DoV az an empty NFFG by default
    self.__global_nffg = NFFG(id=DoV, name=DoV + "-uninitialized")
    if global_res is not None:
      self.set_domain_as_global_view(domain=NFFG.DEFAULT_DOMAIN,
                                     nffg=global_res)

  @property
  def name (self):
    if self.__global_nffg is not None and hasattr(self.__global_nffg, 'name'):
      return self.__global_nffg.name
    else:
      return DoV + "-uninitialized"

  def __str__ (self):
    return "DomainVirtualizer(name=%s)" % self.name

  def __repr__ (self):
    return super(DomainVirtualizer, self).__repr__()

  def is_empty (self):
    """
    Return True if the stored topology is empty.

    :return: topology is empty or not
    :rtype: bool
    """
    # If Dov has not been set yet
    if self.__global_nffg is None:
      return True
    # If Dov does not contain any Node
    elif self.__global_nffg.is_empty():
      return True
    else:
      return False

  def get_resource_info (self):
    """
    Return the global resource info represented this class.

    :return: global resource info
    :rtype: :any:`NFFG`
    """
    return self.__global_nffg

  def set_domain_as_global_view (self, domain, nffg):
    """
    Set the copy of given NFFG as the global view of DoV.

    Add the specific :attr:`DoV` id and generated name to the global view.

    :param nffg: NFFG instance intended to use as the global view
    :type nffg: :any:`NFFG`
    :param domain: name of the merging domain
    :type domain: str
    :return: updated Dov
    :rtype: :any:`NFFG`
    """
    log.debug("Set domain: %s as the global view!" % domain)
    self.__global_nffg = nffg.copy()
    self.__global_nffg.id = DoV
    self.__global_nffg.name = "dov-" + self.__global_nffg.generate_id()
    return self.__global_nffg

  def update_full_global_view (self, nffg):
    """
    Update the merged Global view with the given probably modified global view.

    Reserve id, name values of the global view.

    :param nffg: updated global view which replace the stored one
    :type nffg: :any:`NFFG`
    :return: updated Dov
    :rtype: :any:`NFFG`
    """
    id, name = self.__global_nffg.id, self.__global_nffg.name
    self.__global_nffg = nffg.copy()
    self.__global_nffg.id, self.__global_nffg.name = id, name
    return self.__global_nffg

  def merge_new_domain_into_dov (self, nffg):
    """
    Add a newly detected domain to DoV.

    Based on the feature: escape.util.nffg.NFFGToolBox#merge_domains

    :param nffg: NFFG object need to be merged into DoV
    :type nffg: :any:`NFFG`
    :return: updated Dov
    :rtype: :any:`NFFG`
    """
    # Using general merging function from NFFGToolBox and return the updated
    # NFFG
    return NFFGToolBox.merge_new_domain(base=self.__global_nffg,
                                        nffg=nffg,
                                        log=log)

  def update_domain_in_dov (self, domain, nffg):
    """
    Update the existing domain in the merged Global view.

    :param nffg: NFFG object need to be updated with
    :type nffg: :any:`NFFG`
    :param domain: name of the merging domain
    :type domain: str
    :return: updated Dov
    :rtype: :any:`NFFG`
    """
    ret = NFFGToolBox.update(base=self.__global_nffg,
                             nffg=nffg,
                             log=log)
    if self.__global_nffg.is_empty():
      log.warning("No Node had been remained after updating the domain part: "
                  "%s! DoV is empty!" % domain)
    return ret

  def remove_domain_from_dov (self, domain):
    """
    Remove the nodes and edges with the given from Global view.

    :param domain: domain name
    :type domain: str
    :return: updated Dov
    :rtype: :any:`NFFG`
    """
    ret = NFFGToolBox.remove_domain(base=self.__global_nffg,
                                    domain=domain,
                                    log=log)
    if self.__global_nffg.is_empty():
      log.warning("No Node had been remained after updating the domain part: "
                  "%s! DoV is empty!" % domain)
    return ret


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
