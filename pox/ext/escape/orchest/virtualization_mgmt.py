# Copyright 2015 Janos Czentye
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
Contains components relevant to virtualization of resources and views

:class:`AbstractVirtualizer
<escape.orchest.virtualization_mgmt.AbstractVirtualizer>` contains the  central
logic of Virtualizers

:class:`ESCAPEVirtualizer` implement the standard virtualization logic of the
Resource Orchestration Sublayer

:class:`VirtualizerManager` stores and handles the virtualizers
"""
from escape.util.nffg import NFFG
from escape.orchest.policy_enforcement import PolicyEnforcementMetaClass
from escape.orchest import log as log


class AbstractVirtualizer(object):
  """
  Abstract class for actual Virtualizers

  Follows the Proxy design pattern
  """
  __metaclass__ = PolicyEnforcementMetaClass

  def __init__ (self):
    """
    Init
    """
    super(AbstractVirtualizer, self).__init__()

  def get_resource_info (self):
    """
    Hides object's mechanism and return with a resource object derived from
    :class:`NFFG <escape.util.nffg.NFFG>`

    :raise: NotImplementedError
    :return: resource info
    :rtype: NFFG
    """
    raise NotImplementedError("Derived class have to override this function")

  def sanity_check (self, nffg):
    """
    Place-holder for sanity check which implemented in
    :class:`PolicyEnforcement`
    """
    pass


class ESCAPEVirtualizer(AbstractVirtualizer):
  """
  Actual Virtualizer class for ESCAPEv2
  """

  def __init__ (self):
    """
    Init
    """
    super(ESCAPEVirtualizer, self).__init__()

  def get_resource_info (self):
    """
    Hides object's mechanism and return with a resource object derived from
    :class:`NFFG <escape.util.nffg.NFFG>`

    :return: virtual resource info
    :rtype: NFFG
    """
    # dummy NFFG TODO - implement
    # deep copy???
    log.debug("Return virtual resource info...")
    return self._generate_resource_info()

  def sanity_check (self, nffg):
    """
    Placeholder method for policy checking.

    Return the virtual resource info for the post checker function

    :return: virtual resource info
    :rtype: NFFG
    """
    return self._generate_resource_info()

  def _generate_resource_info (self):
    """
    Private method to return with resouce info
    """
    return NFFG()


DoV_ID = 'DoV'


class VirtualizerManager(object):
  """
  Store, handle and organize instances of derived classes of
  :class:`AbstractVirtualizer
  <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`
  """

  def __init__ (self, layerAPI):
    """
    Init

    :param layerAPI: Layer API object which contains this manager
    :type layerAPI: AbstractAPI
    :return: None
    """
    super(VirtualizerManager, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self._layerAPI = layerAPI
    self._virtualizers = dict()

  @property
  def dov (self):
    """
    Getter method for the :class:`DomainVirtualizer`

    Request DoV from Adaptation if it hasn't set yet

    Use: `virtualizerManager.dov`

    :return: Domain Virtualizer (DoV)
    :rtype: DomainVirtualizer
    """
    log.debug("Invoke %s to get global resource" % self.__class__.__name__)
    # If DoV is not set up, need to request from Adaptation layer
    if DoV_ID not in self._virtualizers:
      log.debug("Missing global view! Requesting global resource info...")
      self._layerAPI.request_domain_resource_info()
      if self._virtualizers[DoV_ID] is not None:
        log.debug("Got requested global resource info")
    # Return with resource info as a DomainVirtualizer
    return self._virtualizers.get(DoV_ID, None)

  @dov.setter
  def dov (self, dov):
    """
    DoV setter

    :param dov: Domain Virtualizer (DoV)
    :type dov: DomainVirtualizer
    :return: None
    """
    self._virtualizers[DoV_ID] = dov

  @dov.deleter
  def dov (self):
    """
    DoV deleter

    :return: None
    """
    del self._virtualizers[DoV_ID]

  def get_virtual_view (self, layer_id):
    """
    Return the virtual view as a derived class of :class:`AbstractVirtualizer
    <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`

    :param layer_id: layer ID
    :type layer_id: int
    :return: virtual view
    :rtype: ESCAPEVirtualizer
    """
    log.debug("Invoke %s to get virtual resource view (for layer ID: %s)" % (
      self.__class__.__name__, layer_id))
    # If this is the first request, need to generate the view
    if layer_id not in self._virtualizers:
      # Pass the global resource as the DomainVirtualizer
      self._virtualizers[layer_id] = self._generate_virtual_view(self.dov,
                                                                 layer_id)
    return self._virtualizers[layer_id]

  def _generate_virtual_view (self, dov, layer_id):
    """
    Generate a missing :class:`ESCAPEVirtualizer` for other layer using global
    view (DoV) and a layer id

    :param dov: Domain Virtualizer derived from AbstractVirtualizer
    :type dov: DomainVirtualizer
    :param layer_id: layer ID
    :type layer_id: int
    :return: generated Virtualizer derived from AbstractVirtualizer
    :rtype: ESCAPEVirtualizer
    """
    # TODO - implement
    resource_info = dov.get_resource_info()
    log.debug(
      "Generating virtual resource view for upper layer (layer ID: %s)" %
      layer_id)
    return ESCAPEVirtualizer()