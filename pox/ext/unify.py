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
Basic POX module for ESCAPE

Initiate appropriate APIs

Follows POX module conventions
"""
import pox.lib.util as poxutil
from pox.core import core

# Initial parameters
init_param = {}


# noinspection PyUnusedLocal
def _start_components (event):
  """
  Initiate and run POX with ESCAPE components.

  :param event: POX's going up event
  :type event: GoingUpEvent
  :return: None
  """
  # Launch ESCAPE components
  from service import launch
  # Launch Service Layer (mostly SAS)
  launch(sg_file=init_param['sg_file'], gui=init_param['gui'])
  from orchestration import launch
  # Launch Resource Orchestration Sublayer (ROS)
  launch()
  from adaptation import launch
  # Launch Controller Adaptation Sublayer (CAS)
  launch(with_infr=init_param['full'], agent=init_param['agent'])
  if init_param['full']:
    from infrastructure import launch
    # Launch Infrastructure Layer (IL) optionally
    launch()


@poxutil.eval_args
def launch (sg_file='', config=None, gui=False, agent=False, full=False,
     debug=True):
  """
  Launch function called by POX core when core is up.

  :param sg_file: Path of the input Service graph (optional)
  :type sg_file: str
  :param config: additional config file with different name
  :type config: str
  :param gui: Signal for initiate GUI (optional)
  :type gui: bool
  :param full: Initiate Infrastructure Layer also
  :type full: bool
  :return: None
  """
  global init_param
  init_param.update(locals())
  # Run POX with DEBUG logging level
  from pox.log.level import launch

  launch(DEBUG=debug)
  # Import colourful logging
  from pox.samples.pretty_log import launch

  launch()
  # Save additional config file name into POX's core as an attribute to avoid to
  # confuse with POX's modules
  if config:
    setattr(core, "config_file_name", config)
  # Register _start_components() to be called when POX is up
  core.addListenerByName("GoingUpEvent", _start_components)
