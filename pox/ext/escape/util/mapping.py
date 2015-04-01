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


class AbstractMappingStrategy(object):
  """
  Abstract class for the mapping strategies

  Follow the Strategy design pattern
  """

  def __init__ (self):
    """
    Init
    """
    super(AbstractMappingStrategy, self).__init__()

  @classmethod
  def map (cls, graph, resource):
    """
    Abstract function for mapping algorithm

    :param graph: Input graph which need to be mapped
    :type graph: NFFG
    :param resource: resource info
    :type resource: NFFG
    :raise: NotImplementedError
    :return: mapped graph
    :rtype: NFFG
    """
    raise NotImplementedError("Derived class must override this function!")


class AbstractMapper(object):
  """
  Abstract class for graph mapping function

  Contain common functions and initialization
  """

  def __init__ (self, strategy):
    """
    Init

    :param strategy: Class of mapping strategy
    :type strategy: AbstractMappingStrategy
    """
    super(AbstractMapper, self).__init__()
    self.strategy = strategy

  def orchestrate (self, input_graph, resource_view):
    """
    Abstract function for wrapping optional steps connected to orchestration
    Implemented function call the mapping algorithm

    :param input_graph: graph representation which need to be mapped
    :type input_graph: NFFG
    :param resource_view: resource information
    :type resource_view: AbstractVirtualizer
    :raise: NotImplementedError
    :return: mapped graph
    :rtype: NFFG
    """
    raise NotImplementedError("Derived class must override this function!")