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

from escape.orchest.mapping_strategy import AbstractMappingStrategy
from escape.orchest.nffg_mapping import AbstractMapper


class ServiceGraphMapper(AbstractMapper):
  """
  Helper class for mapping Service Graph to NFFG
  """

  def __init__ (self):
    super(ServiceGraphMapper, self).__init__()


class DefaultServiceMappingStrategy(AbstractMappingStrategy):
  """
  Mapping class which maps given Service Graph into a single BiS-BiS
  """

  def __init__ (self):
    super(DefaultServiceMappingStrategy, self).__init__()