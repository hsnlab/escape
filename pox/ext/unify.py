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
Basic POX module for ESCAPE

Initiate appropriate APIs
Follow POX module conventions
"""
import pox.lib.util as poxutil
from pox.core import core


def _start_components(event):
    """
    Initiate and run POX with ESCAPE components
    """
    # Run POX with DEBUG logging level
    from pox.log.level import launch
    launch(DEBUG=True)
    # Import colouful logging
    from pox.samples.pretty_log import launch
    launch()
    # Launch ESCAPE components
    from service_layer import launch
    launch()
    from resource_orchestation_layer import launch
    launch()
    from controller_adaptation_layer import launch
    launch()


@poxutil.eval_args
def launch():
    core.addListenerByName("UpEvent", _start_components)
