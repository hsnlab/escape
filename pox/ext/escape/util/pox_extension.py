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
Override and extend internal POX components to achieve ESCAPE-desired behaviour
"""
from pox.core import core
from pox.openflow import OpenFlowConnectionArbiter, OpenFlowNexus, ConnectionIn


class OpenFlowBridge(OpenFlowNexus):
  """
  Own class for listening OpenFlow event originated by one of the contained
  :class:`Connection` and sending OpenFlow messages according to DPID

  Purpose of the class mostly fits the Bride design pattern
  """
  pass


class ExtendedOFConnectionArbiter(OpenFlowConnectionArbiter):
  """
  Extended connection arbiter class for dispatching incoming OpenFlow
  :class:`Connection` between registered OF event originators (
  :class:`OpenFlowNexus`) according to the connection's listening address
  """
  # core name to register the class as a OpenFlowConnectionArbiter
  _core_name = "OpenFlowConnectionArbiter"

  def __init__ (self, default=False):
    """
    Init

    :param default: inherited param
    :type default: :class:`OpenFlowNexus`
    """
    super(ExtendedOFConnectionArbiter, self).__init__(default)
    try:
      # Set original OpenFlow nexus as a last resort
      self._fallback = core.openflow
    except:
      # for safety reason
      core.getLogger().warning(
        "No default OpenFlow nexus is registered. Registering now...")
      core.core.register("openflow", OpenFlowNexus())
      self._fallback = core.openflow
      # registered nexus objects - key: (address, port)
    self._listeners = {}

  def add_connection_listener (self, address, nexus):
    """
    Helper function to register connection listeners a.k.a.
    :class:`OpenFlowNexus`

    :param address: listened socket name in form of (address, port)
    :type address: tuple
    :param nexus: registered object
    :type nexus: :class:`OpenFlowBridge`
    :return: registered listener
    :rtype: :class:`OpenFlowBridge`
    """
    self._listeners[address] = nexus

  @classmethod
  def activate (cls):
    """
    Register this component into ``pox.core`` and replace already registered
    Arbiter.

    :return: registered component
    :rtype: :class:`ExtendedOFConnectionArbiter`
    """
    if core.hasComponent(cls._core_name):
      # If the registered arbiter is our extended one skip registration
      if isinstance(core.components[cls._core_name], cls):
        return
      del core.components[cls._core_name]
    return core.core.registerNew(cls)

  def getNexus (self, connection):
    """
    Return registered connection listener or default ``core.openflow``.

    Fires ConnectionIn event.

    :param connection: incoming connection object
    :type connection: :class:`Connection`
    :return: OpenFlow event originator object
    :rtype: :class:`OpenFlowNexus`
    """
    event = ConnectionIn(connection)
    if self._default:
      # Set default value is exist
      event.nexus = self._default
    else:
      # No default
      con_address = connection.sock.getsockname()
      if con_address in self._listeners:
        # If there is registered listener
        event.nexus = self._listeners[con_address]
      else:
        # Fall back to core.openflow
        event.nexus = self._fallback
    self.raiseEventNoErrors(event)
    return event.nexus
