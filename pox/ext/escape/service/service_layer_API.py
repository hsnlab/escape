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

from lib.revent.revent import EventMixin, Event
import pox.core as core

LAYER_NAME = "service"
log = core.getLogger(LAYER_NAME)


class ServiceEvent(Event):
    """
    Dummy event to force dependency checking working
    Should/Will be removed shortly!
    """
    def __init__(self):
        super(ServiceEvent, self).__init__()


class ServiceLayerAPI(EventMixin):
    """
    Entry point for Service Layer

    Maintain the contact with other UNIFY layers
    Implement the U - Sl reference point
    """
    # Define specific name for core object i.e. pox.core.<_core_name>
    _core_name = LAYER_NAME
    # Events raised by this class
    _eventMixin_events = {ServiceEvent}

    def __init__(self, sg_file, gui):
        super(ServiceLayerAPI, self).__init__()
        log.info("Initiating Service Layer...")
        if sg_file:
            self._read_sg_from_file(sg_file)
        if gui:
            self._initiate_gui()
        else:
            self._initiate_rest_api()

    def _all_dependencies_met(self):
        """
        Called when every componenet on which depends are initialized and registered in pox.core
        Contain dependency relevant initialization
        """
        log.info("Service Layer has been initialized!")

    def _handle_orchestration_ResourceEvent(self, event):
        # palceholder for orchestration dependency
        pass

    def _read_sg_from_file(self, sg_file):
        try:
            with open(sg_file, 'r') as f:
                service_graph = json.load(f)
        except (ValueError, IOError) as e:
            log.error("Can't load service graph from file because: " + str(e))
        else:
            return self._convert_json_to_sg(service_graph)

    def _convert_json_to_sg(self, service_graph):
        # TODO - need standard SG form to implement this
        pass

    def _initiate_gui(self):
        # TODO - set up and initiate MiniEdit here
        pass

    def _initiate_rest_api(self):
        # TODO - initiate and set up REST-API here
        pass