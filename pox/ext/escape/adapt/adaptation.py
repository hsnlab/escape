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
import importlib
import weakref

from escape import CONFIG
from escape.adapt import LAYER_NAME
from escape.infr import LAYER_NAME as infr_name
from escape.orchest.virtualization_mgmt import AbstractVirtualizer
from escape.adapt.domain_adapters import AbstractDomainAdapter, \
  POXDomainAdapter, InternalDomainAdapter
from escape.adapt import log as log
from escape.util.nffg import NFFG


class ControllerAdapter(object):
  """
  Higher-level class for :class:`NFFG <escape.util.nffg.NFFG>` adaptation
  between multiple domains
  """
  # Default adapters
  _adapters = {}

  def __init__ (self, lazy_load=True):
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
    """
    super(ControllerAdapter, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self.domainResManager = DomainResourceManager()
    self._lazy_load = lazy_load
    if not lazy_load:
      # Initiate adapters from CONFIG
      for adapter_name in CONFIG[LAYER_NAME]:
        self.__load_adapter(adapter_name)
    else:
      # Initiate default adapters. Other adapters will be created right after
      # the first reference to them
      self._adapters[POXDomainAdapter.name] = POXDomainAdapter()
      try:
        if CONFIG[infr_name]["LOADED"]:
          self._adapters[InternalDomainAdapter.name] = InternalDomainAdapter()
      except KeyError:
        pass

  def __getattr__ (self, item):
    """
    Expose adapters with it's names as an attribute of this class

    :param item: name of the adapter defined in it's class
    :type item: str
    :return: given domain adapter
    :rtype: AbstractDomainAdapter
    """
    try:
      if not item.startswith('__'):
        return self._adapters[item]
    except KeyError:
      if self._lazy_load:
        return self.__load_adapter(item)
      else:
        raise AttributeError("No adapter is defined with the name: %s" % item)

  def __load_adapter (self, name):
    try:
      adapter_class = getattr(
        importlib.import_module("escape.adapt.domain_adapters"),
        CONFIG[LAYER_NAME][name])
      assert issubclass(adapter_class,
                        AbstractDomainAdapter), "Adapter class: %s is not " \
                                                "subclass of " \
                                                "AbstractDomainAdapter!" % \
                                                adapter_class.__name__
      adapter = adapter_class()
      # Set initialized adapter
      self._adapters[name] = adapter
      # Set up listeners
      adapter.addListeners(self)
      return adapter
    except KeyError as e:
      log.error(
        "Configuration of '%s' is missing. Skip initialization!" % e.args[0])
    except AttributeError:
      log.error(
        "%s is not found. Skip adapter initialization!" % CONFIG[LAYER_NAME][
          name])

  def install_nffg (self, mapped_nffg):
    """
    Start NF-FG installation

    Process given :class:`NFFG <escape.util.nffg.NFFG>`, slice information
    based on domains an invoke domain adapters to install domain specific parts

    :param mapped_nffg: mapped NF-FG instance which need to be installed
    :type mapped_nffg: NFFG
    :return: None
    """
    log.debug("Invoke %s to install NF-FG" % self.__class__.__name__)
    # TODO - implement
    log.debug("NF-FG installation is finished by %s" % self.__class__.__name__)

  def _handle_DomainChangedEvent (self, event):
    """
    Handle DomainChangedEvents, process changes and store relevant information
    in DomainResourceManager
    """
    pass

  def _slice_into_domains (self, nffg):
    """
    Slice given :class:`NFFG <escape.util.nffg.NFFG>` into separate parts

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
    log.debug("Init %s" % self.__class__.__name__)
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
    log.debug("Init %s" % self.__class__.__name__)
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