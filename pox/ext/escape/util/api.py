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
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json
import os.path
import threading

from pox.core import core


log = core.getLogger('REST-API')


class AbstractAPI(object):
    """
    Abstract class for UNIFY's API
    Contain common functions
    """
    # Default value for logger. Should be overwritten by child classes
    _core_name = "LayerAPI"
    # Explicitly defined dependencies as POX componenents
    _dependencies = ()

    def __init__(self):
        """
        Abstract class constructor
        Handle core registration along with _all_dependencies_met()
        Base constructor have to be called as the last call in inherited constructore
        Same situation with _all_dependencies_met() respectively
        """
        super(AbstractAPI, self).__init__()
        # Register this component on POX core if there is no dependent component
        # Due to registration _all_dependencies_met will be called automatically
        if not self._dependencies:
            core.core.register(self._core_name, self)
        # Subscribe for GoingDownEvent to finalize API classes
        # _shutdown function will be called if POX's core going down
        core.addListenerByName('GoingDownEvent', self._shutdown)

    def _all_dependencies_met(self):
        """
        Called when every componenet on which depends are initialized and registered in pox.core
        Contain dependency relevant initialization
        This function should be overwritten by child classes
        Actual APIs have to call this base function as last function call to handle core registration
        """
        # If there are dependent component, this function will be called after all the dependency has been registered
        # In this case register this component as the last step
        if self._dependencies:
            core.core.register(self._core_name, self)

    def _shutdown(self, event):
        """
        Finalization, deallocation, etc. of actual component
        Should be overwritten by child classes
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
            # TODO - return self._convert_json_to_sg(service_graph)
            core.getLogger(self._core_name).info("Graph representation is loaded sucessfully!")
            return graph


class ESCAPERequestHandler(BaseHTTPRequestHandler):
    """
    Minimalistic REST API for Service Layer
    Handle /escape/* URLs
    Method calling permitions represented in escape_intf dictionary
    """
    static_prefix = 'escape'
    escape_intf = {'GET': ('proba', 'list_sg'),
                   'POST': (),
                   'PUT': (),
                   'DELETE': ()}

    def do_GET(self):
        # TODO - Implement GET/POST/HEAD/PUT/DELETE processes
        print 'GET'
        self.process_url(self.path, 'GET')

    def process_url(self, path, http_method):
        """
        Split HTTP path and call the carved function if it is defined in this class and in escape_intf
        """
        if path.startswith('/{prefix}/'.format(prefix=self.static_prefix)):
            name = path.split('/')[2]
            if http_method in self.escape_intf:
                if name in self.escape_intf[http_method]:
                    if hasattr(self, name):
                        func = getattr(self, name)
                        func()
                else:
                    self.send_error(404, message="Method not supported!")
            else:
                self.send_error(501)
        else:
            self.send_error(400, message="URL not recognized!")

    def send_error(self, code, message=None):
        # TODO - need to overwritten
        log.warning(message)

    def send_response(self, code, message=None):
        # TODO - need to overwritten
        pass

    def send_header(self, keyword, value):
        # TODO - need to overwritten
        pass


class RESTServer(object):
    """
    Base HTTP server for REST API
    Initiate an HTTPServer and run it in different thread
    """

    def __init__(self, address='localhost', port=8008):
        self.server = HTTPServer((address, port), ESCAPERequestHandler)
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.started = False

    def start(self):
        self.started = True
        self.thread.start()

    def stop(self):
        if self.started:
            self.server.shutdown()

    def run(self):
        log.info("REST-API is initiated!")
        self.server.serve_forever()
        log.info("REST-API is shutting down...")