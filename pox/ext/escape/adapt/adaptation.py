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
from escape.adapt import LAYER_NAME
from escape.infr import LAYER_NAME as INFR_LAYER_NAME
from escape.orchest.virtualization_mgmt import AbstractVirtualizer
from escape.adapt import log as log
from escape.util.nffg import NFFG


class DomainConfigurator(object):
  """
  Initialize, configure and store Domain Manager objects

  Use global config to create managers and adapters

  Follows Component Configurator design pattern
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
    log.debug("Init Domain configurator")
    super(DomainConfigurator, self).__init__()
    self.__repository = {}
    self._lazy_load = lazy_load
    self._ca = ca
    if not lazy_load:
      # Initiate adapters from CONFIG
      self.load_default_mgrs()

  def get (self, domain_name):
    """
    Get Domain manager with given name.

    :param domain_name: name of domain manager
    :type domain_name: str
    :return: None
    """
    try:
      return self.__repository[domain_name]
    except KeyError:
      if self._lazy_load:
        return self.start(domain_name)
      else:
        raise AttributeError(
          "No adapter is defined with the name: %s" % domain_name)

  def start (self, domain_name):
    """
    Initialize and start a Domain manager.

    :param domain_name: name of domain manager
    :type domain_name: str
    :return: None
    """
    if domain_name not in self.__repository:
      mgr = self.__load_component(domain_name)
      mgr.start()
      return mgr
    else:
      log.warning(
        "Domain Component has been already started! Skip reinitialization...")
      return self.__repository[domain_name]

  def stop (self, domain_name):
    """
    Stop and derefer a Domain manager.

    :param domain_name: name of domain manager
    :type domain_name: str
    :return: None
    """
    if domain_name in self.__repository:
      self.__repository[domain_name].finit()
      del self.__repository[domain_name]

  @property
  def components (self):
    """
    Return the dict of initiated Domain managers.

    :return: managers
    :rtype: dict
    """
    return self.__repository

  def __iter__ (self):
    """
    Return with an iterator rely on initiated managers
    """
    return iter(self.__repository)

  def __load_component (self, component_name, **kwargs):
    """
    Load given component from config.

    :param component_name: adapter's name
    :type component_name: str
    :param kwargs: adapter's initial parameters
    :type kwargs: dict
    :return: initiated adapter
    :rtype: :any:`AbstractDomainAdapter`
    """
    try:
      component_class = CONFIG.get_domain_component(component_name)
      if component_class is not None:
        component = component_class(**kwargs)
        # Set up listeners for e.g. DomainChangedEvents
        component.addListeners(self._ca)
        # Set up listeners for DeployNFFGEvent
        component.addListeners(self._ca._layer_API)
        return component
      else:
        log.error(
          "Configuration of '%s' is missing. Skip initialization!" %
          component_name)
        return None
    except AttributeError:
      log.error(
        "%s is not found. Skip adapter initialization!" % component_name)
      return None

  def load_default_mgrs (self):
    """
    Init default adapters.
    """
    # very dummy initialization
    # TODO - improve
    for name in CONFIG.get_default_mgrs():
      self.__repository[name] = self.__load_component(name)

  def load_internal_mgr (self, remote=True):
    """
    Init Domain Manager for internal domain.

    :param remote: use NETCONF RPCs or direct access (default: True)
    :type remote: bool
    :return: None
    """
    try:
      if CONFIG.is_loaded(INFR_LAYER_NAME):
        # Set adapters for InternalDomainManager
        # Set OpenFlow route handler
        controller = self.__load_component("POX",
                                           name=CONFIG[LAYER_NAME]['INTERNAL'][
                                             'listener-id'])
        # Set emulated network initiator/handler/manager
        network = self.__load_component("MININET")
        # Set NETCONF handling capability if needed
        remote = self.__load_component('VNFStarter',
                                       **CONFIG[LAYER_NAME]['VNFStarter'][
                                         'agent']) if remote else None
        # Set internal domain manager
        self.__repository['INTERNAL'] = self.__load_component("INTERNAL",
                                                              controller=controller,
                                                              network=network,
                                                              remote=remote)
      else:
        log.error("%s layer is not loaded! Abort InternalDomainManager "
                  "initialization!" % INFR_LAYER_NAME)
    except KeyError as e:
      log.error(
        "Got KeyError during initialization of InternalDomainManager: %s", e)


class ControllerAdapter(object):
  """
  Higher-level class for :any:`NFFG` adaptation
  between multiple domains
  """

  def __init__ (self, layer_API, with_infr=False):
    """
    Initialize Controller adapter

    For domain adapters the ControllerAdapter checks the CONFIG first
    If there is no adapter defined explicitly then initialize the default
    Adapter class stored in `_defaults`

    .. warning::
      Adapter classes must be subclass of AbstractDomainAdapter

    .. note::
      Arbitrary domain adapters is searched in
      :mod:`escape.adapt.domain_adapters`

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
    self.domains = DomainConfigurator(self)
    if with_infr:
      # Init internal domain manager
      self.domains.load_internal_mgr()
    # Set virtualizer-related components
    self.domainResManager = DomainResourceManager()

  def install_nffg (self, mapped_nffg):
    """
    Start NF-FG installation

    Process given :any:`NFFG`, slice information based on domains an invoke
    domain adapters to install domain specific parts

    :param mapped_nffg: mapped NF-FG instance which need to be installed
    :type mapped_nffg: NFFG
    :return: None or internal domain NFFG part
    """
    log.debug("Invoke %s to install NF-FG" % self.__class__.__name__)
    # TODO - implement
    # TODO - no NFFG split just very dummy cycle
    if self._with_infr:
      log.debug("Delegate mapped NFFG to Internal domain manager...")
      self.domains.get('INTERNAL').install_nffg(mapped_nffg)
    else:
      for name, adapter in self.domains:
        log.debug("Delegate mapped NFFG to %s domain adapter..." % name)
        adapter.install_routes(mapped_nffg)
    log.debug("NF-FG installation is finished by %s" % self.__class__.__name__)

  def _handle_DomainChangedEvent (self, event):
    """
    Handle DomainChangedEvents, process changes and store relevant information
    in DomainResourceManager
    """
    pass

  def _slice_into_domains (self, nffg):
    """
    Slice given :any:`NFFG` into separate parts

    :param nffg: mapped NFFG object
    :type nffg: NFFG
    :return: sliced parts
    :rtype: dict
    """
    pass


