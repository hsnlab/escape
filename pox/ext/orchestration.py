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
Basic POX module for ESCAPE Resource Orchestration Sublayer (ROS)

Initiate appropriate API class which implements Sl-Or reference point

Follows POX module conventions
"""
from escape.orchest.ros_API import ResourceOrchestrationAPI
from pox.core import core
import pox.lib.util as poxutil

# Initial parameters
init_param = {}


def _start_layer (event):
  """
  Initiate and run POX with ESCAPE components

  :param event: POX's going up event
  :type event: GoingUpEvent
  :return: None
  """
  # Instantiate the API class and register into pox.core only once
  ResourceOrchestrationAPI(**init_param)


@poxutil.eval_args
def launch (nffg_file='', standalone=False):
  """
  Launch function called by POX core when core is up

  :param nffg_file: Path of the NF-FG graph (optional)
  :type nffg_file: str
  :param standalone: Run layer without dependency checking (optional)
  :type standalone: bool
  :return: None
  """
  global init_param
  init_param.update(locals())
  core.addListenerByName("UpEvent", _start_layer)