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
import urlparse
import json
import os.path
import threading

from escape import __version__
from lib.revent import EventMixin
from pox.core import core


class AbstractAPI(EventMixin):
  """
  Abstract class for UNIFY's API

  Contain common functions
  Follows Facade design pattern
  """
  # Default value for logger. Should be overwritten by child classes
  _core_name = "AbstractAPI"
  # Explicitly defined dependencies as POX componenents
  dependencies = ()
  # Events raised by this class, but already defined in superclass
  # _eventMixin_events = set()

  def __init__ (self, standalone=False, **kwargs):
    """
    Abstract class constructor
    Handle core registration along with _all_dependencies_met()
    Set given parameters (standalone parameter is mandatory) automatically as
    self._<param_name> = <param_value>
    Base constructor funtions have to be called as the last step in derived
    classes. Same situation with _all_dependencies_met() respectively.
    Must not override these fuction, just use initialize() function for init
    steps. Actual API classes must only call super() in their constructor
    with the form:
    super(<API Class name>, self).__init__(standalone=standalone, **kwargs)
    IMPORTANT!
    Do not use prefixes in the name of event handlers, because of automatic
    dependecy discovery considers that as a dependent componenet and this
    situation casue a dead lock (component will be waiting to each other to
    set up)

    :param standalone: started in standalone mode or not
    :type standalone: bool
    """
    super(AbstractAPI, self).__init__()
    # Save custom parameters with the given name
    self._standalone = standalone
    for key, value in kwargs.iteritems():
      setattr(self, '_' + key, value)
    # Check if need to skip dependency handling
    if standalone:
      # Initiate component manually
      self._all_dependencies_met()
    else:
      # Wait for the necessery POX component until they are resolved and set
      # up event handlers. The dependencies are given explicitly which are
      # defined in the actual API and not use automatic event handler based
      # dependency discovery to avoid issues come from fully event-driven
      # structure.
      # See more in POXCore document.
      core.core.listen_to_dependencies(self, getattr(self, 'dependencies', ()))

  def _all_dependencies_met (self):
    """
    Called when every componenet on which depends are initialized on
    pox.core. Contain dependency relevant initialization.
    """
    self.initialize()
    # With fully event-driven communication between the layers the dependency
    # handling takes care by listen_to_dependencies() run into a dead-lock.
    # The root of this problem is the bidirectional or cyclic dependency
    # between the componenets, so basicly the layers will always wait to each
    # other to be registered on core. To avoid this situation the naming
    # convention of event handlers on which the dependency checking based is
    # not followed (aka leave _handle_<component name>_<event name>) and
    # the event listeners is set up manually. For automatic core registration
    # the components have to containt dependencies explicitly.
    if not self._standalone:
      for dep in self.dependencies:
        if core.core.hasComponent(dep):
          dep_layer = core.components[dep]
          # Register actual event handlers on dependent layer
          dep_layer.addListeners(self)
          # Register dependent layer's event handlers on actual layer
          self.addListeners(dep_layer)
        else:
          raise AttributeError("Component is not registered on core")
    # Subscribe for GoingDownEvent to finalize API classes
    # shutdown() function will be called if POX's core going down
    core.addListenerByName('GoingDownEvent', self.shutdown)
    # Everything is set up an "running" so register the component on pox.core
    # as a final step. Other dependent component can finish initialization now.
    core.core.register(self._core_name, self)

  def initialize (self):
    """
    Init function for child API classes to symplify dynamic initilization
    Called when every componenet on which depends are initialized and
    registeredmin pox.core.
    This function should be overwritten by child classes.
    """
    pass

  def shutdown (self, event):
    """
    Finalization, deallocation, etc. of actual component
    Should be overwritten by child classes

    :param event: shutdown event raised by POX core
    :type event: GoingDownEvent
    """
    pass

  @staticmethod
  def _read_json_from_file (graph_file):
    """
    Read the given file and return a string formatted as JSON

    :param graph_file: file path
    :type graph_file: str
    :return: JSON data
    :rtype: str
    """
    if graph_file and not graph_file.startswith('/'):
      graph_file = os.path.abspath(graph_file)
    with open(graph_file, 'r') as f:
      graph = json.load(f)
    return graph

  def __str__ (self):
    """
    Print class type and non-private attributes with their types for debugging

    :return: specific string
    :rtype: str
    """
    print '<%s.%s object at %s>' % (
      self.__class__.__module__, self.__class__.__name__, hex(id(self)))
    print "Non-private attributes:"
    import pprint

    return pprint.pformat(
      [(f, type(getattr(self, f))) for f in dir(self) if not f.startswith('_')])


