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

  def __init__ (self):
    """
    Init.
    """
    super(AbstractVirtualizer, self).__init__()

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


class DefaultESCAPEVirtualizer(AbstractVirtualizer):
  """
  Actual Virtualizer class for ESCAPEv2.

  No filtering, just offer the whole global resource view.
  """

  def __init__ (self, global_view):
    """
    Init.

    :param global_view: virtualizer instance represents the global view
    :type global_view: :any:`virtualizer`
    """
    super(DefaultESCAPEVirtualizer, self).__init__()
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

  def sanity_check (self, nffg):
    """
    Placeholder method for policy checking.

    Return the virtual resource info for the post checker function.

    :return: virtual resource info
    :rtype: :any:`NFFG`
    """
    return self.global_view.get_resource_info()


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
    log.debug("Invoke %s to get global resource" % self.__class__.__name__)
    # If DoV is not set up, need to request from Adaptation layer
    if DoV not in self._virtualizers:
      log.debug("Missing global view! Requesting global resource info...")
      self.raiseEventNoErrors(MissingGlobalViewEvent)
      if self._virtualizers[DoV] is not None:
        log.debug("Got requested global resource info")
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
    :rtype: :any:`DefaultESCAPEVirtualizer`
    """
    log.debug("Invoke %s to get virtual resource view (for layer ID: %s)" % (
      self.__class__.__name__, virtualizer_id))
    # If this is the first request, need to generate the view
    if virtualizer_id not in self._virtualizers:
      # Pass the global resource as the DomainVirtualizer
      self._virtualizers[virtualizer_id] = self._generate_virtual_view(
        virtualizer_id)
    # Return Virtualizer
    return self._virtualizers[virtualizer_id]

  def _generate_virtual_view (self, layer_id):
    """
    Generate a missing :class:`DefaultESCAPEVirtualizer` for other layer
    using global view (DoV) and a given layer id.

    :param layer_id: layer ID
    :type layer_id: int
    :return: generated Virtualizer derived from AbstractVirtualizer
    :rtype: :any:`DefaultESCAPEVirtualizer`
    """
    log.debug(
      "Generating Virtualizer for upper layer (layer ID: %s)" % layer_id)
    # Requesting a reference to DoV and create a simple Virtualizer
    return DefaultESCAPEVirtualizer(self.dov)
