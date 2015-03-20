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


class AbstractMapper(object):
  """
  Abstract class for graph mapping function

  Contain common functions and initialization
  """

  def __init__ (self, strategy):
    super(AbstractMapper, self).__init__()
    self.strategy = strategy

  def orchestrate (self, input_graph, resource_view):
    """

    :param input_graph:
    :param resource_view:
    :return:
    """
    raise NotImplementedError("Derived class must override this function!")


class ResourceOrchestrationMapper(AbstractMapper):
  """
  Main class for NFFG mapping

  Use the given mapping strategy
  """

  def orchestrate (self, input_graph, resource_view):
    pass

  def __init__ (self, strategy):
    super(ResourceOrchestrationMapper, self).__init__(strategy)