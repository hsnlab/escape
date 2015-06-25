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
from mininet.net import VERSION as MNVERSION
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.topo import Topo

from escape.infr import log
from escape.util.nffg import NFFG


class AbstractTopology(Topo):
  """
  Abstract class for representing emulated topology.

  Have the functions to build a ESCAPE-specific topology.

  Can be used to define reusable topology similar to Mininet's high-level API.
  Reusable, convenient and pre-defined way to define a topology, but less
  flexible and powerful.
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


class ESCAPENetworkBridge(object):
  """
  Internal class for representing the emulated topology.

  Represents a container class for network elements such as switches, nodes,
  execution environments, links etc. Contains network management functions
  similar to Mininet's mid-level API extended with ESCAPEv2 related capabilities

  Separate the interface using internally from original Mininet object to
  implement loose coupling and avoid changes caused by Mininet API changes
  e.g. 2.1.0 -> 2.2.0

  Follows Bridge design pattern.
  """

  def __init__ (self, network=None):
    """
    Initialize Mininet implementation with proper attributes.
    """
    log.debug(
      "Init %s based on Mininet v%s" % (self.__class__.__name__, MNVERSION))
    if network:
      self.__mininet = network
    else:
      log.warning(
        "Network implementation object is missing! Using bare Mininet "
        "object...")
      self.__mininet = Mininet(controller=InternalControllerProxy)

  @property
  def network (self):
    """
    Internal network representation

    :return: network representation
    :rtype: :class:`mininet.net.Mininet`
    """
    return self.__mininet

  def start_network (self):
    """
    Start network
    """
    log.debug("Starting Mininet network...")
    if self.__mininet:
      self.__mininet.start()
      log.debug("Mininet network has been started!")
    else:
      log.error("Missing topology! Skipping emulation and running dry...")

  def stop_network (self):
    """
    Stop network
    """
    log.debug("Shutting down Mininet network...")
    if self.__mininet:
      self.__mininet.stop()

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
    self.__mininet = net


class NetworkBuilder(object):
  """
  Builder class for topology.

  Update the network object based on the parameters if it's given or create
  an empty instance.

  Always return with an ESCAPENetworkBridge instance which offer a generic
  interface for created :any:`Mininet` object and hide implementation's nature.

  Follows Builder design pattern.
  """

  def __init__ (self, net=None):
    """
    Initialize NetworkBuilder.
    """
    if net:
      if isinstance(net, Mininet):
        self.topo = net
      else:
        raise RuntimeError(
          "Network object's type must be a derived class of Mininet!")
    else:
      self.topo = Mininet()

  def __init_from_NFFG (self, net, nffg):
    """
    Initialize topology from :any:`NFFG`

    :param nffg: topology
    :type nffg: :any:`NFFG`
    :return: None
    """
    # TODO -implement
    raise NotImplementedError()

  def __init_from_dict (self, dict):
    """
    Initialize topology from a dictionary.

    Keywords for network elements: controllers, ee, saps, switches, links

    Option keywords: netopts

    :param dict: topology
    :type dict: :any:`NFFG`
    :return: None
    """
    # TODO - implement
    raise NotImplementedError()

  def __init_from_AbstractTopology (self, topo):
    """
    Build topology from pre-defined Topology class

    :param topo: topology
    :type topo: :any:`AbstractTopology`
    :return: None
    """
    # TODO - implement
    raise NotImplementedError()

  def __init_from_CONFIG (self):
    """
    Build a pre-defined topology stored in CONFIG.

    :return: None
    """
    raise NotImplementedError()

  def __init_from_file (self, path):
    """
    Build a pre-defined topology stored in a file.

    :param path: file path
    :type path: str
    :return: None
    """
    raise NotImplementedError()

  def build (self, topology=None):
    """
    Initialize network

    :param topology: topology representation
    :type topology: :any:`NFFG` or :any:`dict` or :any:`AbstractTopology`
    :return: None
    """
    # TODO - initial settings
    if isinstance(topology, NFFG):
      self.__init_from_NFFG(nffg=topology)
    elif isinstance(topology, dict):
      self.__init_from_dict(dict=topology)
    elif isinstance(topology, AbstractTopology):
      self.__init_from_AbstractTopology(topo=topology)
    elif isinstance(topology, str):
      self.__init_from_file(path=topology)
    elif topology is None:
      log.debug("Topology description is missing. Try to load from CONFIG...")
      self.__init_from_CONFIG()
    else:
      raise RuntimeError("Unsupported topology format: %s" % type(topology))
      # TODO - return with Interface object
