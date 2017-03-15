# Copyright 2017 Janos Czentye
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
import threading
import weakref

from wrapt.decorators import synchronized

import escape.adapt
from escape.adapt.policy_enforcement import PolicyEnforcementMetaClass
from escape.nffg_lib.nffg import NFFGToolBox, NFFG
from escape.util.config import CONFIG
from escape.util.misc import enum, VERBOSE
from pox.lib.revent.revent import EventMixin, Event

# Common reference name for the DomainVirtualizer
DoV = "DoV"
"""Common reference name for the DomainVirtualizer"""
log = escape.adapt.log.getChild("view")


class DoVChangedEvent(Event):
  """
  Event for signalling the DoV is changed.
  """
  # Constants for type of changes
  TYPE = enum("UPDATE", "EXTEND", "CHANGE", "REDUCE", "EMPTY")
  """Constants for type of changes"""

  def __init__ (self, cause):
    """
    Init.

    :param cause: cause of the change
    :type cause: str
    :return: None
    """
    super(DoVChangedEvent, self).__init__()
    self.cause = cause


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
  """Metaclass"""
  # Default domain type for Virtualizers
  DEFAULT_DOMAIN = "VIRTUAL"
  """Default domain type for Virtualizers"""

  # # Trivial Virtualizer types
  # DOMAIN_VIRTUALIZER = "DOV"
  # SINGLE_VIRTUALIZER = "SINGLE"
  # GLOBAL_VIRTUALIZER = "GLOBAL"
  TYPE = None

  def __init__ (self):
    """
    Init.

    :return: None
    """
    super(AbstractVirtualizer, self).__init__()

  def __str__ (self):
    """
    Return with specific string representation.

    :return: string representation
    :rtype: str
    """
    return "%s(type=%s)" % (self.__class__.__name__, self.TYPE)

  def get_resource_info (self):
    """
    Hides object's mechanism and return with a resource object derived from
    :class:`NFFG`.

    .. warning::
      Derived class have to override this function!

    :raise: NotImplementedError
    :return: resource info
    :rtype: :class:`NFFG`
    """
    raise NotImplementedError

  def sanity_check (self, nffg):
    """
    Place-holder for sanity check which implemented in
    :class:`PolicyEnforcement`.

    :param nffg: NFFG instance
    :type nffg: :class:`NFFG`
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
    :return: None
    """
    super(AbstractFilteringVirtualizer, self).__init__()
    self.id = id
    if global_view is not None:
      # Save the Global view (a.k.a DoV) reference and offer a filtered NFFG
      self.global_view = weakref.proxy(global_view)
      # Subscribe DoV events
      global_view.addListeners(self)
    self.__dirty = None  # Set None to signal domain has not changed yet
    self.__cache = None  # Cache for computed topology

  def __str__ (self):
    """
    Return with specific string representation.

    :return: string representation
    :rtype: str
    """
    return "%s(assigned:%s, type=%s)" % (
      self.__class__.__name__, self.id, self.TYPE)

  def is_changed (self):
    """
    Return True if virtual resource view has been changed or has not set yet
    and need to generate the virtual view.

    :return: view has been changed or not
    :rtype: bool
    """
    return self.__dirty is not False

  def get_resource_info (self):
    """
    Hides object's mechanism and return with a resource info.

    :return: resource info
    :rtype: :class:`NFFG`
    """
    # If topology has not changed -> return with cached resource
    if self.__dirty is False:
      log.debug("DoV is unchanged! Return cached NFFG...")
    else:
      if self.__dirty is None:
        log.debug("Virtual view is uninitialized! "
                  "Requesting resource NFFG...")
      else:
        log.debug("DoV has been changed! Requesting new resource NFFG...")
      # If Virtualizer dirty resource info is changed since last request or has
      # never queried yet -> acquire resource info with template method
      # Acquire and cache new resource
      self.__cache = self._acquire_resource()
      log.debug("Clear dirty flag...")
      # Clear dirty flag
      self.__dirty = False
    return self.__cache

  def get_cached_resource_info (self):
    """
    Return the cached resource info object. If the cached topo is missing it
    returns with None.
    This function will not acquire the latest topology and has not affect to
    the dirty flag.

    :return: cached topology
    :rtype: :class:`NFFG`
    """
    return self.__cache

  def _handle_DoVChangedEvent (self, event):
    """
    Handle :any:`DomainChangedEvent` raised by the observer
    :any:`DomainVirtualizer`.

    :param event: event object
    :type event: :any:`DomainChangedEvent`
    :return: None
    """
    log.debug("Received DoVChanged notification for %s! Cause: %s -> "
              "Set dirty flag!" % (self,
                                   DoVChangedEvent.TYPE.reversed[event.cause]))
    # Topology is changed, set dirty flag
    self.__dirty = True

  def _acquire_resource (self):
    """
    Template method for acquiring or filtering the resource info if the
    topology has changed.

    .. warning::
      Derived class have to override this function!

    :raise: NotImplementedError
    :return: resource info
    :rtype: :class:`NFFG`
    """
    raise NotImplementedError


