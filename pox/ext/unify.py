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
Basic POX module for ESCAPE

Initiate appropriate APIs
Follow POX module conventions
"""
import pox.lib.util as poxutil
from pox.core import core

# Initial parameters
init_param = {}


# noinspection PyUnusedLocal
def _start_components (event):
  """
  Initiate and run POX with ESCAPE components
  """
  # Launch ESCAPE components
  # Launch Service Layer
  from service_layer import launch

  launch(sg_file=init_param['sg_file'], gui=init_param['gui'])
  # Launch Resource Orchestration Sublayer
  from resource_orchestration_layer import launch

  launch()
  # Lauch Controller Adaptation Sublayer (CAS)
  from controller_adaptation_layer import launch

  launch()


@poxutil.eval_args
def launch (sg_file='', gui=False):
  global init_param
  init_param.update(locals())

  # Run POX with DEBUG logging level
  from pox.log.level import launch

  launch(DEBUG=True)

  # Import colouful logging
  from pox.samples.pretty_log import launch

  launch()

  core.addListenerByName("GoingUpEvent", _start_components)