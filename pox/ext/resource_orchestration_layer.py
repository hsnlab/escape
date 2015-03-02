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
Basic POX module for ESCAPE Resource Orchestration sublayer

Initiate appropriate API class which implements Sl-Or reference point
Follow POX module conventions
"""
from escape.orchestration.resource_orchestration_API import ResourceOrchestrationAPI
from pox.core import core
import pox.lib.util as poxutil


@poxutil.eval_args
def launch(nffg=''):
    # Instantiate the API class and register into pox.core only once
    core.core.registerNew(ResourceOrchestrationAPI, nffg)
    # Wait for the necessery POX component until they are resolved and set up event handlers.
    # For this function event handler must follow the long naming convention: _handle_component_event().
    # The relevant components are registered on the API class by default withe the name: _<comp-name>_
    # See more in POXCore document.
    core.core.listen_to_dependencies(getattr(core, ResourceOrchestrationAPI._core_name), attrs=True)