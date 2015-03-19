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
from escape.service.service_mapping import ServiceGraphMapper
from escape.util.nffg import NFFG
from escape.service import log as log


class ServiceOrchestrator(object):
  """
  Main class for the actual Service Graph processing
  """

  def __init__ (self):
    super(ServiceOrchestrator, self).__init__()
    self.sg_manager = SGManager()
    self.virt_res_manager = VirtualResourceManager()
    self.sg_mapper = ServiceGraphMapper()

  def initiate_service_graph (self, sg):
    log.info("Invoke Service Orchestrator component to handle given SG")
    # Store newly created SG
    self.sg_manager.save(sg)
    # Get virtual resource info
    virt_resource = self.virt_res_manager.get_virtual_resouce_info()
    # Run mapping algoritm
    return self.sg_mapper.orchestrate(sg, virt_resource)


class SGManager(object):
  """
  Store, handle and organize Service Graphs

  Currently it just stores SGs in one central place
  """
  service_graphs = dict()

  def __init__ (self):
    super(SGManager, self).__init__()

  def save (self, sg):
    """
    Save SG in a dict

    :param sg:
    :return: computed id of given SG
    """
    graph_id = len(self.service_graphs)
    self.service_graphs[graph_id] = sg
    log.info("SG is saved by SGManager")
    return graph_id

  def get (self, graph_id):
    """
    Return service graph with given id
    """
    return self.service_graphs[graph_id]


class VirtualResourceManager(object):
  """
  Support Service Graph mapping, follows the used virtual resources according to
  the Service Graph(s) in effect
  """

  def __init__ (self):
    super(VirtualResourceManager, self).__init__()

  def get_virtual_resouce_info (self):
    log.info("Requesting virtual resource info")
    # TODO - implement
    return NFFG()


class NFIBManager(object):
  """
  Manage the handling of Network Function Information Base
  """

  def __init__ (self):
    super(NFIBManager, self).__init__()