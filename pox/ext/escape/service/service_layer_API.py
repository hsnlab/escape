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
from lib.revent.revent import EventMixin, Event
import pox.core as core

log = core.getLogger("service")


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
    _core_name = "service"
    _eventMixin_events = {ServiceEvent}

    def __init__(self):
        log.info("Initiating Service Layer...")

    def _all_dependencies_met(self):
        """
        Called when every componenet on which depends are initialized and registered in pox.core
        Contain dependency relevant initialization
        """
        log.info("Service Layer has been initialized!")

    def _handle_orchestration_ResourceEvent(self, event):
        # palceholder for orchestration dependency
        pass