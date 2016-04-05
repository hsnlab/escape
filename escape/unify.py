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
import logging

import pox.lib.util as poxutil
from pox.core import core, log

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
  if init_param['full']:
    # Launch Infrastructure Layer (IL) optionally
    from infrastructure import launch

    launch(topo=init_param['topo'])
  # Launch Controller Adaptation Sublayer (CAS)
  from adaptation import launch

  launch(with_infr=init_param['full'])
  # Launch Resource Orchestration Sublayer (ROS)
  from orchestration import launch

  launch(agent=init_param['agent'], rosapi=init_param['rosapi'],
         cfor=init_param['cfor'])
  if not init_param['agent']:
    # Launch Service Layer (mostly SAS)
    from service import launch

    launch(sg_file=init_param['sg_file'], gui=init_param['gui'])


@poxutil.eval_args
def launch (sg_file='', config=None, gui=False, agent=False, rosapi=False,
            full=False, loglevel="INFO", cfor=False, visualization=False,
            topo=None):
  """
  Launch function called by POX core when core is up.

  :param sg_file: Path of the input Service graph (optional)
  :type sg_file: str
  :param config: additional config file with different name
  :type config: str
  :param gui: Signal for initiate GUI (optional)
  :type gui: bool
  :param agent: Do not start the service layer (optional)
  :type agent: bool
  :param rosapi:
  :param full: Initiate Infrastructure Layer also
  :type full: bool
  :param loglevel: run on specific run level  (default: INFO)
  :type loglevel: str
  :param cfor: start Cf-Or REST API (optional)
  :type cfor: bool
  :param visualization: send NFFGs to remote visualization server (optional)
  :type visualization: bool
  :param topo: Path of the initial topology graph (optional)
  :type topo: str
  :return: None
  """
  global init_param
  # Add new VERBOSE log level to root logger
  logging.addLevelName(5, 'VERBOSE')
  init_param.update(locals())
  # Import colourful logging
  from pox.samples.pretty_log import launch
  if loglevel == 'VERBOSE':
    launch()
    # Set the Root logger level explicitly
    logging.getLogger('').setLevel("VERBOSE")
  else:
    # Launch pretty logger with specific log level
    launch(**{loglevel: True})
  log.info("Setup logger - formatter: %s, level: %s" % (
    "pretty_log", logging.getLevelName(log.getEffectiveLevel())))
  # Save additional config file name into POX's core as an attribute to avoid to
  # confuse with POX's modules
  if config:
    setattr(core, "config_file_name", config)
  from escape.util.misc import get_escape_name_version
  log.info("Starting %s(version: %s) components..." % get_escape_name_version())

  if visualization:
    log.debug("Enable remote visualization...")
    from escape.util.visualization import RemoteVisualizer
    core.register(RemoteVisualizer._core_name, RemoteVisualizer())
  # Register _start_components() to be called when POX is up
  core.addListenerByName("GoingUpEvent", _start_components)