class DomainVirtualizer(AbstractVirtualizer):
  """
  Specific Virtualizer class for global domain virtualization.

  Implement the same interface as :class:`AbstractVirtualizer
  <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`

  Use :class:`NFFG` format to store the global infrastructure info.
  """
  # Events raised by this class
  _eventMixin_events = {DoVChangedEvent}
  """Events raised by this class"""
  TYPE = 'DOV'
  # Reentrant lock to synchronize the access to the DoV
  __DoV_lock = threading.RLock()

  def __init__ (self, mgr, global_res=None, **kwargs):
    """
    Init.

    :param mgr: global domain resource manager
    :type mgr: :any:`GlobalResourceManager`
    :param global_res: initial global resource (optional)
    :type global_res: :class:`NFFG`
    :param kwargs: optional parameters for Virtualizer
    :type kwargs: dict
    :return: None
    """
    super(DomainVirtualizer, self).__init__()
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
    """
    Return with the name of the View.

    :return: name of the view
    :rtype: str
    """
    if self.__global_nffg is not None and hasattr(self.__global_nffg, 'name'):
      return self.__global_nffg.name
    else:
      return DoV + "-uninitialized"

  def __str__ (self):
    """
    Return with specific string representation.

    :return: string representation
    :rtype: str
    """
    return "DomainVirtualizer(name=%s)" % self.name

  def __repr__ (self):
    """
    Return with specific representation.

    :return: spec representation
    :rtype: str
    """
    return super(DomainVirtualizer, self).__repr__()

  @synchronized(__DoV_lock)
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

  @synchronized(__DoV_lock)
  def get_resource_info (self):
    """
    Return the copy of the global resource info represented this class.

    :return: global resource info
    :rtype: :class:`NFFG`
    """
    return self.__global_nffg.copy()

  @synchronized(__DoV_lock)
  def set_domain_as_global_view (self, domain, nffg):
    """
    Set the copy of given NFFG as the global view of DoV.

    Add the specific :attr:`DoV` id and generated name to the global view.

    :param nffg: NFFG instance intended to use as the global view
    :type nffg: :class:`NFFG`
    :param domain: name of the merging domain
    :type domain: str
    :return: updated Dov
    :rtype: :class:`NFFG`
    """
    log.debug("Set domain: %s as the global view!" % domain)
    if not self.__global_nffg.is_empty():
      log.warning("Global view is not empty! Current state will be lost!")
    self.__global_nffg = nffg.copy()
    self.__global_nffg.id = DoV
    self.__global_nffg.name = DoV
    # Raise event for observing Virtualizers about topology change
    self.raiseEventNoErrors(DoVChangedEvent, cause=DoVChangedEvent.TYPE.UPDATE)
    return self.__global_nffg

  @synchronized(__DoV_lock)
  def update_full_global_view (self, nffg):
    """
    Update the merged Global view with the given probably modified global view.

    Reserve id, name values of the global view.

    :param nffg: updated global view which replace the stored one
    :type nffg: :class:`NFFG`
    :return: updated Dov
    :rtype: :class:`NFFG`
    """
    dov_id = self.__global_nffg.id
    dov_name = self.__global_nffg.name
    self.__global_nffg = nffg.copy()
    self.__global_nffg.id, self.__global_nffg.name = dov_id, dov_name
    # Raise event for observing Virtualizers about topology change
    self.raiseEventNoErrors(DoVChangedEvent, cause=DoVChangedEvent.TYPE.UPDATE)
    return self.__global_nffg

  @synchronized(__DoV_lock)
  def merge_new_domain_into_dov (self, nffg):
    """
    Add a newly detected domain to DoV.

    Based on the feature: escape.util.nffg.NFFGToolBox#merge_domains

    :param nffg: NFFG object need to be merged into DoV
    :type nffg: :class:`NFFG`
    :return: updated Dov
    :rtype: :class:`NFFG`
    """
    # Using general merging function from NFFGToolBox and return the updated
    # NFFG
    NFFGToolBox.merge_new_domain(base=self.__global_nffg, nffg=nffg, log=log)
    # Raise event for observing Virtualizers about topology change
    log.log(VERBOSE, "Merged Dov:\n%s" % self.__global_nffg.dump())
    self.raiseEventNoErrors(DoVChangedEvent, cause=DoVChangedEvent.TYPE.EXTEND)
    return self.__global_nffg

  @synchronized(__DoV_lock)
  def remerge_domain_in_dov (self, domain, nffg):
    """
    Update the existing domain in the merged Global view with explicit domain
    remove and re-add.

    :param nffg: changed infrastructure info
    :type nffg: :class:`NFFG`
    :param domain: name of the merging domain
    :type domain: str
    :return: updated Dov
    :rtype: :class:`NFFG`
    """
    NFFGToolBox.remove_domain(base=self.__global_nffg, domain=domain, log=log)
    # log.log(VERBOSE, "Reduced Dov:\n%s" % self.__global_nffg.dump())
    NFFGToolBox.merge_new_domain(base=self.__global_nffg, nffg=nffg, log=log)
    log.log(VERBOSE, "Re-merged DoV:\n%s" % self.__global_nffg.dump())
    if self.__global_nffg.is_empty():
      log.warning("No Node had been remained after updating the domain part: "
                  "%s! DoV is empty!" % domain)
    # Raise event for observing Virtualizers about topology change
    self.raiseEventNoErrors(DoVChangedEvent, cause=DoVChangedEvent.TYPE.CHANGE)
    return self.__global_nffg

  @synchronized(__DoV_lock)
  def update_domain_in_dov (self, domain, nffg):
    """
    Update the existing domain in the merged Global view.

    :param nffg: changed infrastructure info
    :type nffg: :class:`NFFG`
    :param domain: name of the merging domain
    :type domain: str
    :return: updated Dov
    :rtype: :class:`NFFG`
    """
    NFFGToolBox.update_domain(base=self.__global_nffg, updated=nffg, log=log)
    if self.__global_nffg.is_empty():
      log.warning("No Node had been remained after updating the domain part: "
                  "%s! DoV is empty!" % domain)
    log.log(VERBOSE, "Updated DoV:\n%s" % self.__global_nffg.dump())
    # Raise event for observing Virtualizers about topology change
    self.raiseEventNoErrors(DoVChangedEvent, cause=DoVChangedEvent.TYPE.CHANGE)
    return self.__global_nffg

  @synchronized(__DoV_lock)
  def remove_domain_from_dov (self, domain):
    """
    Remove the nodes and edges with the given from Global view.

    :param domain: domain name
    :type domain: str
    :return: updated Dov
    :rtype: :class:`NFFG`
    """
    NFFGToolBox.remove_domain(base=self.__global_nffg, domain=domain, log=log)
    if self.__global_nffg.is_empty():
      log.warning("No Node had been remained after updating the domain part: "
                  "%s! DoV is empty!" % domain)
    log.log(VERBOSE, "Reduced Dov:\n%s" % self.__global_nffg.dump())
    # Raise event for observing Virtualizers about topology change
    self.raiseEventNoErrors(DoVChangedEvent, cause=DoVChangedEvent.TYPE.REDUCE)
    return self.__global_nffg

  @synchronized(__DoV_lock)
  def clean_domain_from_dov (self, domain):
    """
    Clean domain by removing initiated NFs and flowrules related to BiSBiS
    nodes of the given domain

    :param domain: domain name
    :type domain: str
    :return: updated Dov
    :rtype: :class:`NFFG`
    """
    if self.__global_nffg.is_empty():
      log.debug("DoV is empty! Skip cleanup domain: %s" % domain)
      return self.__global_nffg
    if self.__global_nffg.is_bare():
      log.debug("No initiated service has been detected in DoV! "
                "Skip cleanup domain: %s" % domain)
      return self.__global_nffg
    NFFGToolBox.clear_domain(base=self.__global_nffg, domain=domain, log=log)
    log.log(VERBOSE, "Cleaned Dov:\n%s" % self.__global_nffg.dump())
    self.raiseEventNoErrors(DoVChangedEvent, cause=DoVChangedEvent.TYPE.CHANGE)
    return self.__global_nffg

  @synchronized(__DoV_lock)
  def update_domain_status_in_dov (self, domain, nffg):
    """
    Set status of initiated NFs and flowrules related to BiSBiS nodes of the
    given domain.

    :param domain: domain name
    :type domain: str
    :param nffg: changed infrastructure info
    :type nffg: :class:`NFFG`
    :return: updated Dov
    :rtype: :class:`NFFG`
    """
    if self.__global_nffg.is_empty():
      log.debug("DoV is empty! Skip cleanup domain: %s" % domain)
      return self.__global_nffg
    NFFGToolBox.update_status_info(nffg=nffg, status=NFFG.STATUS_DEPLOY)
    NFFGToolBox.update_nffg_by_status(base=self.__global_nffg, updated=nffg,
                                      log=log)
    log.log(VERBOSE, "Updated Dov:\n%s" % self.__global_nffg.dump())
    self.raiseEventNoErrors(DoVChangedEvent, cause=DoVChangedEvent.TYPE.CHANGE)
    return self.__global_nffg

  @synchronized(__DoV_lock)
  def remove_deployed_elements (self):
    """
    Remove all the NFs, flowrules and dynamic ports from DoV.

    :return: updated Dov
    :rtype: :class:`NFFG`
    """
    if self.__global_nffg.is_empty():
      log.debug("DoV is empty! Skip DoV cleanup")
      return self.__global_nffg
    NFFGToolBox.remove_deployed_services(nffg=self.__global_nffg, log=log)
    log.log(VERBOSE, "Cleared Dov:\n%s" % self.__global_nffg.dump())
    self.raiseEventNoErrors(DoVChangedEvent, cause=DoVChangedEvent.TYPE.CHANGE)
    return self.__global_nffg


