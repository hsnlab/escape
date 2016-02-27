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
Contains components relevant to virtualization of resources and views.
"""
import weakref

from escape.nffg_lib.nffg import NFFGToolBox
from escape.orchest import log as log
from escape.orchest.policy_enforcement import PolicyEnforcementMetaClass
from pox.lib.revent.revent import EventMixin, Event

if 'DoV' not in globals():
  try:
    from escape.adapt.adaptation import DoV, DoVChangedEvent
  except ImportError:
    DoV = "DoV"


class MissingGlobalViewEvent(Event):
  """
  Event for signaling missing global resource view.
  """
  pass


class AbstractVirtualizer(EventMixin):
  """
  Abstract class for actual Virtualizers.

  Follows the Proxy design pattern.
  """
  __metaclass__ = PolicyEnforcementMetaClass
  # Default domain type for Virtualizers
  DEFAULT_DOMAIN = "VIRTUAL"
  # Trivial Virtualizer types
  DOMAIN_VIRTUALIZER = "DOV"
  SINGLE_VIRTUALIZER = "SINGLE"
  GLOBAL_VIRTUALIZER = "GLOBAL"

  def __init__ (self, type):
    """
    Init.

    :param type: Virtualizer type
    :type type: str
    """
    super(AbstractVirtualizer, self).__init__()
    self.type = type

  def __str__ (self):
    return "%s(type=%s)" % (self.__class__.__name__, self.type)

  def get_resource_info (self):
    """
    Hides object's mechanism and return with a resource object derived from
    :any:`NFFG`.

    .. warning::
      Derived class have to override this function!

    :raise: NotImplementedError
    :return: resource info
    :rtype: :any:`NFFG`
    """
    raise NotImplementedError("Derived class have to override this function")

  def sanity_check (self, nffg):
    """
    Place-holder for sanity check which implemented in
    :class:`PolicyEnforcement`.

    :param nffg: NFFG instance
    :type nffg: :any:`NFFG`
    :return: None
    """
    pass


class AbstractFilteringVirtualizer(AbstractVirtualizer):
  """
  Abstract class for Virtualizers filtering another Virtualizers.

  Contains template methods, dirty flag and event mechanism to handle
  resource changes in the observed and filtered :any:`DomainVirtualizer`.
  """

  def __init__ (self, id, global_view, type):
    """
    Init.

    :param id: id of the assigned entity
    :type: id: str
    :param global_view: virtualizer instance represents the global view
    :type global_view: :any:`DomainVirtualizer`
    :param type: Virtualizer type
    :type type: str
    """
    super(AbstractFilteringVirtualizer, self).__init__(type=type)
    self.id = id
    if global_view is not None:
      # Save the Global view (a.k.a DoV) reference and offer a filtered NFFG
      self.global_view = weakref.proxy(global_view)
      # Subscribe DoV events
      global_view.addListeners(self)
    self._dirty = None  # Set None to signal domain has not changed yet
    self._cache = None  # Cache for computed topology

  def __str__ (self):
    return "%s(assigned:%s, type=%s)" % (
      self.__class__.__name__, self.id, self.type)

  def get_resource_info (self):
    """
    Hides object's mechanism and return with a resource info.

    :return: resource info
    :rtype: :any:`NFFG`
    """
    # If topology has not changed -> return with cached resource
    if self._dirty is False:
      log.debug("DoV is unchanged! Return cached NFFG...")
      return self._cache
    # If Virtualizer dirty resource info is changed since last request or has
    # never queried yet -> acquire resource info with template method
    if self._dirty is True:
      log.debug("DoV has been changed! Requesting new resource NFFG...")
    # Acquire resource
    resource = self._acquire_resource()
    # Cache new resource
    self._cache = resource
    # Clear dirty flag
    self._dirty = False
    return resource

  def _handle_DoVChangedEvent (self, event):
    """
    Handle :any:`DomainChangedEvent` raised by the observer
    :any:`DomainVirtualizer`.

    :param event: event object
    :type event: :any:`DomainChangedEvent`
    :return: None
    """
    log.debug("Received DoVChanged notification for %s! Cause: %s" % (
      self, DoVChangedEvent.TYPE.reversed[event.cause]))
    # Topology is changed, set dirty flag
    self._dirty = True

  def _acquire_resource (self):
    """
    Template method for acquiring or filtering the resource info if the
    topology has changed.

    .. warning::
      Derived class have to override this function!

    :raise: NotImplementedError
    :return: resource info
    :rtype: :any:`NFFG`
    """
    raise NotImplementedError("Derived class have to override this function")


class GlobalViewVirtualizer(AbstractFilteringVirtualizer):
  """
  Virtualizer class for experimenting and testing.

  No filtering, just offer the whole global resource view.
  """

  def __init__ (self, global_view, id):
    """
    Init.

    :param global_view: virtualizer instance represents the global view
    :type global_view: :any:`DomainVirtualizer`
    :param id: id of the assigned entity
    :type: id: str
    """
    log.debug("Initiate unfiltered/global <Virtual View>")
    super(GlobalViewVirtualizer, self).__init__(id=id,
                                                global_view=global_view,
                                                type=self.GLOBAL_VIRTUALIZER)

  def get_resource_info (self):
    """
    Return with the unfiltered global view.

    :return: Virtual resource info
    :rtype: :any:`NFFG`
    """
    # Leave the dirty mechanism operational
    self._dirty = False
    log.debug(
      "No filtering in Virtualizer: %s. Return full global resource..." %
      self.type)
    # Currently we NOT filter the global view just propagate to other layers
    # and entities intact
    return self.global_view.get_resource_info()

  def _acquire_resource (self):
    pass


class SingleBiSBiSVirtualizer(AbstractFilteringVirtualizer):
  """
  Actual Virtualizer class for ESCAPEv2.

  Default virtualizer class which offer the trivial one BisBis view.
  """

  def __init__ (self, global_view, id):
    """
    Init.

    :param global_view: virtualizer instance represents the global view
    :type global_view: :any:`DomainVirtualizer`
    :param id: id of the assigned entity
    :type: id: str
    """
    log.debug("Initiate default SingleBiSBiS <Virtual View>")
    super(SingleBiSBiSVirtualizer, self).__init__(id=id,
                                                  global_view=global_view,
                                                  type=self.SINGLE_VIRTUALIZER)

  def _acquire_resource (self):
    """
    Compute and return with the Single BiS-BiS view based on the global view.

    :return: single BiSBiS representation of the global view
    :rtype: :any:`NFFG`
    """
    dov = self.global_view.get_resource_info()
    if dov.is_empty():
      # DoV is not initialized yet! Probably only just remote Mgrs has been
      # enabled! return with the default empty DoV
      log.warning(
        "Requested global resource view is empty! Return the default empty "
        "topology!")
      return dov
    else:
      # Generate the Single BiSBiS representation
      return NFFGToolBox.generate_SBB_representation(dov=dov, log=log)


class VirtualizerManager(EventMixin):
  """
  Store, handle and organize instances of derived classes of
  :class:`AbstractVirtualizer
  <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`.
  """
  # Events raised by this class
  _eventMixin_events = {MissingGlobalViewEvent}

  def __init__ (self):
    """
    Initialize virtualizer manager.

    :return: None
    """
    super(VirtualizerManager, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self._virtualizers = dict()

  @property
  def dov (self):
    """
    Getter method for the :class:`DomainVirtualizer`.

    Request DoV from Adaptation if it hasn't set yet.

    Use: `virtualizerManager.dov`.

    :return: Domain Virtualizer (DoV)
    :rtype: :any:`DomainVirtualizer`
    """
    log.debug(
      "Invoke %s to get DoV" % self.__class__.__name__)
    # If DoV is not set up, need to request from Adaptation layer
    if DoV not in self._virtualizers:
      log.debug("Missing DoV! Requesting the View now...")
      self.raiseEventNoErrors(MissingGlobalViewEvent)
      if DoV in self._virtualizers and self._virtualizers[DoV] is not None:
        log.debug(
          "Got requested DoV: %s" % self._virtualizers[DoV])
    # Return with resource info as a DomainVirtualizer
    return self._virtualizers.get(DoV, None)

  @dov.setter
  def dov (self, dov):
    """
    DoV setter.

    :param dov: Domain Virtualizer (DoV)
    :type dov: :any:`DomainVirtualizer`
    :return: None
    """
    self._virtualizers[DoV] = dov

  @dov.deleter
  def dov (self):
    """
    DoV deleter.

    :return: None
    """
    del self._virtualizers[DoV]

  def get_virtual_view (self, virtualizer_id, type=None, cls=None):
    """
    Return the Virtual View as a derived class of :class:`AbstractVirtualizer
    <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`.

    :param virtualizer_id: unique id of the requested Virtual view
    :type virtualizer_id: int or str
    :param type: type of the Virtualizer predefined in this class
    :type type: str
    :param cls: specific Virtualizer class if type is not given
    :type cls: :any:`AbstractVirtualizer`
    :return: virtual view
    :rtype: :any:`AbstractVirtualizer`
    """
    log.debug("Invoke %s to get <Virtual View> (for layer ID: %s)" % (
      self.__class__.__name__, virtualizer_id))
    # If this is the first request, need to generate the view
    if virtualizer_id not in self._virtualizers:
      if type is not None:
        # SINGLE: generate a trivial Single BiS-BiS virtualizer
        log.debug("Requested virtualizer type: %s" % type)
        if type == AbstractVirtualizer.SINGLE_VIRTUALIZER:
          self._generate_single_view(id=virtualizer_id)
        # GLOBAL: generate a non-filtering Global View Virtualizer
        elif type == AbstractVirtualizer.GLOBAL_VIRTUALIZER:
          self._generate_global_view(id=virtualizer_id)
        # Not supported format
        else:
          log.warning("Unsupported Virtualizer type: %s" % type)
          return
      # If a specific AbstractVirtualizer type was given
      elif cls is not None:
        log.debug(
          "Generating Virtualizer type: %s with id: %s" % (
            cls.__name__, virtualizer_id))
        self._virtualizers[virtualizer_id] = cls(self.dov, virtualizer_id)
      # Generate a Single BiS-BiS Virtualizer by default
      else:
        # Virtualizer type is not defined: Use SingleBiSBiSVirtualizer by
        # default
        self._generate_single_view(id=virtualizer_id)
    # Return Virtualizer
    return self._virtualizers[virtualizer_id]

  def _generate_single_view (self, id):
    """
    Generate a Single BiSBiS virtualizer, store and return with it.

    :param id: unique virtualizer id
    :type id: int or str
    :return: generated Virtualizer
    :rtype: :any:`SingleBiSBiSVirtualizer`
    """
    if id in self._virtualizers:
      log.warning(
        "Requested Virtualizer with ID: %s is already exist! "
        "Virtualizer creation skipped..." % id)
    else:
      log.debug(
        "Generating Single BiSBiS Virtualizer with id: %s" % id)
      self._virtualizers[id] = SingleBiSBiSVirtualizer(self.dov, id)
    return self._virtualizers[id]

  def _generate_global_view (self, id):
    """
    Generate a Global View virtualizer, store and return with it.

    :param id: unique virtualizer id
    :type id: int or str
    :return: generated Virtualizer
    :rtype: :any:`GlobalViewVirtualizer`
    """
    if id in self._virtualizers:
      log.warning(
        "Requested Virtualizer with ID: %s is already exist! "
        "Virtualizer creation skipped..." % id)
    else:
      log.debug(
        "Generating Global View Virtualizer with id: %s" % id)
      self._virtualizers[id] = GlobalViewVirtualizer(self.dov, id)
    return self._virtualizers[id]
