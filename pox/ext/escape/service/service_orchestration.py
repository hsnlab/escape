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
from escape.service import log as log


class ServiceOrchestrator(object):
  """
  Main class for the actual Service Graph processing
  """

  def __init__ (self, virtResManager):
    super(ServiceOrchestrator, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self.sg_manager = SGManager()
    self.virtResManager = virtResManager
    self.sg_mapper = ServiceGraphMapper()

  def initiate_service_graph (self, sg):
    log.debug("Invoke %s to initiate SG" % self.__class__.__name__)
    # Store newly created SG
    self.sg_manager.save(sg)
    # Get virtual resource info
    virt_resource = self.virtResManager.get_virtual_resouce_info()
    # Run service mapping algorithm
    nffg = self.sg_mapper.orchestrate(sg, virt_resource)
    log.debug("SG initiation is finished by %s" % self.__class__.__name__)
    return nffg


class SGManager(object):
  """
  Store, handle and organize Service Graphs

  Currently it just stores SGs in one central place
  """
  service_graphs = dict()

  def __init__ (self):
    super(SGManager, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)

  def save (self, sg):
    """
    Save SG in a dict

    :param sg: Service Graph
    :return: computed id of given SG
    """
    sg.id = len(self.service_graphs)
    self.service_graphs[sg.id] = sg
    log.debug(
      "SG is saved by %s with id: %s" % (self.__class__.__name__, sg.id))
    return sg.id

  def get (self, graph_id):
    """
    Return service graph with given id
    """
    return self.service_graphs.get(graph_id, None)


class VirtualResourceManager(object):
  """
  Support Service Graph mapping, follows the used virtual resources according to
  the Service Graph(s) in effect
  """

  def __init__ (self, serviceAPI):
    super(VirtualResourceManager, self).__init__()
    # service layer API for comminucation with other layers
    self.serviceAPI = serviceAPI
    # NFFG object which represent the virtual view of this layer
    self._virtual_view = None
    log.debug("Init %s" % self.__class__.__name__)

  def get_virtual_resouce_info (self):
    log.debug("Invoke %s to get virtual view" % self.__class__.__name__)
    if not self.virtual_view:
      log.debug("Missing virtual view! Requesting virtual resource info...")
      self.serviceAPI.get_virtual_resource_info()
    log.debug("Got requested virtual resource info")
    return self.virtual_view

  @property
  def virtual_view (self):
    return self._virtual_view

  @virtual_view.setter
  def virtual_view (self, virtual_view):
    self._virtual_view = virtual_view


class NFIBManager(object):
  """
  Manage the handling of Network Function Information Base
  """

  def __init__ (self):
    super(NFIBManager, self).__init__()