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
The overall POX module for the layer modules of ESCAPE.

Initiate appropriate layer APIs.

Follows POX module conventions.
"""
import logging
import os
import site
import sys

import pox.lib.util as poxutil
from escape_logging import setup_logging
from pox.core import core, log as core_log

# Initial parameters used for storing command line parameters.
init_param = {}
"""Initial parameters used for storing command line parameters."""


# noinspection PyUnusedLocal
def _start_components (event):
  """
  Initiate and run POX with ESCAPE components.

  :param event: POX's going up event
  :type event: :class:`pox.core.GoingUpEvent`
  :return: None
  """
  # Launch ESCAPE components
  if init_param['full']:
    # Launch Infrastructure Layer (IL) optionally
    from infrastructure import launch

    launch(topo=init_param['mininet'])
  # Launch Controller Adaptation Sublayer (CAS)
  from adaptation import launch

  launch(with_infr=init_param['full'], dovapi=init_param['dovapi'])
  # Launch Resource Orchestration Sublayer (ROS)
  from orchestration import launch

  launch(agent=init_param['agent'], rosapi=init_param['rosapi'],
         cfor=init_param['cfor'])
  if not init_param['agent']:
    # Launch Service Layer (mostly SAS)
    from service import launch

    launch(sg_file=init_param['sg_file'], gui=init_param['gui'])


def __init_loggers (loglevel, log, test, log_folder=None):
  """
  Init loggers.

  :param loglevel: run on specific run level  (default: INFO)
  :type loglevel: str
  :param log: add ESCAPE main log file for test mode (default: log/escape.log)
  :type log: str
  :param test: Start ESCAPE in test mode (optional)
  :type test: bool
  :return: None
  """
  # Import colourful logging
  if loglevel == 'VERBOSE':
    setup_logging(test_mode=True if test else False, log_file=log,
                  log_folder=log_folder)
    # Set the Root logger level explicitly
    logging.getLogger('').setLevel("VERBOSE")
  else:
    # Launch pretty logger with specific log level
    setup_logging(test_mode=True if test else False, loglevel=True,
                  log_file=log, log_folder=log_folder)


def __init_stats (stats_folder):
  if stats_folder is None:
    stats_folder = "log/stats"
  core_log.info("Initialize stats folder: %s" % stats_folder)
  from escape.util.stat import initialize
  initialize(stats_folder=stats_folder)


def __init_config (config, test, quit):
  """
  Init configuration.

  :param config: additional config file with different name
  :type config: str
  :param test: Start ESCAPE in test mode (optional)
  :type test: bool
  :param quit: Quit after the first service request has processed (optional)
  :type quit: bool
  :return:
  """
  # Save test mode
  if test:
    setattr(core, "TEST_MODE", True)

  # Save quit mode
  if quit:
    setattr(core, "QUIT_AFTER_PROCESS", True)
  from escape.util.config import ESCAPEConfig
  # Define global configuration and try to load additions from file
  ESCAPEConfig().load_config(config=config)


def __print_header ():
  from escape.util.misc import get_escape_revision
  revision = get_escape_revision()
  core_log.info("Starting %s" % revision[0])
  core_log.info("Version: %s" % revision[1])
  core_log.info("Current branch: %s" % revision[2])
  core_log.info("Initializing main layer modules...")


def __setup_pythonpath ():
  """
  Setup PYTHONPATH if ESCAPE was stated in a subshell.

  :return: None
  """
  # Detect and add dependency directories in case it run in a subshell
  PROJECT_ROOT = os.path.normpath(os.path.abspath(__file__) + "/../../..")
  site.addsitedir(sitedir=PROJECT_ROOT)
  # Remove project root to avoid name collision
  sys.path.remove(PROJECT_ROOT)


@poxutil.eval_args
def launch (sg_file=None, config=None, gui=False, agent=False, rosapi=False,
            dovapi=False, full=False, loglevel="INFO", cfor=False, quit=False,
            visualization=False, mininet=None, test=False, log=None,
            log_folder=None):
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
  :param mininet: Path of the initial topology graph (optional)
  :type mininet: str
  :param test: Start ESCAPE in test mode (optional)
  :type test: bool
  :param log: add ESCAPE main log file for test mode (default: log/escape.log)
  :type log: str
  :param quit: Quit after the first service request has processed (optional)
  :type quit: bool
  :return: None
  """
  # Store args into this module file
  global init_param
  init_param.update(locals())

  __setup_pythonpath()
  __init_loggers(loglevel=loglevel, log=log, test=test, log_folder=log_folder)
  __init_config(config=config, test=test, quit=quit)
  __print_header()

  if visualization:
    core_log.debug("Enable remote visualization...")
    from escape.util.com_logger import RemoteVisualizer
    core.register(RemoteVisualizer._core_name, RemoteVisualizer())

  # Register _start_components() to be called when POX is up
  core.addListenerByName("GoingUpEvent", _start_components)
