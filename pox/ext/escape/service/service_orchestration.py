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
    self.sgManager = SGManager()
    self.virtResManager = virtResManager
    self.sgMapper = ServiceGraphMapper()
    self.nfibManager = NFIBManager()

  def initiate_service_graph (self, sg):
    """
    Main function for initiating Service Graphs

    :param sg: service graph storeg in NFFG instance
    :type sg: NFFG
    :return: NF-FG description
    :rtype: NFFG
    """
    log.debug("Invoke %s to initiate SG" % self.__class__.__name__)
    # Store newly created SG
    self.sgManager.save(sg)
    # Get virtual resource info as a Virtualizer
    virtual_view = self.virtResManager.get_virtual_resource_view()
    # Run service mapping algorithm
    nffg = self.sgMapper.orchestrate(sg, virtual_view)
    log.debug("SG initiation is finished by %s" % self.__class__.__name__)
    return nffg


class SGManager(object):
  """
  Store, handle and organize Service Graphs

  Currently it just stores SGs in one central place
  """

  def __init__ (self):
    super(SGManager, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self._service_graphs = dict()

  def save (self, sg):
    """
    Save SG in a dict

    :param sg: Service Graph
    :type sg: NFFG
    :return: computed id of given Service Graph
    :rtype: int
    """
    sg.id = len(self._service_graphs)
    self._service_graphs[sg.id] = sg
    log.debug(
      "SG is saved by %s with id: %s" % (self.__class__.__name__, sg.id))
    return sg.id

  def get (self, graph_id):
    """
    Return service graph with given id

    :param graph_id: graph ID
    :type graph_id: int
    :return: stored Service Graph
    :rtype: NFFG
    """
    return self._service_graphs.get(graph_id, None)


class VirtualResourceManager(object):
  """
  Support Service Graph mapping, follows the used virtual resources according to
  the Service Graph(s) in effect
  Handles object derived from AbstractVirtualizer and requested from lower layer
  """

  def __init__ (self, layerAPI):
    super(VirtualResourceManager, self).__init__()
    # service layer API for comminucation with other layers
    self._layerAPI = layerAPI
    # Derived object from AbstractVirtualizer which represent the virtual
    # view of this layer
    self._virtual_view = None
    log.debug("Init %s" % self.__class__.__name__)

  def get_virtual_resource_view (self):
    """
    Return resource info of actual layer as an NFFG instance
    If it isn't exist reqiures it from Orchestration layer

    :return: resource info as a Virtualizer
    :rtype: ESCAPEVirtualizer
    """
    log.debug("Invoke %s to get virtual resource" % self.__class__.__name__)
    if not self.virtual_view:
      log.debug("Missing virtual view! Requesting virtual resource info...")
      self._layerAPI.request_virtual_resource_info()
      log.debug("Got requested virtual resource info")
    return self.virtual_view

  @property
  def virtual_view (self):
    """
    Virtual view getter
    """
    return self._virtual_view

  @virtual_view.setter
  def virtual_view (self, view):
    """
    Virtual view setter
    """
    self._virtual_view = view

  @virtual_view.deleter
  def virtual_view (self):
    """
    Virtual view deleter
    """
    del self.virtual_view


class NFIBManager(object):
  """
  Manage the handling of Network Function Information Base
  """

  def __init__ (self):
    super(NFIBManager, self).__init__()