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
from escape.service.service_layer_API import ServiceLayerAPI
from pox.core import core
import pox.lib.util as poxutil


@poxutil.eval_args
def launch(sg='', gui=False):
    # Instantiate the API class and register into pox.core only once
    core.core.registerNew(ServiceLayerAPI, sg, gui)
    # Wait for the necessery POX component until they are resolved and set up event handlers.
    # For this function event handler must follow the long naming convention: _handle_component_event().
    # But for fail-safe operation, the dependencies are given explicitly
    # The dependencies are set in the actual API
    # See more in POXCore document.
    core.core.listen_to_dependencies(getattr(core, ServiceLayerAPI._core_name), attrs=True)