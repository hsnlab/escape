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
Contains classes relevant to Resource Orchestration Sublayer functionality
"""
from escape.orchest.ros_mapping import ResourceOrchestrationMapper
from escape.orchest import log as log
from escape.orchest.virtualization_mgmt import AbstractVirtualizer, \
  VirtualizerManager


class ResourceOrchestrator(object):
  """
  Main class for the handling of the ROS-level mapping functions
  """

  def __init__ (self, layer_API):
    """
    Initialize main Resource Orchestration Layer components

    :param layer_API: layer API instance
    :type layer_API: ResourceOrchestrationAPI
    :return: None
    """
    super(ResourceOrchestrator, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self.nffgManager = NFFGManager()
    # Init virtualizer manager
    # Listeners must be weak references in order the layer API can garbage
    # collected
    self.virtualizerManager = VirtualizerManager()
    self.virtualizerManager.addListeners(layer_API, weak=True)
    # Init Resource Orchestration Mapper
    # Listeners must be weak references in order the layer API can garbage
    # collected
    self.nffgMapper = ResourceOrchestrationMapper()
    self.nffgMapper.addListeners(layer_API, weak=True)
    # Init NFIB manager
    self.nfibManager = NFIBManager()

  def instantiate_nffg (self, nffg):
    """
    Main API function for NF-FG instantiation

    :param nffg: NFFG instance
    :type nffg: NFFG
    :return: mapped NFFG instance
    :rtype: NFFG
    """
    log.debug("Invoke %s to instantiate NF-FG" % self.__class__.__name__)
    # Store newly created NF-FG
    self.nffgManager.save(nffg)
    # Get Domain Virtualizer to acquire global domain view
    global_view = self.virtualizerManager.dov
    if global_view is not None:
      if isinstance(global_view, AbstractVirtualizer):
        # Run Nf-FG mapping orchestration
        mapped_nffg = self.nffgMapper.orchestrate(nffg, global_view)
        log.debug(
          "NF-FG instantiation is finished by %s" % self.__class__.__name__)
        return mapped_nffg
      else:
        log.warning("Global view is not subclass of AbstractVirtualizer!")
    else:
      log.warning("Global view is not acquired correctly!")
    log.error("Abort mapping process!")


class NFFGManager(object):
  """
  Store, handle and organize Network Function Forwarding Graphs
  """

  def __init__ (self):
    """
    Init
    """
    super(NFFGManager, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self._nffgs = dict()

  def save (self, nffg):
    """
    Save NF-FG in a dict

    :param nffg: Network Function Forwarding Graph
    :type nffg: NFFG
    :return: generated ID of given NF-FG
    :rtype: int
    """
    nffg.id = len(self._nffgs)
    self._nffgs[nffg.id] = nffg
    log.debug(
      "NF-FG is saved by %s with id: %s" % (self.__class__.__name__, nffg.id))
    return nffg.id

  def get (self, nffg_id):
    """
    Return NF-FG with given id

    :param nffg_id: ID of NF-FG
    :type nffg_id: int
    :return: NF-Fg instance
    :rtype: NFFG
    """
    return self._nffgs.get(nffg_id, default=None)


class NFIBManager(object):
  """
  Manage the handling of Network Function Information Base
  """

  def __init__ (self):
    """
    Init
    """
    super(NFIBManager, self).__init__()

  def add(self, nf):
    # TODO - implement
    pass

  def remove(self, nf_id):
    # TODO - implement
    pass

  def getNF(self, nf_id):
    # TODO - implement
    pass