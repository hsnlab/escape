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


class ESCAPEVirtualizer(AbstractVirtualizer):
  """
  Actual virtualizer class for ESCAPE
  """

  __metaclass__ = PolicyEnforcementMetaClass

  def __init__ (self):
    super(ESCAPEVirtualizer, self).__init__()


class VirtualizerManager(object):
  """
  Store, handle and organize Virtualizer instances
  """
  virtualizers = dict()

  def __init__ (self):
    super(VirtualizerManager, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    # TODO - request/get/create domain virtualizer
    self.virtualizers['DoV'] = NFFG()

  def get_domain_view (self):
    log.debug("Requesting Domain Virtualizer...")
    # TODO - implement
    log.debug("Got requested Domain virtualizer")
    return self.virtualizers.get('DoV', None)