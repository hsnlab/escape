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
Basic POX module for ESCAPE Controller Adaptation sublayer

Initiate appropriate API class which implements Or-Ca reference point
Follow POX module conventions
"""
from escape.adaptation.controller_adaptation_API import ControllerAdaptationAPI
from pox.core import core
import pox.lib.util as poxutil

# Initial parameters
init_param = {}


def _start_layer(event):
    # Instantiate the API class and register into pox.core only once
    # core.core.registerNew(ControllerAdaptationAPI, mapped_nffg)
    adaptation = ControllerAdaptationAPI(mapped_nffg_file=init_param['mapped_nffg'])
    # Wait for the necessery POX component until they are resolved and set up event handlers.
    # For this function event handler must follow the long naming convention: _handle_component_event().
    # The relevant components are registered on the API class by default with the name: _<comp-name>_
    # But for fail-safe operation, the dependencies are given explicitly which are defined in the actual API
    # See more in POXCore document.
    core.core.listen_to_dependencies(adaptation, attrs=True, components=getattr(adaptation, '_dependencies', ()))


@poxutil.eval_args
def launch(mapped_nffg=''):
    global init_param
    init_param.update(locals())
    core.addListenerByName("UpEvent", _start_layer)