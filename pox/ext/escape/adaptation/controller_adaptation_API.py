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
from escape.adaptation import LAYER_NAME
from escape.util.api import AbstractAPI
from lib.revent.revent import EventMixin, Event
import pox.core as core

log = core.getLogger(LAYER_NAME)


class AdaptationEvent(Event):
    """
    Dummy event to force dependency checking working
    Should/Will be removed shortly!
    """

    def __init__(self):
        super(AdaptationEvent, self).__init__()


class ControllerAdaptationAPI(EventMixin, AbstractAPI):
    """
    Entry point for Controller Adaptation Sublayer

    Maintain the contact with other UNIFY layers
    Implement the Or - Ca reference point
    """
    # Define specific name for core object i.e. pox.core.<_core_name>
    _core_name = LAYER_NAME
    # Events raised by this class
    _eventMixin_events = {AdaptationEvent}

    def __init__(self, mapped_nffg_file):
        # Initializations after this class is instantiated
        # Call base class init explicitly because Python super() with multiple inheritance is tricky
        EventMixin.__init__(self)
        AbstractAPI.__init__(self)
        log.info("Initiating Controller Adaptation Layer...")
        if mapped_nffg_file:
            self._read_graph_from_file(mapped_nffg_file)


def _all_dependencies_met(self):
    """
    Called when every componenet on which depends are initialized and registered in pox.core
    Contain dependency relevant initialization
    """
    log.info("Controller Adaptation Layer has been initialized!")