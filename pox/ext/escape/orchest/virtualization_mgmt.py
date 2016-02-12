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
import itertools

from escape.nffg_lib.nffg import NFFG
from escape.orchest import log as log
from escape.orchest.policy_enforcement import PolicyEnforcementMetaClass
from pox.lib.revent.revent import EventMixin, Event

if 'DoV' not in globals():
  try:
    from escape.adapt.adaptation import DoV
  except ImportError:
    DoV = "DoV"


class MissingGlobalViewEvent(Event):
  """
  Event for signaling missing global resource view.
  """
  pass


class AbstractVirtualizer(object):
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

  def __init__ (self, id, type):
    """
    Init.

    :param id: id of the assigned entity
    :type: id: str
    :param type: Virtualizer type
    :type type: str
    """
    super(AbstractVirtualizer, self).__init__()
    self.id = id
    self.type = type

  def __str__ (self):
    return "%s(assigned=%s)" % (self.__class__.__name__, self.id)

  def __repr__ (self):
    return super(AbstractVirtualizer, self).__repr__()

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


class GlobalViewVirtualizer(AbstractVirtualizer):
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
                                                type=self.GLOBAL_VIRTUALIZER)
    # Save the Global view (a.k.a DoV) reference and offer a filtered NFFG
    self.global_view = global_view

  def get_resource_info (self):
    """
    Hides object's mechanism and return with a resource object derived from
    :any:`NFFG`.

    :return: Virtual resource info as an NFFG
    :rtype: :any:`NFFG`
    """
    # log.debug("Request virtual resource info...")
    # Currently we NOT filter the global view just propagate to other layers
    # and entities intact
    return self.global_view.get_resource_info()


class SingleBiSBiSVirtualizer(AbstractVirtualizer):
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
                                                  type=self.SINGLE_VIRTUALIZER)
    # Save the Global view (a.k.a DoV) reference and offer a filtered NFFG
    self.global_view = global_view
    self.__resource_cache = None

  def get_resource_info (self):
    """
    Hides object's mechanism and return with a resource object derived from
    :any:`NFFG`.

    :return: Virtual resource info as an NFFG
    :rtype: :any:`NFFG`
    """
    # log.debug("Request virtual resource info...")
    # Currently we NOT filter the global view just propagate to other layers
    # and entities intact
    if self.__resource_cache is None:
      self.__resource_cache = self._generate_one_bisbis()
    return self.__resource_cache

  def _generate_one_bisbis (self):
    """
    Generate trivial virtual topology a.k.a 1 BisBis.

    :return: 1 Bisbis topo
    :rtype: :any:`NFFG`
    """
    log.debug(
      "Generate trivial SingleBiSBiS NFFG based on %s:" % self.global_view)
    # Create Single BiSBiS NFFG
    nffg = NFFG(id="SingleBiSBiS-NFFG", name="Single-BiSBiS-View")
    if self.global_view is None:
      log.error(
        "Missing global view from %s. Skip OneBiSBiS generation!" %
        self.__class__.__name__)
      return
    dov = self.global_view.get_resource_info()
    if dov is None:
      log.error("Missing resource info from DoV. Skip OneBisBis generation!")
      return
    import random
    # Create the single BiSBiS infra
    sbb = nffg.add_infra(
      id="SingleBiSbiS-%s" % (id(self) + random.randint(0, 1000)),
      name="Single-BiSBiS",
      domain=NFFG.DEFAULT_DOMAIN,
      infra_type=NFFG.TYPE_INFRA_BISBIS)
    log.debug("Add Infra BiSBiS: %s" % sbb)

    # Compute and add resources
    # Sum of available CPU
    try:
      sbb.resources.cpu = sum(
        # If iterator is empty, sum got None --> TypeError thrown by sum
        (n.resources.cpu for n in dov.infras if
         n.resources.cpu is not None) or None)
    except TypeError:
      sbb.resources.cpu = None
    # Sum of available memory
    try:
      sbb.resources.mem = sum(
        # If iterator is empty, sum got None --> TypeError thrown by sum
        (n.resources.mem for n in dov.infras if
         n.resources.mem is not None) or None)
    except TypeError:
      sbb.resources.mem = None
    # Sum of available storage
    try:
      sbb.resources.storage = sum(
        # If iterator is empty, sum got None --> TypeError thrown by sum
        (n.resources.storage for n in dov.infras if
         n.resources.storage is not None) or None)
    except TypeError:
      sbb.resources.storage = None
    # Minimal available delay value of infras and links in DoV
    try:
      # Get the minimum delay in Dov to avoid false negative mapping result
      sbb.resources.delay = min(itertools.chain(
        # If the chained iterators is empty --> ValueError thrown by sum
        (n.resources.delay for n in dov.infras if
         n.resources.delay is not None),
        (l.delay for l in dov.links if l.delay is not None)))
    except ValueError:
      sbb.resources.delay = None
    # Maximum available bandwidth value of infras and links in DoV
    try:
      max_bw = max(itertools.chain(
        (n.resources.bandwidth for n in dov.infras if
         n.resources.bandwidth is not None),
        (l.bandwidth for l in dov.links if l.bandwidth is not None)))
      # Number of infras and links in DoV
      sum_infra_link = sum(1 for _ in itertools.chain(dov.infras, dov.links))
      # Overestimate switching capacity to avoid false positive mapping result
      sbb.resources.bandwidth = max_bw * sum_infra_link
    except ValueError:
      sbb.resources.bandwidth = None
    log.debug("Computed SingleBiBBiS resources: %s" % sbb.resources)

    # Add supported types
    s_types = set()
    for infra in dov.infras:
      s_types = s_types.union(infra.supported)
    sbb.add_supported_type(s_types)
    log.debug("Add supported types: %s" % s_types)

    # Add existing SAPs and their connections to the SingleBiSBiS infra
    from copy import deepcopy
    for sap in dov.saps:
      c_sap = nffg.add_sap(sap=deepcopy(sap))
      log.debug("Add SAP: %s" % c_sap)
      # Discover and add SAP connections
      for u, v, l in dov.network.out_edges_iter([sap.id], data=True):
        link1, link2 = nffg.add_undirected_link(port1=c_sap.ports[l.src.id],
                                                port2=sbb.add_port(
                                                  "port-%s" % c_sap.id),
                                                p1p2id=l.id,
                                                delay=l.delay,
                                                bandwidth=l.bandwidth)
        log.debug("Add connection: %s" % link1)
        log.debug("Add connection: %s" % link2)
    log.debug("SingleBiSBiS generation has been finished!")
    # Return with Single BiSBiS infra
    return nffg


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
      "Invoke %s to get <Global Resource View>" % self.__class__.__name__)
    # If DoV is not set up, need to request from Adaptation layer
    if DoV not in self._virtualizers:
      log.debug("Missing <Global Resource View>! Requesting the View now...")
      self.raiseEventNoErrors(MissingGlobalViewEvent)
      if DoV in self._virtualizers and self._virtualizers[DoV] is not None:
        log.debug(
          "Got requested <Global Resource View>: %s" % self._virtualizers[DoV])
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
