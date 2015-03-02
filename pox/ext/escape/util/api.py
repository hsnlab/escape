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
import json
import os.path

import pox.core as core


log = core.getLogger()


class AbstractAPI(object):
    """
    Abstract class for UNIFY's API
    Contain common functions
    """
    # Default value for logger. Should be overwritten by child classes
    _core_name = "LayerAPI"

    def __init__(self):
        super(AbstractAPI, self).__init__()

    def _all_dependencies_met(self):
        """
        Called when every componenet on which depends are initialized and registered in pox.core
        Contain dependency relevant initialization
        This function should be overwritten by child classes
        """
        pass

    def _read_graph_from_file(self, graph_file):
        try:
            if graph_file and not graph_file.startswith('/'):
                graph_file = os.path.abspath(graph_file)
            with open(graph_file, 'r') as f:
                graph = json.load(f)
        except (ValueError, IOError, TypeError) as e:
            core.getLogger(self._core_name).error("Can't load graph representation from file because of: " + str(e))
        else:
            # return self._convert_json_to_sg(service_graph)
            core.getLogger(self._core_name).info("Graph representation is loaded sucessfully!")
            return graph