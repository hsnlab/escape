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
The logger module for ESCAPE.

Based on pretty_logger: /pox/pox/samples/pretty_log.py
"""
import logging

import pox.log
from pox.log import color, level
from pox.core import log

# Add new VERBOSE log level to root logger
logging.addLevelName(5, 'VERBOSE')
logging.getLogger('').setLevel("VERBOSE")

color.LEVEL_COLORS['VERBOSE'] = 'white'

DEFAULT_FORMAT = "[@@@bold@@@level%(name)-23s@@@reset] @@@bold%(" \
                 "message)s@@@normal"
TEST_FORMAT = "[@@@bold@@@level%(levelname)-18s@@@reset][@@@bold@@@level%(" \
              "name)-23s@@@reset] @@@bold%(message)s@@@normal"


def launch (test_mode=False, **kw):
  pox.log.launch(format=TEST_FORMAT if test_mode else DEFAULT_FORMAT)
  color.launch()
  level.launch(**kw)
  log.info("Setup logger - formatter: %s, level: %s" % (
    launch.__module__, logging.getLevelName(log.getEffectiveLevel())))
