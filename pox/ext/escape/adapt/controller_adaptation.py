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
import weakref

from escape.orchest.virtualization_management import AbstractVirtualizer
from escape.adapt.domain_adapters import POXDomainAdapter, MininetDomainAdapter
from escape.adapt import log as log


class ControllerAdapter(object):
  """
  Higher-level class for NFFG adaptation between multiple domains
  """

  def __init__ (self):
    super(ControllerAdapter, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self.domainResManager = DomainResourceManager()
    self.pox = POXDomainAdapter()
    self.mininet = MininetDomainAdapter()

  def install_nffg (self, mapped_nffg):
    """
    Start NF-FG installation
    """
    log.debug("Invoke %s to install NF-FG" % self.__class__.__name__)
    # TODO - implement
    log.debug("NF-FG installation is finished by %s" % self.__class__.__name__)


class DomainVirtualizer(AbstractVirtualizer):
  """
  Specific virtualizer class for global domain virtualization

  Should implement the same interface as AbstractVirtualizer
  """

  def __init__ (self, domainResManager):
    super(DomainVirtualizer, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    # Garbage-collector safe
    self.domainResManager = weakref.proxy(domainResManager)

  def get_resource_info (self):
    # TODO - implement - possibly don't store anything just convert??
    pass


class DomainResourceManager(object):
  """
  Handle and store global resources
  """

  def __init__ (self):
    super(DomainResourceManager, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self._dov = DomainVirtualizer(self)

  @property
  def dov (self):
    return self._dov