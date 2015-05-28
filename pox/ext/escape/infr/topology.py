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
Wrapper module for handling emulated test topology based on Mininet
"""
from escape.infr import log
from escape.util.nffg import NFFG
from mininet.net import VERSION as MNVERSION
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.topo import Topo


class AbstractTopology(Topo):
  """
  Abstract class for representing emulated topology

  Can be used to define reusable topology similar to Mininet's high-level API
  """

  def __init__ (self, hopts=None, sopts=None, lopts=None, eopts=None):
    super(AbstractTopology, self).__init__(hopts, sopts, lopts, eopts)
    # TODO - extend and implement


class InternalControllerProxy(RemoteController):
  """
  Controller class for emulated Mininet network. Making connection with
  internal controller initiated by POXDomainAdapter.
  """

  def __init__ (self, name="InternalPOXController", ip='127.0.0.1', port=6653,
       **kwargs):
    """
    Init

    :param name: name of the controller (default: InternalPOXController)
    :type name: str
    :param ip: IP address (default: 127.0.0.1)
    :type ip: str
    :param port: port number (default 6633)
    :type port: int
    """
    super(InternalControllerProxy, self).__init__(name, ip, port, **kwargs)

  def checkListening (self):
    """
    Check the controller port is open
    """
    listening = self.cmd("echo A | telnet -e A %s %d" % (self.ip, self.port))
    if 'Connected' not in listening:
      log.debug(
        "Unable to contact with internal controller at %s:%d. Waiting..." % (
          self.ip, self.port))


class NetworkWrapper(object):
  """
  Wrapper class for Mininet topology

  Represents a container class for network elements such as switches, nodes,
  execution evironments, links etc.

  Contains network management functions similar to Mininet's mid-level API
  extendend with ESCAPEv2 related capabilities
  """

  def __init__ (self, topology=None):
    """
    Initialize NetworkWrapper. Set up emulated network from _topology_ if it
    is given.

    :param topology: network representation
    :type topology: :any:`NFFG` or :any:`dict` or :any:`AbstractTopology`
    """
    log.debug(
      "Init %s based on Mininet v%s" % (self.__class__.__name__, MNVERSION))
    super(NetworkWrapper, self).__init__()
    self._net = None
    if topology:
      self.initialize(topology)

  @property
  def network (self):
    """
    Internal network representation

    :return: network representation
    :rtype: :class:`mininet.net.Mininet`
    """
    return self._net

  def __init_from_NFFG (self, nffg):
    """
    Initialize topology from :any:`NFFG`

    :param nffg: topology
    :type nffg: :any:`NFFG`
    :return: None
    """
    # TODO -implement
    pass

  def __init_from_dict (self, topology):
    """
    Initialize topology from a dictionary.

    Keywords for network elements: controllers, ee, saps, switches, links

    Option keywords: netopts

    :param topology: topology
    :type topology: :any:`NFFG`
    :return: None
    """
    # TODO - implement
    pass

  def __init_from_AbstractTopology (self, topology):
    """
    Build topology from pre-defined Topology class

    :param topology: topology
    :type topology: :any:`AbstractTopology`
    :return: None
    """
    # TODO - implement
    pass

  def initialize (self, topology=None, wait_for_controller=True):
    """
    Initialize network

    :param topology: topology representation
    :type topology: :any:`NFFG` or :any:`dict` or :any:`AbstractTopology`
    :param wait_for_controller: wait for POXDomainAdapter (default: True)
    :return: None
    """
    if isinstance(topology, NFFG):
      self.__init_from_NFFG(topology)
    elif isinstance(topology, dict):
      self.__init_from_dict(topology)
    elif isinstance(topology, AbstractTopology):
      self.__init_from_AbstractTopology(topology)
    # start network
    if not wait_for_controller:
      self.start_network()

  def start_network (self):
    """
    Start network
    """
    log.debug("Starting Mininet network...")
    if self._net:
      self._net.start()
      log.debug("Mininet network has been started!")
    else:
      log.error("Missing topology! Skipping emulation and running dry...")

  def stop_network (self):
    """
    Stop network
    """
    log.debug("Shutting down Mininet network...")
    if self._net:
      self._net.stop()

  def test_network (self):
    """
    For testing
    """
    log.debug("Init simple switch topo for testing purposes")
    # self._net = Mininet(topo=SingleSwitchTopo(2), controller=RemoteController)
    net = Mininet()
    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    s1 = net.addSwitch('s1')
    c0 = net.addController('c0', InternalControllerProxy)
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    self._net = net
