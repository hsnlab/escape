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
      Adapter classes must be subclass of AbstractDomainAdapter

    .. note::
      Arbitrary domain adapters is searched in
      :mod:`escape.adapt.domain_adapters`

    :param ca: ControllerAdapter instance
    :type ca: :any:`ControllerAdapter`
    :param lazy_load: load adapters only at first reference (default: True)
    :type lazy_load: bool
    """
    log.debug("Init DomainConfigurator")
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

  def __iter__ (self):
    """
    Return with an iterator rely on initiated DomainManagers.
    """
    return self.__repository.iteritems()

  # Configuration related functions

  def load_component (self, component_name):
    """
    Load given component (DomainAdapter/DomainManager) from config.
    Initiate the given component class, pass the additional attributes,
    register the event listeners and return with the newly created object.

    :param component_name: component's name
    :type component_name: str
    :return: initiated component
    :rtype: :any:`AbstractDomainAdapter` or :any:`AbstractDomainManager`
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
      self.start_mgr(mgr)

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

  def __init__ (self, layer_API, with_infr=False):
    """
    Initialize Controller adapter.

    For domain components the ControllerAdapter checks the CONFIG first.

    :param layer_API: layer API instance
    :type layer_API: :any:`ControllerAdaptationAPI`
    :param with_infr: using emulated infrastructure (default: False)
    :type with_infr: bool
    """
    log.debug("Init ControllerAdapter")
    super(ControllerAdapter, self).__init__()
    # Set a weak reference to avoid circular dependencies
    self._layer_API = weakref.proxy(layer_API)
    self._with_infr = with_infr
    # Set virtualizer-related components
    self.domainResManager = DomainResourceManager()
    self.domains = ComponentConfigurator(self)
    if with_infr:
      # Init internal domain manager if Infrastructure Layer is started
      self.domains.load_internal_mgr()
    # Init default domain managers
    self.domains.load_default_mgrs()
    # print "create test - VNFStarterAdapter"
    # starter = VNFStarterAdapter(server='localhost', port=830,
    #                             username='mininet', password='mininet',
    #                             debug=True)
    # with starter as s:
    #   reply = s.getVNFInfo()
    #   pprint(reply)
    #   reply = s.initiateVNF(vnf_type=s.VNF_HEADER_COMP)
    #   pprint(reply)
    #   vnf_id = reply['access_info']['vnf_id']
    #   reply = s.connectVNF(vnf_id=vnf_id, vnf_port=1, switch_id="EE1")
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
    log.debug("Invoke %s to install NF-FG" % self.__class__.__name__)
    # TODO - implement
    # TODO - no NFFG split just very dummy cycle
    for name, mgr in self.domains:
      log.debug("Delegate mapped NFFG to %s domain manager..." % name)
      mgr.install_nffg(mapped_nffg)
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
    Slice given :any:`NFFG` into separate parts.

    .. warning::
      Not implemented yet!

    :param nffg: mapped NFFG object
    :type nffg: NFFG
    :return: sliced parts
    :rtype: dict
    """
    pass


class DomainVirtualizer(AbstractVirtualizer):
  """
  Specific Virtualizer class for global domain virtualization.

  Implement the same interface as :class:`AbstractVirtualizer
  <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`
  """

  def __init__ (self, domainResManager):
    """
    Init.

    :param domainResManager: domain resource manager
    :type domainResManager: DomainResourceManager
    :return: None
    """
    super(DomainVirtualizer, self).__init__()
    log.debug("Init DomainVirtualizer")
    # Garbage-collector safe
    self.domainResManager = weakref.proxy(domainResManager)
    self.__global_view = None

  def get_resource_info (self):
    """
    Return the global resource info represented this class.

    .. warning::
      Not implemented yet!

    :return: global resource info
    :rtype: NFFG
    """
    return self.__global_view

  def set_nffg (self, nffg):
    self.__global_view = nffg


class DomainResourceManager(object):
  """
  Handle and store global resources.
  """

  def __init__ (self):
    """
    Init
    """
    super(DomainResourceManager, self).__init__()
    log.debug("Init DomainResourceManager")
    self._dov = DomainVirtualizer(self)
    self._tracked_domains = set()

  @property
  def dov (self):
    """
    Getter for :class:`DomainVirtualizer`.

    :return: Domain Virtualizer
    :rtype: ESCAPEVirtualizer
    """
    return self._dov

  def update_domain_resource (self, domain, nffg):
    """
    Update global resource database with resource usage relevant to installed
    components, routes, VNFs, etc.

    .. warning::
      Not implemented yet!

    :param domain: domain name
    :type domain: str
    :param nffg: domain resource
    :type nffg: :any:`NFFG`
    :return: None
    """
    if domain not in self._tracked_domains:
      log.info("Add %s domain to Global Resource View (DoV)..." % domain)
      self._dov.set_nffg(nffg)
      self._tracked_domains.add(domain)
    else:
      log.info("Updating Global Resource View...")
      # FIXME - only support INTERNAL domain ---> extend & improve !!!
      if domain == 'INTERNAL':
        self._dov.set_nffg(nffg)

