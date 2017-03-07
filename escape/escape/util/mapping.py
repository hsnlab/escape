# Copyright 2017 Janos Czentye
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
Contains abstract classes for NFFG mapping.
"""
import threading

from escape.util.config import CONFIG
from escape.util.misc import call_as_coop_task
from pox.core import core
from pox.lib.revent.revent import EventMixin, Event


class AbstractMappingStrategy(object):
  """
  Abstract class for the mapping strategies.

  Follows the Strategy design pattern.
  """

  def __init__ (self):
    """
    Init.

    :return: None
    """
    super(AbstractMappingStrategy, self).__init__()

  @classmethod
  def map (cls, graph, resource):
    """
    Abstract function for mapping algorithm.

    .. warning::
      Derived class have to override this function

    :param graph: Input graph which need to be mapped
    :type graph: :class:`NFFG`
    :param resource: resource info
    :type resource: :class:`NFFG`
    :raise: :any:`exceptions.NotImplementedError`
    :return: mapped graph
    :rtype: :class:`NFFG`
    """
    raise NotImplementedError


class ProcessorError(Exception):
  """
  Specific error signaling characteristics (one or more) does not meet the
  requirements checked and/or defined in a inherited class
  of :any:`ProcessorError`.
  """
  pass


class AbstractMappingDataProcessor(object):
  """
  Abstract class for contain and perform validation steps.
  """

  def __init__ (self, layer_name):
    """
    Init.

    :param layer_name: layer name
    :type layer_name: str
    :return: None
    """
    super(AbstractMappingDataProcessor, self).__init__()
    self._layer_name = layer_name

  def pre_mapping_exec (self, input_graph, resource_graph):
    """
    Invoked right before the mapping algorithm.

    The given attributes are direct reference to the :class:`NFFG` objects
    which are forwarded to the algorithm.

    If there is a return value considering True (True, not-empty container,
    collection, an object reference etc.) or a kind of specific
    :any:`ProcessorError` is thrown in the function the mapping process will be
    skipped and the orchestration process will be aborted.

    The Validator instance is created during the initialization of ESCAPEv2
    and used the same instance before or after every mapping process to provide
    a persistent way to cache data between validations.

    :param input_graph: graph representation which need to be mapped
    :type input_graph: :class:`NFFG`
    :param resource_graph: resource information
    :type resource_graph: :class:`NFFG`
    :return: need to abort the mapping process
    :rtype: bool or None
    """
    raise NotImplementedError

  def post_mapping_exec (self, input_graph, resource_graph, result_graph):
    """
    Invoked right after if the mapping algorithm is completed without an error.

    The given attributes are direct reference to the :class:`NFFG` objects
    the mapping algorithm is worked on.

    If there is a return value considering True (e.g. True, not-empty
    container, collection, an object reference etc.) or a kind of specific
    :any:`ProcessorError` is thrown in the function the orchestration process
    will be aborted.

    :param input_graph: graph representation which need to be mapped
    :type input_graph: :class:`NFFG`
    :param resource_graph: resource information
    :type resource_graph: :class:`NFFG`
    :param result_graph: result of the mapping process
    :type result_graph: :class:`NFFG`
    :return: need to abort the mapping process
    :rtype: bool or None
    """
    raise NotImplementedError


class ProcessorSkipper(AbstractMappingDataProcessor):
  """
  Default class for skipping validation and proceed to mapping algorithm.
  """

  def pre_mapping_exec (self, input_graph, resource_graph):
    """
    Skip the validation by default and return with successful result.

    :return: successful result (False)
    :rtype: bool
    """
    return False

  def post_mapping_exec (self, input_graph, resource_graph, result_graph):
    """
    Skip the validation ba default and return with successful result.

    :return: successful result (False)
    :rtype: bool
    """
    return False


class PrePostMapNotifier(AbstractMappingDataProcessor):
  """
  Notifier class for notifying other POX modules about pre/post map event.

  For future features, currently AbstractMapper explicitly raise the event.
  """

  def pre_mapping_exec (self, input_graph, resource_graph):
    """
    Raise specific event for pre-mapping validation. Default return value is
    skip validation.

    :param input_graph: graph representation which need to be mapped
    :type input_graph: :class:`NFFG`
    :param resource_graph: resource information
    :type resource_graph: :class:`NFFG`
    :return: successful result (False)
    :rtype: bool
    """
    # Raise event for external POX modules
    core.components[self._layer_name].raiseEvent(PreMapEvent,
                                                 input_graph=input_graph,
                                                 resource_graph=resource_graph)
    # Return everything is OK.
    return False

  def post_mapping_exec (self, input_graph, resource_graph, result_graph):
    """
    Raise specific event for post-mapping validation. Default return value is
    skip validation.

    :param input_graph: graph representation which need to be mapped
    :type input_graph: :class:`NFFG`
    :param resource_graph: resource information
    :type resource_graph: :class:`NFFG`
    :param result_graph: result of the mapping process
    :type result_graph: :class:`NFFG`
    :return: successful result (False)
    :rtype: bool
    """
    # Raise event for external POX modules
    core.components[self._layer_name].raiseEvent(PostMapEvent,
                                                 input_graph=input_graph,
                                                 resource_graph=resource_graph,
                                                 result_graph=result_graph)
    # Return everything is OK.
    return False


class PreMapEvent(Event):
  """
  Raised before the request graph is mapped to the (virtual) resources.

  Event handlers might modify the request graph, for example, to
  enforce some decomposition rules.
  """

  def __init__ (self, input_graph, resource_graph):
    """
    Init.

    :param input_graph: graph representation which need to be mapped
    :type input_graph: :class:`NFFG`
    :param resource_graph: resource information
    :type resource_graph: :class:`NFFG`
    :return: None
    """
    super(PreMapEvent, self).__init__()
    self.input_graph = input_graph
    self.resource_graph = resource_graph

  @property
  def sg (self):
    """
    For support backward compatibility.

    :return: input graph
    :rtype: :class:`NFFG`
    """
    return self.input_graph


class PostMapEvent(Event):
  """
  Raised after the request graph is mapped to the (virtual) resources.

  Event handlers might modify the mapped request graph.
  """

  def __init__ (self, input_graph, resource_graph, result_graph):
    """
    Init.

    :param input_graph: graph representation which need to be mapped
    :type input_graph: :class:`NFFG`
    :param resource_graph: resource information
    :type resource_graph: :class:`NFFG`
    :param result_graph: result of the mapping process
    :type result_graph: :class:`NFFG`
    :return: None
    """
    super(PostMapEvent, self).__init__()
    self.input_graph = input_graph
    self.resource_graph = resource_graph
    self.result_graph = result_graph


class AbstractMapper(EventMixin):
  """
  Abstract class for graph mapping function.

  Inherited from :class`EventMixin` to implement internal event-based
  communication.

  If the Strategy class is not set as ``DEFAULT_STRATEGY`` the it try to search
  in the CONFIG with the name STRATEGY under the given Layer name.

  Contain common functions and initialization.
  """
  # Default Strategy class as a fallback strategy
  DEFAULT_STRATEGY = None
  """Default Strategy class as a fallback strategy"""

  def __init__ (self, layer_name, strategy=None, threaded=None):
    """
    Initialize Mapper class.

    Set given strategy class and threaded value or check in `CONFIG`.

    If no valid value is found for arguments set the default params defined
    in `_default`.

    .. warning::
      Strategy classes must be a subclass of AbstractMappingStrategy

    :param layer_name: name of the layer which initialize this class. This
      value is used to search the layer configuration in `CONFIG`
    :type layer_name: str
    :param strategy: strategy class (optional)
    :type strategy: :any:`AbstractMappingStrategy`
    :param threaded: run mapping algorithm in separate Python thread instead
      of in the coop microtask environment (optional)
    :type threaded: bool
    :return: None
    """
    self._layer_name = layer_name
    # Set threaded
    self._threaded = threaded if threaded is not None else CONFIG.get_threaded(
      layer_name)
    # Set strategy
    if strategy is None:
      # Use the Strategy in CONFIG
      strategy = CONFIG.get_strategy(layer_name)
      if strategy is None and self.DEFAULT_STRATEGY is not None:
        # Use the default Strategy if it's set
        strategy = self.DEFAULT_STRATEGY
      if strategy is None:
        raise RuntimeError("Strategy class is not found!")
    self.strategy = strategy
    assert issubclass(strategy,
                      AbstractMappingStrategy), "Mapping strategy is not " \
                                                "subclass of " \
                                                "AbstractMappingStrategy!"
    self.processor = CONFIG.get_mapping_processor(layer_name)(layer_name)
    super(AbstractMapper, self).__init__()

  @property
  def threaded (self):
    """
    Return the :any:`AbstractMapper` object is configured with threaded.

    :return: mapping is performed in separate thread or not
    :rtype: bool
    """
    return self._threaded

  def _perform_mapping (self, input_graph, resource_view):
    """
    Abstract function for wrapping optional steps connected to initiate
    mapping algorithm.

    Implemented function call the mapping algorithm.

    .. warning::
      Derived class have to override this function!

    Follows the Template Method design pattern.

    :param input_graph: graph representation which need to be mapped
    :type input_graph: :class:`NFFG`
    :param resource_view: resource information
    :type resource_view: :any:`AbstractVirtualizer`
    :raise: NotImplementedError
    :return: mapped graph
    :rtype: :class:`NFFG`
    """
    raise NotImplementedError

  def orchestrate (self, input_graph, resource_view):
    """
    Abstract function for wrapping optional steps connected to orchestration.

    Implemented function call the mapping algorithm.

    If a derived class of :any:`AbstractMappingDataProcessor` is set in the
    global config under the name "PROCESSOR" then the this class performs
    pre/post mapping steps.

    After the pre/post-processor steps the relevant Mapping event will be
    raised on the main API class of the layer!

    :param input_graph: graph representation which need to be mapped
    :type input_graph: :class:`NFFG`
    :param resource_view: resource information
    :type resource_view: :any:`AbstractVirtualizer`
    :raise: NotImplementedError
    :return: mapped graph
    :rtype: :class:`NFFG`
    """
    # Get resource info
    resource_graph = resource_view.get_resource_info()
    # If validator is not None call the pre function
    if CONFIG.get_processor_enabled(layer=self._layer_name):
      # Preform pre-mapping validation
      if self.processor is not None and self.processor.pre_mapping_exec(
         input_graph=input_graph, resource_graph=resource_graph):
        # Raise Error if processor function return with True
        raise ProcessorError("Pre mapping validation is failed!")
    # Raise event for external POX modules
    if core.hasComponent(self._layer_name):
      core.components[self._layer_name].raiseEvent(
        PreMapEvent, input_graph=input_graph, resource_graph=resource_graph)
    # Invoke mapping algorithm
    mapping_result = self._perform_mapping(input_graph=input_graph,
                                           resource_view=resource_view)
    # Perform post-mapping validation
    # If the mapping is threaded skip post mapping here
    if not self._threaded:
      # If validator is not None call the post function
      if CONFIG.get_processor_enabled(layer=self._layer_name):
        if self.processor is not None and self.processor.post_mapping_exec(
           input_graph=input_graph, resource_graph=resource_graph,
           result_graph=mapping_result):
          # Raise Error if processor function return with True
          raise ProcessorError("Post mapping validation is failed!")
      # Raise event for external POX modules
      if core.hasComponent(self._layer_name):
        core.components[self._layer_name].raiseEvent(
          PostMapEvent, input_graph=input_graph, resource_graph=resource_graph,
          result_graph=mapping_result)
    # Return the mapped NFFG
    return mapping_result

  def _start_mapping (self, graph, resource):
    """
    Run mapping algorithm in a separate Python thread.

    Should be called in _perform_mapping() function to initiate mapping if
    threaded is enabled!

    :param graph: Network Function Forwarding Graph
    :type graph: :class:`NFFG`
    :param resource: global resource
    :type resource: :class:`NFFG`
    :return: None
    """

    def run ():
      core.getLogger("worker").info(
        "Schedule mapping algorithm: %s" % self.strategy.__name__)
      nffg = self.strategy.map(graph=graph, resource=resource)
      # Must use call_as_coop_task because we want to call a function in a
      # coop microtask environment from a separate thread
      call_as_coop_task(self._mapping_finished, mapped_nffg=nffg)

    core.getLogger("worker").debug("Initialize working thread...")
    self._mapping_thread = threading.Thread(target=run)
    self._mapping_thread.daemon = True
    self._mapping_thread.start()

  def _mapping_finished (self, mapped_nffg):
    """
    Called from a separate thread when the mapping process is finished.

    .. warning::
      Derived class have to override this function!

    :param mapped_nffg: generated NF-FG
    :type mapped_nffg: :class:`NFFG`
    :return: None
    """
    raise NotImplementedError


class AbstractOrchestrator(object):
  """
  Abstract class for common and generic Orchestrator functions.

  If the mapper class is not set as ``DEFAULT_MAPPER`` the it try to search in
  the CONFIG with the name MAPPER under the given Layer name.
  """
  # Default Mapper class as a fallback mapper
  DEFAULT_MAPPER = None

  def __init__ (self, layer_API, mapper=None, strategy=None):
    """
    Init.

    :param layer_API: reference os the actual layer performing the orchestration
    :type layer_API: :any:`AbstractAPI`
    :param mapper: additional mapper class (optional)
    :type mapper: :any:`AbstractMapper`
    :param strategy: override strategy class for the used Mapper (optional)
    :type strategy: :any:`AbstractMappingStrategy`
    :return: None
    """
    layer_name = layer_API._core_name
    # Set Mapper
    if mapper is None:
      # Use the Mapper in CONFIG
      mapper = CONFIG.get_mapper(layer_name)
      if mapper is None and self.DEFAULT_MAPPER is not None:
        # Use de default Mapper if it's set
        self.mapper = self.DEFAULT_MAPPER
      if mapper is None:
        raise RuntimeError("Mapper class is not found!")
    assert issubclass(mapper, AbstractMapper), "Mapper is not subclass of " \
                                               "AbstractMapper!"
    self.mapper = mapper(strategy=strategy)
    # Init Mapper listeners
    # Listeners must be weak references in order the layer API can garbage
    # collected
    # self.mapper is set by the AbstractOrchestrator's constructor
    self.mapper.addListeners(layer_API, weak=True)
    super(AbstractOrchestrator, self).__init__()