class DomainVirtualizer(AbstractVirtualizer):
  """
  Specific Virtualizer class for global domain virtualization

  Implement the same interface as :class:`AbstractVirtualizer
  <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`
  """

  def __init__ (self, domainResManager):
    """
    Init

    :param domainResManager: domain resource manager
    :type domainResManager: DomainResourceManager
    :return: None
    """
    super(DomainVirtualizer, self).__init__()
    log.debug("Init DomainVirtualizer")
    # Garbage-collector safe
    self.domainResManager = weakref.proxy(domainResManager)

  def get_resource_info (self):
    """
    Return the global resource info represented this class

    :return: global resource info
    :rtype: NFFG
    """
    # TODO - implement - possibly don't store anything just convert??
    log.debug("Request global resource info...")
    return NFFG()


class DomainResourceManager(object):
  """
  Handle and store global resources
  """

  def __init__ (self):
    """
    Init
    """
    super(DomainResourceManager, self).__init__()
    log.debug("Init DomainResourceManager")
    self._dov = DomainVirtualizer(self)

  @property
  def dov (self):
    """
    Getter for :class:`DomainVirtualizer`

    :return: Domain Virtualizer
    :rtype: ESCAPEVirtualizer
    """
    return self._dov

  def update_resource_usage (self, data):
    """
    Update global resource database with resource usage relevant to installed
    components, routes, VNFs, etc.

    :param data: usage data
    :type data: dict
    :return: None
    """
    pass
