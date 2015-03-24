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
from escape.util.nffg import NFFG
from escape.orchest.policy_enforcement import PolicyEnforcementMetaClass
from escape.orchest import log as log


class AbstractVirtualizer(object):
  """
  Abstract class for actual virtualizers

  Follows the Proxy design pattern
  """

  def __init__ (self):
    super(AbstractVirtualizer, self).__init__()

  def get_resource_info (self):
    raise NotImplementedError("Derived class have to override this function")


class ESCAPEVirtualizer(AbstractVirtualizer):
  """
  Actual virtualizer class for ESCAPE
  """
  __metaclass__ = PolicyEnforcementMetaClass

  def __init__ (self):
    super(ESCAPEVirtualizer, self).__init__()

  def get_resource_info (self):
    # dummy NFFG TODO - implement
    # deep copy???
    return NFFG()


class VirtualizerManager(object):
  """
  Store, handle and organize Virtualizer instances
  """

  def __init__ (self):
    super(VirtualizerManager, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self._virtualizers = dict()

  def get_global_domain_view (self):
    log.debug("Requesting Domain Virtualizer...")
    # If DoV is not set up, need to request from Adaptation layer
    if 'DoV' not in self._virtualizers:
      log.debug("Missing global view! Requesting global resource info...")
    log.debug("Got requested Domain Virtualizer")
    return self._virtualizers.get('DoV', None)

  def get_virtual_view (self, layer_id):
    # If this is the first request, need to generate the view
    if layer_id not in self._virtualizers:
      self.generate_virtual_view(self.get_global_domain_view(), layer_id)
    return self._virtualizers[layer_id]

  def generate_virtual_view (self, global_view, layer_id):
    # TODO - implement
    pass