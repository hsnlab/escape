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
"""
Contains classes relevant to Service Adaptation Sublayer functionality

:class:`ServiceOrchestrator` orchestrates SG mapping and centralize layer logic

:class:`SGManager` stores and handles Service Graphs

:class:`VirtualResourceManager` contains the functionality tided to the
layer's virtual view and virtual resources

:class:`NFIBManager` handles the Network Function Information Base and hides
implementation dependent logic
"""
from escape.orchest.virtualization_mgmt import AbstractVirtualizer
from escape.service.sas_mapping import ServiceGraphMapper
from escape.service import log as log


class ServiceOrchestrator(object):
  """
  Main class for the actual Service Graph processing
  """

  def __init__ (self, virtResManager):
    """
    Initialize main Service Layer components

    :param virtResManager: virtual resource manager
    :type virtResManager: VirtualResourceManager
    :return: None
    """
    super(ServiceOrchestrator, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self.sgManager = SGManager()
    self.virtResManager = virtResManager
    self.sgMapper = ServiceGraphMapper()
    self.nfibManager = NFIBManager()

  def initiate_service_graph (self, sg):
    """
    Main function for initiating Service Graphs

    :param sg: service graph stored in NFFG instance
    :type sg: NFFG
    :return: NF-FG description
    :rtype: NFFG
    """
    log.debug("Invoke %s to initiate SG" % self.__class__.__name__)
    # Store newly created SG
    self.sgManager.save(sg)
    # Get virtual resource info as a Virtualizer
    virtual_view = self.virtResManager.virtual_view
    if virtual_view is not None:
      if isinstance(virtual_view, AbstractVirtualizer):
        # Run orchestration before service mapping algorithm
        nffg = self.sgMapper.orchestrate(sg, virtual_view)
        log.debug("SG initiation is finished by %s" % self.__class__.__name__)
        return nffg
      else:
        log.warning("Virtual view is not subclass of AbstractVirtualizer!")
    else:
      log.warning("Virtual view is not acquired correctly!")
    log.error("Abort mapping process!")


class SGManager(object):
  """
  Store, handle and organize Service Graphs

  Currently it just stores SGs in one central place
  """

  def __init__ (self):
    """
    Init
    """
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
  Support Service Graph mapping, follow the used virtual resources according to
  the Service Graph(s) in effect

  Handles object derived from :class`AbstractVirtualizer` and requested from
  lower layer
  """

  def __init__ (self, layerAPI):
    """
    Initialize virtual resource manager

    :param layerAPI: layer API object which contain this manager
    :type layerAPI: ServiceLayerAPI
    :return: None
    """
    super(VirtualResourceManager, self).__init__()
    # service layer API for communication with other layers
    self._layerAPI = layerAPI
    # Derived object from AbstractVirtualizer which represent the virtual
    # view of this layer
    self._virtual_view = None
    log.debug("Init %s" % self.__class__.__name__)

  @property
  def virtual_view (self):
    """
    Return resource info of actual layer as an :class:`NFFG
    <escape.util.nffg.NFFG>` instance

    If it isn't exist requires it from Orchestration layer

    :return: resource info as a Virtualizer
    :rtype: AbstractVirtualizer
    """
    log.debug("Invoke %s to get virtual resource" % self.__class__.__name__)
    if not self._virtual_view:
      log.debug("Missing virtual view! Requesting virtual resource info...")
      self._layerAPI.request_virtual_resource_info()
      if self._virtual_view is not None:
        log.debug("Got requested virtual resource info")
    return self._virtual_view

  @virtual_view.setter
  def virtual_view (self, view):
    """
    Virtual view setter

    :param view: virtual view
    :type view: AbstractVirtualizer
    :return: None
    """
    self._virtual_view = view

  @virtual_view.deleter
  def virtual_view (self):
    """
    Virtual view deleter

    :return: None
    """
    del self._virtual_view


class NFIBManager(object):
  """
  Manage the handling of Network Function Information Base
  """

  def __init__ (self):
    """
    Init
    """
    super(NFIBManager, self).__init__()