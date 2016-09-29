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
Unifying package for ESCAPEv2 functions.

'cfg' defines the default configuration settings such as the concrete
RequestHandler and strategy classes, the initial Adapter classes, etc.

`CONFIG` contains the ESCAPEv2 dependent configuration as an
:any:`ESCAPEConfig`.
"""

from escape.util.config import ESCAPEConfig, PROJECT_ROOT

__project__ = "ESCAPEv2"
__authors__ = "Janos Czentye, Balazs Sonkoly, Levente Csikor"
__copyright__ = "Copyright 2015, under Apache License Version 2.0"
__credits__ = "Janos Czentye, Balazs Sonkoly, Levente Csikor, Attila Csoma, " \
              "Felician Nemeth, Andras Gulyas, Wouter Tavernier, and Sahel " \
              "Sahhaf"
__license__ = "Apache License, Version 2.0"
__version__ = "2.0.0"
__maintainer__ = "Janos Czentye"
__email__ = "czentye@tmit.bme.hu"
__status__ = "prototype"

ADDITIONAL_DIRS = ("unify_virtualizer",  # Virtualizer lib
                   "mapping",  # Mapping algorithm
                   "mininet"  # Tweaked Mininet for Click-Mininet Infrastructure
                   )
"""Additional source code directories added to PYTHONPATH"""


def add_dependencies ():
  """
  Add dependency directories to PYTHONPATH.
  Dependencies are directories besides the escape.py initial script except pox.

  :return: None
  """
  import os
  import sys
  from pox.core import log

  # Skipped folders under project's root
  skipped = ("escape", "examples", "pox", "OpenYuma", "Unify_ncagent", "tools",
             "gui", "hwloc2nffg", "nffg_BME", "include", "share", "lib", "bin",
             "dummy-orchestrator", "click")
  for sub_folder in os.listdir(PROJECT_ROOT):
    abs_sub_folder = os.path.join(PROJECT_ROOT, sub_folder)
    if not os.path.isdir(abs_sub_folder):
      continue
    if not (sub_folder.startswith('.') or sub_folder.upper().startswith(
       'PYTHON')) and sub_folder in ADDITIONAL_DIRS:
      if abs_sub_folder not in sys.path:
        log.debug("Add dependency: %s" % abs_sub_folder)
        sys.path.insert(0, abs_sub_folder)
      else:
        log.debug("Dependency: %s already added." % abs_sub_folder)


# Detect and add dependency directories
add_dependencies()
# Define global configuration and try to load additions from file
CONFIG = ESCAPEConfig().load_config()
"""Default configuration object"""
