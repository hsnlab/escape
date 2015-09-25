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

from escape.util.nffg import NFFG

if 'DoV' not in globals():
  try:
    from escape.adapt.adaptation import DoV
  except ImportError:
    DoV = "DoV"
from escape.orchest.policy_enforcement import PolicyEnforcementMetaClass
from escape.orchest import log as log
from pox.lib.revent.revent import EventMixin, Event


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

  def __init__ (self, id):
    """
    Init.

    :param id: id of the assigned entity
    :type: id: str
    """
    super(AbstractVirtualizer, self).__init__()
    self.id = id

  def __str__ (self):
    return "%s(assigned=%s)" % (self.__class__.__name__, self.id)

  def __repr__ (self):
    return super(AbstractVirtualizer, self).__repr__()

  def get_resource_info (self):
    """
    Hides object's mechanism and return with a resource object derived from
    :any:`NFFG`.

    .. warning::
      Derived class have to override this function

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
    super(GlobalViewVirtualizer, self).__init__(id=id)
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
    super(SingleBiSBiSVirtualizer, self).__init__(id=id)
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
    dov = self.global_view.get_resource_info()
    # Create the single BiSBiS infra
    sbb = nffg.add_infra(id="SingleBiSbiS", name="Single-BiSBiS",
                         domain=NFFG.DOMAIN_VIRTUAL,
                         infra_type=NFFG.TYPE_INFRA_BISBIS)
    log.debug("Add Infra BiSBiS: %s" % sbb)

    # Compute and add resources
    sbb.resources.cpu = sum(
      # Sum of available CPU
      (n.resources.cpu for n in dov.infras if
       n.resources.cpu is not None))
    sbb.resources.mem = sum(
      # Sum of available memory
      (n.resources.mem for n in dov.infras if
       n.resources.mem is not None))
    sbb.resources.storage = sum(
      # Sum of available storage
      (n.resources.storage for n in dov.infras if
       n.resources.storage is not None))
    sbb.resources.delay = min(
      # Minimal available delay value of infras in DoV
      min((n.resources.delay for n in dov.infras if
           n.resources.delay is not None)),
      # Minimal available delay value of inter-infra links
      min((l.delay for l in dov.links if l.delay is not None)))
    max_bw = max(
      # Maximum available bandwidth value of infras in DoV
      max((n.resources.bandwidth for n in dov.infras if
           n.resources.bandwidth is not None)),
      # Maximum available bandwidth value of inter-infra links
      max(l.bandwidth for l in dov.links if l.bandwidth is not None))
    infra_count = reduce(lambda a, b: a + 1, dov.infras, 0)
    link_count = reduce(lambda a, b: a + 1, dov.links, 0)

    # Maximum usable/reducible amount of bw to avoid false negative mapping
    # errors
    sbb.resources.bandwidth = max_bw * (infra_count + link_count)
    log.debug("Set infra's resources: %s" % sbb.resources)

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
                                                port2=sbb.add_port(),
                                                p1p2id=l.id,
                                                delay=l.delay,
                                                bandwidth=l.bandwidth)
        log.debug("Add connection: %s" % link1)
        log.debug("Add connection: %s" % link2)
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

  def get_virtual_view (self, virtualizer_id):
    """
    Return the Virtual View as a derived class of :class:`AbstractVirtualizer
    <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`.

    :param virtualizer_id: unique id of the requested Virtual view
    :type virtualizer_id: int or str
    :return: virtual view
    :rtype: :any:`AbstractVirtualizer`
    """
    log.debug("Invoke %s to get <Virtual View> (for layer ID: %s)" % (
      self.__class__.__name__, virtualizer_id))
    # If this is the first request, need to generate the view
    if virtualizer_id not in self._virtualizers:
      # Pass the global resource as the DomainVirtualizer
      self._virtualizers[virtualizer_id] = self._generate_virtual_view(
        virtualizer_id)
    # Return Virtualizer
    return self._virtualizers[virtualizer_id]

  def _generate_virtual_view (self, id):
    """
    Generate a missing :class:`SingleBisBisVirtualizer` for other layer
    using global view (DoV) and a given layer id.

    :param id: layer ID
    :type id: int
    :return: generated Virtualizer derived from AbstractVirtualizer
    :rtype: :any:`SingleBiSBiSVirtualizer`
    """
    log.debug("Generating Virtualizer for upper layer (layer ID: %s)" % id)
    # Requesting a reference to DoV and create the trivial 1 Bis-Bis virtual
    # view
    return SingleBiSBiSVirtualizer(self.dov, id)

  def generate_single_view (self, id):
    """
    Generate a Single BiSBiS virtualizer, store and return with it.

    :param id: unique virtualizer id
    :type id: int or str
    :return: generated Virtualizer
    :rtype: :any:`SingleBiSBiSVirtualizer`
    """
    if id in self._virtualizers:
      log.warning(
        "Requested Single BiS-BiS Virtualizer with ID: %s is already exist! "
        "Virtualizer creation skipped..." % id)
    else:
      self._virtualizers[id] = SingleBiSBiSVirtualizer(self.dov, id)
    return self._virtualizers[id]
