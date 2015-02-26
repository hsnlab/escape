# Copyright 2015 Janos Czentye
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Basic POX module for ESCAPE Service (Graph Adaptation) sublayer

Initiate appropriate API class which implements U-Sl reference point
Follow POX module conventions
"""
import os.path

from escape.service.service_layer_API import ServiceLayerAPI
from pox.core import core
import pox.lib.util as poxutil


@poxutil.eval_args
def launch(sg='', gui=False):
    # Initialize the API class, wait for the necessery POX component until they are resolved and set up event handlers.
    # For this function event handler must follow the long naming convention: _handle_component_event().
    # See more in POXCore document.
    if sg and not sg.startswith('/'):
        sg = os.path.abspath(sg)
    core.core.registerNew(ServiceLayerAPI, sg, gui)
    core.core.listen_to_dependencies(getattr(core, ServiceLayerAPI._core_name))