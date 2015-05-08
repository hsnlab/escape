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
Contains Adapter classes which represent the connections between ESCAPEv2 and
other different domains

:class:`AbstractDomainAdapter` contains general logic for actual Adapters

:class:`MininetDomainAdapter` implements Mininet related functionality

:class:`POXDomainAdapter` implements POX related functionality

:class:`OpenStackDomainAdapter` implements OpenStack related functionality
"""
from escape.adapt import log as log
from pox.lib.revent import Event, EventMixin


class DomainChangedEvent(Event):
  """
  Event class for signaling some kind of change(s) in specific domain
  """

  def __init__ (self, domain, cause, data=None):
    """
    Init event object

    :param domain: domain name
    :type domain: str
    :param cause: type of the domain change
    :type cause: str
    :param data: data connected to the change (optional)
    :type data: object
    :return: None
    """
    super(DomainChangedEvent, self).__init__()


class AbstractDomainAdapter(EventMixin):
  """
  Abstract class for different domain adapters

  Follows the Adapter design pattern (Adaptor base class)
  """
  # Events raised by this class
  _eventMixin_events = {DomainChangedEvent}

  def __init__ (self):
    """
    Init
    """
    super(AbstractDomainAdapter, self).__init__()

  def install (self, nffg):
    """
    Intall domain specific part of a mapped NFFG

    :param nffg: domain specific slice of mapped NFFG
    :type nffg: NFFG
    :return: None
    """
    raise NotImplementedError("Derived class have to override this function")

  def notify_change (self):
    """
    Notify other components (ControllerAdapter) about changes in specific domain
    """
    raise NotImplementedError("Derived class have to override this function")


class MininetDomainAdapter(AbstractDomainAdapter):
  """
  Adapter class to handle communication with Mininet

  .. warning::
    Not implemented yet!
  """

  def __init__ (self):
    """
    Init
    """
    super(MininetDomainAdapter, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)

  def install (self, nffg):
    log.info("Install Mininet domain part...")
    # TODO - implement
    pass

  def notify_change (self):
    # TODO - implement
    pass


class POXDomainAdapter(AbstractDomainAdapter):
  """
  Adapter class to handle communication with POX OpenFlow controller

  .. warning::
    Not implemented yet!
  """

  def __init__ (self):
    """
    Init
    """
    super(POXDomainAdapter, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)

  def install (self, nffg):
    log.info("Install POX domain part...")
    # TODO - implement
    pass

  def notify_change (self):
    # TODO - implement
    pass


class OpenStackDomainAdapter(AbstractDomainAdapter):
  """
  Adapter class to handle communication with OpenStack

  .. warning::
    Not implemented yet!
  """

  def __init__ (self):
    """
    Init
    """
    super(OpenStackDomainAdapter, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)

  def install (self, nffg):
    log.info("Install OpenStack domain part...")
    # TODO - implement
    pass

  def notify_change (self):
    # TODO - implement
    pass