class GlobalViewVirtualizer(AbstractFilteringVirtualizer):
  """
  Virtualizer class for experimenting and testing.

  No filtering, just offer the whole global resource view.
  """
  TYPE = 'GLOBAL'
  """Type name of the Virtualizer"""

  def __init__ (self, global_view, id, **kwargs):
    """
    Init.

    :param global_view: virtualizer instance represents the global view
    :type global_view: :any:`DomainVirtualizer`
    :param id: id of the assigned entity
    :type: id: str
    :param kwargs: optional parameters for Virtualizer
    :type kwargs: dict
    :return: None
    """
    log.debug("Initiate unfiltered/global <Virtual View>")
    super(GlobalViewVirtualizer, self).__init__(id=id,
                                                global_view=global_view,
                                                type=self.TYPE)

  def get_resource_info (self):
    """
    Return with the unfiltered global view.

    :return: Virtual resource info
    :rtype: :class:`NFFG`
    """
    # Leave the dirty mechanism operational
    self._dirty = False
    log.debug(
      "No filtering in Virtualizer: %s. Return full global resource..." %
      self.TYPE)
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
  TYPE = 'SINGLE'
  """Type name of the Virtualizer"""

  def __init__ (self, global_view, id, **kwargs):
    """
    Init.

    :param global_view: virtualizer instance represents the global view
    :type global_view: :any:`DomainVirtualizer`
    :param id: id of the assigned entity
    :type: id: str
    :param kwargs: optional parameters for Virtualizer
    :type kwargs: dict
    :return: None
    """
    log.debug("Initiate SingleBiSBiS <Virtual View>")
    super(SingleBiSBiSVirtualizer, self).__init__(id=id,
                                                  global_view=global_view,
                                                  type=self.TYPE)

  def _acquire_resource (self):
    """
    Compute and return with the Single BiS-BiS view based on the global view.

    :return: single BiSBiS representation of the global view
    :rtype: :class:`NFFG`
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
      sbb = NFFGToolBox.generate_SBB_representation(nffg=dov, log=log)
      log.log(VERBOSE, "Generated SBB:\n%s" % sbb.dump())
      return sbb


class ZeroDelayedSBBVirtualizer(SingleBiSBiSVirtualizer):
  """
  Single BiSBiS Virtualizer generating SBB node with 0 delay.
  """
  TYPE = 'ZERO-DELAYED-SBB'
  """Type name of the Virtualizer"""

  def _acquire_resource (self):
    sbb = super(ZeroDelayedSBBVirtualizer, self)._acquire_resource()
    for infra in sbb.infras:
      log.debug("Set %s delay: 0" % infra.id)
      infra.resources.delay = 0
    return sbb


class LocalSingleBiSBiSVirtualizer(AbstractFilteringVirtualizer):
  """
  Actual Virtualizer class for ESCAPEv2.

  Virtualizer class which offer the trivial one BisBis view without the domains
  detected by an :any:`ExternalDomainManager`.
  """
  TYPE = 'SINGLE-LOCAL'
  """Type name of the Virtualizer"""

  def __init__ (self, global_view, id, **kwargs):
    """
    Init.

    :param global_view: virtualizer instance represents the global view
    :type global_view: :any:`DomainVirtualizer`
    :param id: id of the assigned entity
    :type: id: str
    :param kwargs: optional parameters for Virtualizer
    :type kwargs: dict
    :return: None
    """
    log.debug("Initiate only-local SingleBiSBiS <Virtual View>")
    super(LocalSingleBiSBiSVirtualizer, self).__init__(id=id,
                                                       global_view=global_view,
                                                       type=self.TYPE)

  @staticmethod
  def __filter_external_domains (nffg):
    """
    Filter out domains detected by external DomainManagers.

    :param nffg: filtered NFFG
    :return: :class:`NFFG`
    """
    log.debug("Filtering domains detected from external DomainManagers...")
    # Get External DomainManager names
    ext_mgr = CONFIG.get_external_managers()
    # Copy NFFG
    filtered_nffg = nffg.copy()
    # Remove the detected domains by External DomainManagers
    for ext in ext_mgr:
      # Get all the domains
      domains = NFFGToolBox.detect_domains(nffg=filtered_nffg)
      # Get domains detected and initiated by the External DomainManager
      ext_domains = [d for d in domains if ext in d]
      # Remove collected domains from NFFG
      for domain in ext_domains:
        log.debug(
          "Remove domain: %s originated from external DomainManager: %s" % (
            domain, ext))
        NFFGToolBox.remove_domain(base=filtered_nffg, domain=domain, log=log)
    filtered_nffg.name += "-filtered"
    return filtered_nffg

  def _acquire_resource (self):
    """
    Compute and return with the Single BiS-BiS view based on the global view.

    :return: single BiSBiS representation of the global view
    :rtype: :class:`NFFG`
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
      filtered_dov = self.__filter_external_domains(nffg=dov)
      # Generate the Single BiSBiS representation
      sbb = NFFGToolBox.generate_SBB_representation(nffg=filtered_dov, log=log)
      log.log(VERBOSE, "Generated SBB:\n%s" % sbb.dump())
      return sbb


