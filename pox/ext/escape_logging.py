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
The logger module for ESCAPE.

Based on pretty_logger: /pox/pox/samples/pretty_log.py
"""
import logging
import os

import pox.log
from pox.core import log, _ext_path
from pox.log import color, level

# Add new VERBOSE log level to root logger
logging.addLevelName(5, 'VERBOSE')
logging.getLogger('').setLevel("VERBOSE")

# Set color for the additional VERBOSE level in POX
color.LEVEL_COLORS['VERBOSE'] = 'white'

# Use logger format from pretty_logger
DEFAULT_LOGGER_FORMAT = "[@@@bold@@@level%(levelname)0.8s@@@reset]" \
                        "[@@@bold@@@level%(name)-23s@@@reset] " \
                        "@@@bold%(message)s@@@normal"
# Add logger level to the log entries in test mode
TEST_LOGGER_FORMAT = "[@@@bold@@@level%(levelname)-18s@@@reset]" \
                     "[@@@bold@@@level%(name)-23s@@@reset]" \
                     " @@@bold%(message)s@@@normal"
# Add logger level to the log entries in test mode
FILE_LOGGER_FORMAT = "|%(levelname)s" \
                     "|%(name)s" \
                     "|%(asctime)s" \
                     "|---|%(message)s"

# Log folder name
LOG_FOLDER = os.path.realpath(_ext_path + "../log")


def setup_logging (test_mode=False, log_file=None, log_folder=None, **kwargs):
  """
  Launch and set parameters for logging.

  :param test_mode: use test mode logging (default: False)
  :type test_mode: bool
  :param log_file: log file path
  :type log_file: str
  :return: None
  """
  # Enable logging in specific logging level
  level.launch(**kwargs)
  # Launch colorful logging
  color.launch()
  if test_mode:
    # Define logger for test mode
    pox.log.launch(format=TEST_LOGGER_FORMAT)
    log.info("Setup Logger - formatter: %s, level: %s"
             % (pox.log.launch.__module__,
                logging.getLevelName(log.getEffectiveLevel())))
    # Set default log_file to log in file in test mode
  else:
    # Define default logger
    pox.log.launch(format=DEFAULT_LOGGER_FORMAT)
    log.info("Setup logger - formatter: %s, level: %s"
             % (setup_logging.__module__,
                logging.getLevelName(log.getEffectiveLevel())))
  if log_folder is not None:
    global LOG_FOLDER
    LOG_FOLDER = log_folder
  if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)
  if log_file is None:
    log_file = os.path.join(LOG_FOLDER, "escape.log")
  if log_file:
    # Define additional logger for logging to file
    pox.log.launch(format=FILE_LOGGER_FORMAT, file=log_file + ',w')
    log.info("Setup Logger - formatter: %s, level: %s, file: %s"
             % (pox.log.launch.__module__,
                logging.getLevelName(log.getEffectiveLevel()),
                log_file))
