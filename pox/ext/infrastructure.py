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
Basic POX module for ESCAPE Infrastructure Layer

Initiate appropriate API class which emulate Co-Rm reference point

Follows POX module conventions
"""
import os

from escape.infr.il_API import InfrastructureLayerAPI
from escape.util.misc import quit_with_error
from pox.core import core
import pox.lib.util as poxutil

# Initial parameters
init_param = {}


def _start_layer (event):
  """
  Initiate and run Infrastructure module.

  :param event: POX's going up event
  :type event: GoingUpEvent
  :return: None
  """
  # Instantiate the API class and register into pox.core only once
  InfrastructureLayerAPI(**init_param)


@poxutil.eval_args
def launch (standalone=False, topo=None):
  """
  Launch function called by POX core when core is up.

  :param standalone: Run layer without dependency checking (optional)
  :type standalone: bool
  :param topo: Load the topology description from file (optional)
  :type topo: str
  :return: None
  """
  global init_param
  init_param.update(locals())
  if os.geteuid() != 0:
    quit_with_error(msg="Mininet emulation requires root privileges!",
                    logger=InfrastructureLayerAPI._core_name)
  # Load additional params into CONFIG if necessary
  core.addListenerByName("UpEvent", _start_layer)