class RESTServer(object):
  """
  Base HTTP server for REST API

  Initiate an HTTPServer and run it in different thread
  """

  def __init__ (self, RequestHandlerClass, address, port):
    self._server = HTTPServer((address, port), RequestHandlerClass)
    self._thread = threading.Thread(target=self.run)
    self._thread.daemon = True
    self.started = False

  def start (self):
    self.started = True
    self._thread.start()

  def stop (self):
    if self.started:
      self._server.shutdown()

  def run (self):
    self._server.RequestHandlerClass.log.debug(
      "Init REST-API on %s:%d!" % self._server.server_address)
    # Start API loop
    self._server.serve_forever()
    self._server.RequestHandlerClass.log.debug(
      "REST-API on %s:%d is shutting down..." % self._server.server_address)


class AbstractRequestHandler(BaseHTTPRequestHandler):
  """
  Minimalistic REST API for Layer APIs

  Handle /escape/* URLs
  Method calling permitions represented in escape_intf dictionary

  IMPORTANT!
  This class is out of the context of the recoco's co-operative thread context!
  While you don't need to worry much about synchronization between recoco
  tasks, you do need to think about synchronization between recoco task and
  normal threads.
  Synchronisation is needed to take care manually: use relevant helper
  function of core object: callLater/raiseLater or use schedule_as_coop_task
  decorator defined in util.misc on the called function
  """
  # For HTTP Response messages
  server_version = "ESCAPE/" + __version__
  static_prefix = "escape"
  # Bind HTTP verbs to UNIFY's API functions
  request_perm = {'GET': (), 'POST': (), 'PUT': (), 'DELETE': ()}
  # Name of the layer API to which the server bounded
  bounded_layer = None
  # Logger. Should be overdefined in child classes
  log = core.getLogger("REST-API")

  def do_GET (self):
    """
    Get information about an entity. R for CRUD convention.
    """
    self._process_url()

  def do_POST (self):
    """
    Create an entity. C for CRUD convention.
    """
    self._process_url()

  def do_PUT (self):
    """
    Update an entity. U for CRUD convention.
    """
    self._process_url()

  def do_DELETE (self):
    """
    Delete an entity. D for CRUD convention.
    """
    self._process_url()

  def _process_url (self):
    """
    Split HTTP path and call the carved function
    if it is defined in this class and in request_perm
    """
    self.log.debug("Got HTTP request: %s" % str(self.raw_requestline).rstrip())
    http_method = self.command.upper()
    real_path = urlparse.urlparse(self.path).path
    if real_path.startswith('/%s/' % self.static_prefix):
      func_name = real_path.split('/')[2]
      if http_method in self.request_perm:
        if func_name in self.request_perm[http_method]:
          if hasattr(self, func_name):
            getattr(self, func_name)()
        else:
          self.send_error(405)
      else:
        self.send_error(501)
    else:
      self.send_error(404)

  def _parse_json_body (self):
    """
    Parse HTTP request body in JSON format
    Parsed JSON object is unicode
    GET, DELETE messages don't have body - return empty dict by default

    :return: request body in JSON format
    :rtype: str
    """
    charset = 'utf-8'
    try:
      splitted_type = self.headers['Content-Type'].split('charset=')
      if len(splitted_type) > 1:
        charset = splitted_type[1]
      content_len = int(self.headers.getheader('Content-Length', 0))
      raw_data = self.rfile.read(content_len)
      return json.loads(raw_data, encoding=charset)
    except KeyError:
      # Content-Length header is not defined or charset is not defined in
      # Content-Type header. Return empty dictionary.
      pass
    except ValueError as e:
      # Failed to parse request body to JSON
      self.log_error("Request parsing failed: %s", e)
    return {}

  def _send_json_response (self, data, encoding='utf-8'):
    """
    Send requested data in json format

    :param data: data in JSON format
    :type data: dict
    """
    response_body = json.dumps(data, encoding=encoding)
    self.send_response(200)
    self.send_header('Content-Type', 'text/json; charset=' + encoding)
    self.send_header('Content-Length', len(response_body))
    self.end_headers()
    self.wfile.write(response_body)

  def log_error (self, mformat, *args):
    """
    Overwritten to use POX logging mechanism
    """
    self.log.warning("%s - - [%s] %s" % (
      self.client_address[0], self.log_date_time_string(), mformat % args))

  def log_message (self, mformat, *args):
    """
    Disable logging of incoming messages
    """
    pass

  def log_full_message (self, mformat, *args):
    """
    Overwritten to use POX logging mechanism
    """
    self.log.debug("%s - - [%s] %s" % (
      self.client_address[0], self.log_date_time_string(), mformat % args))

  def _proceed_API_call (self, function, *args, **kwargs):
    """
    Fail-safe method to call API function
    The cooperative microtask context is handled by actual APIs
    Should call this with params, not directly the function of actual API

    :param function: function name
    :type function: str
    """
    if core.core.hasComponent(self.bounded_layer):
      layer = core.components[self.bounded_layer]
      if hasattr(layer, function):
        getattr(layer, function)(*args, **kwargs)
      else:
        # raise NotImplementedError()
        self.log.warning(
          'Mistyped or not implemented API function call: %s ' % function)
    else:
      self.log.error('Error: No componenet has registered with the name: %s, '
                     'ABORT function call!' % self.bounded_layer)