class VirtualizerManager(EventMixin):
  """
  Store, handle and organize instances of derived classes of
  :class:`AbstractVirtualizer
  <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`.
  """
  # Events raised by this class
  _eventMixin_events = {MissingGlobalViewEvent}

  VIRTUALIZERS = {
    # DomainVirtualizer.TYPE: DomainVirtualizer,
    GlobalViewVirtualizer.TYPE: GlobalViewVirtualizer,
    SingleBiSBiSVirtualizer.TYPE: SingleBiSBiSVirtualizer,
    LocalSingleBiSBiSVirtualizer.TYPE: LocalSingleBiSBiSVirtualizer,
    ZeroDelayedSBBVirtualizer.TYPE: ZeroDelayedSBBVirtualizer
  }
  """Collection of the available Virtualizers type -> class"""

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

  def get_virtual_view (self, virtualizer_id, type=None, cls=None, **kwargs):
    """
    Return the Virtual View as a derived class of :class:`AbstractVirtualizer
    <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`.

    :param virtualizer_id: unique id of the requested Virtual view
    :type virtualizer_id: int or str
    :param type: type of the Virtualizer predefined in this class
    :type type: str
    :param cls: specific Virtualizer class if type is not given
    :type cls: :any:`AbstractVirtualizer`
    :param kwargs: optional parameters for Virtualizer
    :type kwargs: dict
    :return: virtual view
    :rtype: :any:`AbstractVirtualizer`
    """
    log.debug("Invoke %s to get <Virtual View> (for layer ID: %s)" % (
      self.__class__.__name__, virtualizer_id))
    # If this is the first request, need to generate the view
    if virtualizer_id not in self._virtualizers:
      if type is not None:
        if type in self.VIRTUALIZERS:
          virtualizer_class = self.VIRTUALIZERS[type]
          self._virtualizers[virtualizer_id] = virtualizer_class(self.dov,
                                                                 virtualizer_id,
                                                                 **kwargs)
          log.debug("Generated Virtualizer with type: %s id: %s" % (
            type, virtualizer_id))
        # Not supported format
        else:
          log.error("Unsupported Virtualizer type: %s" % type)
          return
      # If a specific AbstractVirtualizer type was given
      elif cls is not None:
        log.debug("Generating Virtualizer type: %s with id: %s" %
                  (cls.__name__, virtualizer_id))
        self._virtualizers[virtualizer_id] = cls(self.dov, virtualizer_id,
                                                 **kwargs)
      # Generate a Single BiS-BiS Virtualizer by default
      else:
        # Virtualizer type is not defined: Use SingleBiSBiSVirtualizer by
        # default
        log.error(
          "Virtualizer type is missing for requested Virtualizer: %s!" %
          virtualizer_id)
        return None
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
      log.warning("Requested Virtualizer with ID: %s is already exist! "
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
      log.warning("Requested Virtualizer with ID: %s is already exist! "
                  "Virtualizer creation skipped..." % id)
    else:
      log.debug("Generating Global View Virtualizer with id: %s" % id)
      self._virtualizers[id] = GlobalViewVirtualizer(self.dov, id)
    return self._virtualizers[id]
