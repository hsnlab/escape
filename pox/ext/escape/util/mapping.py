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
Contains abstract classes for NFFG mapping.
"""
import threading

from escape import CONFIG
from escape.service import LAYER_NAME as SAS
from escape.orchest import LAYER_NAME as ROS
from escape.util.misc import call_as_coop_task
from pox.lib.revent.revent import EventMixin
from pox import core


class AbstractMappingStrategy(object):
  """
  Abstract class for the mapping strategies.

  Follows the Strategy design pattern.
  """

  def __init__ (self):
    """
    Init
    """
    super(AbstractMappingStrategy, self).__init__()

  @classmethod
  def map (cls, graph, resource):
    """
    Abstract function for mapping algorithm.

    .. warning::
      Derived class have to override this function

    :param graph: Input graph which need to be mapped
    :type graph: NFFG
    :param resource: resource info
    :type resource: NFFG
    :raise: NotImplementedError
    :return: mapped graph
    :rtype: NFFG
    """
    raise NotImplementedError("Derived class must override this function!")


class AbstractMapper(EventMixin):
  """
  Abstract class for graph mapping function.

  Inherited from :class`EventMixin` to implement internal event-based
  communication.

  Contain common functions and initialization.
  """
  _defaults = {SAS: 'DefaultServiceMappingStrategy',
               ROS: 'ESCAPEMappingStrategy'}

  def __init__ (self, layer_name, strategy=None, threaded=None):
    """
    Initialize Mapper class.

    Set given strategy class and threaded value or check in `CONFIG`.

    If no valid value is found for arguments set the default params defined
    in `_default`.

    .. warning::
      Strategy classes must be a subclass of AbstractMappingStrategy

    .. note::
      SAS strategy is searched in :mod:`escape.service.sas_mapping`

    .. note::
      ROS strategy is searched in :mod:`escape.orchest.ros_mapping`

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
    # Set threaded
    self._threaded = threaded if threaded is not None else CONFIG.get_threaded(
      layer_name)
    # Set strategy
    if strategy is not None:
      assert issubclass(strategy,
                        AbstractMappingStrategy), "Mapping strategy is not " \
                                                  "subclass of " \
                                                  "AbstractMappingStrategy!"
      self.strategy = strategy
    else:
      self.strategy = CONFIG.get_strategy(layer_name)
      if self.strategy is None:
        self.strategy = self._defaults[layer_name]
    super(AbstractMapper, self).__init__()

  def orchestrate (self, input_graph, resource_view):
    """
    Abstract function for wrapping optional steps connected to orchestration.

    Implemented function call the mapping algorithm.

    .. warning::
      Derived class have to override this function

    :param input_graph: graph representation which need to be mapped
    :type input_graph: :any:`NFFG`
    :param resource_view: resource information
    :type resource_view: :any:`AbstractVirtualizer`
    :raise: NotImplementedError
    :return: mapped graph
    :rtype: :any:`NFFG`
    """
    raise NotImplementedError("Derived class must override this function!")

  def _start_mapping (self, graph, resource):
    """
    Run mapping algorithm in a separate Python thread.

    :param graph: Network Function Forwarding Graph
    :type graph: :any:`NFFG`
    :param resource: global resource
    :type resource: :any:`NFFG`
    :return: None
    """

    def run ():
      core.getLogger("worker").info(
        "Schedule mapping algorithm: %s" % self.strategy.__name__)
      nffg = self.strategy.map(graph=graph, resource=resource)
      # Must use call_as_coop_task because we want to call a function in a
      # coop microtask environment from a separate thread
      call_as_coop_task(self._mapping_finished, nffg=nffg)

    core.getLogger("worker").debug("Initialize working thread...")
    self._mapping_thread = threading.Thread(target=run)
    self._mapping_thread.daemon = True
    self._mapping_thread.start()

  def _mapping_finished (self, nffg):
    """
    Called from a separate thread when the mapping process is finished.

    .. warning::
      Derived class have to override this function

    :param nffg: generated NF-FG
    :type nffg: :any:`NFFG`
    :return: None
    """
    raise NotImplementedError("Derived class must override this function!")
