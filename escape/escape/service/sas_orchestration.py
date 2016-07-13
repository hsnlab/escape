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
Contains classes relevant to Service Adaptation Sublayer functionality.
"""
from escape.adapt.virtualization import AbstractVirtualizer
from escape.service import log as log, LAYER_NAME
from escape.service.sas_mapping import ServiceGraphMapper
from escape.util.mapping import AbstractOrchestrator, ProcessorError
from escape.util.misc import notify_remote_visualizer, VERBOSE
from pox.lib.revent.revent import EventMixin, Event


class MissingVirtualViewEvent(Event):
  """
  Event for signaling missing virtual resource view
  """
  pass


class ServiceOrchestrator(AbstractOrchestrator):
  """
  Main class for the actual Service Graph processing.
  """
  # Default Mapper class as a fallback mapper
  DEFAULT_MAPPER = ServiceGraphMapper

  def __init__ (self, layer_API):
    """
    Initialize main Service Layer components.

    :param layer_API: layer API instance
    :type layer_API: :any:`ServiceLayerAPI`
    :return: None
    """
    super(ServiceOrchestrator, self).__init__(layer_API=layer_API)
    log.debug("Init %s" % self.__class__.__name__)
    # Init SG Manager
    self.sgManager = SGManager()
    # Init virtual resource manager
    # Listeners must be weak references in order the layer API can garbage
    # collected
    self.virtResManager = VirtualResourceManager()
    self.virtResManager.addListeners(layer_API, weak=True)

  def initiate_service_graph (self, sg):
    """
    Main function for initiating Service Graphs.

    :param sg: service graph stored in NFFG instance
    :type sg: :any:`NFFG`
    :return: NF-FG description
    :rtype: :any:`NFFG`
    """
    log.debug("Invoke %s to initiate SG(id=%s)" %
              (self.__class__.__name__, sg.id))
    # Store newly created SG
    self.sgManager.save(sg)
    # Get virtual resource info as a Virtualizer
    virtual_view = self.virtResManager.virtual_view
    # Notify remote visualizer about resource view of this layer if it's needed
    notify_remote_visualizer(data=virtual_view.get_resource_info(),
                             id=LAYER_NAME)
    # Log verbose service request
    log.log(VERBOSE, "Service layer request graph:\n%s" % sg.dump())
    if virtual_view is not None:
      if isinstance(virtual_view, AbstractVirtualizer):
        # If the request is a bare NFFG, it is probably an empty topo for domain
        # deletion --> skip mapping to avoid BadInputException and forward
        # topo to adaptation layer
        if sg.is_bare():
          log.warning("No valid service request (VNFs/Flowrules/SGhops) has "
                      "been detected in SG request! Skip orchestration in "
                      "layer: %s and proceed with the bare %s..." %
                      (LAYER_NAME, sg))
          if sg.is_virtualized():
            if sg.is_SBB():
              log.debug("Request is a bare SingleBiSBiS representation!")
            else:
              log.warning("Detected virtualized representation with multiple "
                          "BiSBiS nodes! Currently this type of virtualization "
                          "is nut fully supported!")
          else:
            log.debug("Detected full view representation!")
          # Return with the original request
          return sg
        else:
          log.info("Request check: detected valid content!")
        try:
          # Run orchestration before service mapping algorithm
          mapped_nffg = self.mapper.orchestrate(sg, virtual_view)
          log.debug("SG initiation is finished by %s" % self.__class__.__name__)
          return mapped_nffg
        except ProcessorError as e:
          log.warning("Mapping pre/post processing was unsuccessful! "
                      "Cause: %s" % e)
      else:
        log.warning("Virtual view is not subclass of AbstractVirtualizer!")
    else:
      log.warning("Virtual view is not acquired correctly!")
    # Only goes there if there is a problem
    log.error("Abort orchestration process!")


class SGManager(object):
  """
  Store, handle and organize Service Graphs.

  Currently it just stores SGs in one central place.
  """

  def __init__ (self):
    """
    Init.
    """
    super(SGManager, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self._service_graphs = dict()

  def save (self, sg):
    """
    Save SG in a dict.

    :param sg: Service Graph
    :type sg: :any:`NFFG`
    :return: computed id of given Service Graph
    :rtype: int
    """
    sg_id = self._generate_id(sg)
    self._service_graphs[sg_id] = sg.copy()
    log.debug("SG: %s is saved by %s with id: %s" % (
      sg, self.__class__.__name__, sg_id))
    return sg.id

  def get (self, graph_id):
    """
    Return service graph with given id.

    :param graph_id: graph ID
    :type graph_id: int
    :return: stored Service Graph
    :rtype: :any:`NFFG`
    """
    return self._service_graphs.get(graph_id, None)

  def _generate_id (self, sg):
    """
    Try to generate a unique id for SG.

    :param sg: SG
    :type sg: :any:`NFFG`
    """
    tmp = sg.id if sg.id is not None else id(sg)
    if tmp in self._service_graphs:
      tmp = len(self._service_graphs)
      if tmp in self._service_graphs:
        for i in xrange(100):
          tmp += i
          if tmp not in self._service_graphs:
            return tmp
        else:
          raise RuntimeError("Can't be able to generate a unique id!")
    return tmp


class VirtualResourceManager(EventMixin):
  """
  Support Service Graph mapping, follow the used virtual resources according to
  the Service Graph(s) in effect.

  Handles object derived from :class`AbstractVirtualizer` and requested from
  lower layer.
  """
  # Events raised by this class
  _eventMixin_events = {MissingVirtualViewEvent}

  def __init__ (self):
    """
    Initialize virtual resource manager.

    :return: None
    """
    super(VirtualResourceManager, self).__init__()
    # Derived object from AbstractVirtualizer which represent the virtual
    # view of this layer
    self._virtual_view = None
    log.debug("Init %s" % self.__class__.__name__)

  @property
  def virtual_view (self):
    """
    Return resource info of actual layer as an :class:`NFFG
    <escape.util.nffg.NFFG>` instance.

    If it isn't exist requires it from Orchestration layer.

    :return: resource info as a Virtualizer
    :rtype: :any:`AbstractVirtualizer`
    """
    log.debug("Invoke %s to get the <Virtual View>" % self.__class__.__name__)
    if not self._virtual_view:
      log.debug("Missing <Virtual View>! Requesting <Virtual View> now...")
      self.raiseEventNoErrors(MissingVirtualViewEvent)
      if self._virtual_view is not None:
        log.debug("Got requested <Virtual View>: %s" % self._virtual_view)
    return self._virtual_view

  @virtual_view.setter
  def virtual_view (self, view):
    """
    Virtual view setter.

    :param view: virtual view
    :type view: :any:`AbstractVirtualizer`
    :return: None
    """
    self._virtual_view = view

  @virtual_view.deleter
  def virtual_view (self):
    """
    Virtual view deleter.

    :return: None
    """
    del self._virtual_view
