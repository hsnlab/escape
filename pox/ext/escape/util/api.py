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
import weakref

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
  _dependencies = ()
  # Events raised by this class, but already defined in superclass
  # _eventMixin_events = set()

  def __init__ (self, standalone=False, **kwargs):
    """
    Abstract class constructor
    Handle core registration along with _all_dependencies_met()
    Set given parameters (standalone parameter is mandatory) automatically
    Base constructor funtions have to be called as the last step
    Same situation with _all_dependencies_met() respectively
    Must not override, just  use initialize() function instead
    Actual API classes must call super with the form:
    super(<API Class name>, self).__init__(standalone=standalone, **kwargs)
    """
    super(AbstractAPI, self).__init__()
    # Save custom parameters with the given name
    self.standalone = standalone
    for key, value in kwargs.iteritems():
      setattr(self, key, value)
    # Register this component on POX core if there is no dependent component
    # Due to registration _all_dependencies_met will be called automatically
    if not self._dependencies:
      core.core.register(self._core_name, self)
    # Check if need to skip dependency handling
    if standalone:
      # Skip setting up Event listeners
      # Initiate component manually also
      self._all_dependencies_met()
      # Initiate dependency references with Logger object
      for dep in self._dependencies:
        setattr(self, dep, StandaloneHelper(self))
    else:
      # Wait for the necessery POX component until they are resolved and set
      # up event handlers. For this function event handler must follow the
      # long naming convention: _handle_component_event(). The relevant
      # components are registered on the API class by default with the name:
      # <comp-name>. But for fail-safe operation, the dependencies are given
      # explicitly which are defined in the actual API. See more in POXCore
      # document.
      # core.core.listen_to_dependencies(self,
      # components=getattr(self, '_dependencies',
      # ()), attrs=True, short_attrs=True)

      core.core.listen_to_dependencies(self, getattr(self, '_dependencies', ()))
    # Subscribe for GoingDownEvent to finalize API classes
    # _shutdown function will be called if POX's core going down
    core.addListenerByName('GoingDownEvent', self.shutdown)

  def _all_dependencies_met (self):
    """
    Called when every componenet on which depends are initialized and registered
    in pox.core. Contain dependency relevant initialization.
    Actual APIs have to call this base function as last function call to handle
    core registration
    """
    self.initialize()
    # If there are dependent component, this function will be called after all
    # the dependency has been registered. In this case register this component
    # as the last step.
    if self._dependencies:
      core.core.register(self._core_name, self)

  def initialize (self):
    """
    Init function for child API classes to symplify dynamic initilization
    This function should be overwritten by child classes.
    """
    pass

  def shutdown (self, event):
    """
    Finalization, deallocation, etc. of actual component
    Should be overwritten by child classes
    """
    pass

  def _read_json_from_file (self, graph_file):
    if graph_file and not graph_file.startswith('/'):
      graph_file = os.path.abspath(graph_file)
    with open(graph_file, 'r') as f:
      graph = json.load(f)
    return graph

  def __str__ (self):
    """
    Print class type and non-private attributes with their types for debugging
    """
    print '<%s.%s object at %s>' % (
      self.__class__.__module__, self.__class__.__name__, hex(id(self)))
    print "Non-private attributes:"
    import pprint

    return pprint.pformat(
      [(f, type(getattr(self, f))) for f in dir(self) if not f.startswith('_')])


class StandaloneHelper(object):
  """
  Represent a component on which an actual running component (started in
  standalone mode) depends

  Catch and log every function call
  Not used in case of fully event-driven inter-layer communication
  """

  def __init__ (self, container):
    super(StandaloneHelper, self).__init__()
    self.container = weakref.proxy(container)  # Garbage-Collector safe

  def __getattr__ (self, name):
    """
    Catch all attribute/function that don't exists
    """
    # TODO - what if somebody want to access to an atrribute instead of function
    def logger (*args, **kwargs):
      # Wrapper function for logging
      msg = "Called function %s - with params:\n%s\n%s" % (name, args, kwargs)
      core.getLogger(self.container._core_name + '-standalone').info(msg)
      return  # Do nothing just log

    return logger


class RESTServer(object):
  """
  Base HTTP server for REST API

  Initiate an HTTPServer and run it in different thread
  """

  def __init__ (self, RequestHandlerClass, address, port):
    self.server = HTTPServer((address, port), RequestHandlerClass)
    self.thread = threading.Thread(target=self.run)
    self.thread.daemon = True
    self.started = False

  def start (self):
    self.started = True
    self.thread.start()

  def stop (self):
    if self.started:
      self.server.shutdown()

  def run (self):
    self.server.RequestHandlerClass.log.info(
      "REST-API is initiated on %s:%d!" % self.server.server_address)
    # Start API loop
    self.server.serve_forever()
    self.server.RequestHandlerClass.log.info(
      "REST-API on %s:%d is shutting down..." % self.server.server_address)


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
    self.process_url()

  def do_POST (self):
    """
    Create an entity. C for CRUD convention.
    """
    self.process_url()

  def do_PUT (self):
    """
    Update an entity. U for CRUD convention.
    """
    self.process_url()

  def do_DELETE (self):
    """
    Delete an entity. D for CRUD convention.
    """
    self.process_url()

  def process_url (self):
    """
    Split HTTP path and call the carved function
    if it is defined in this class and in request_perm
    """
    http_method = self.command.upper()
    real_path = urlparse.urlparse(self.path).path
    if real_path.startswith('/%s/' % self.static_prefix):
      func_name = real_path.split('/')[2]
      if http_method in self.request_perm:
        if func_name in self.request_perm[http_method]:
          if hasattr(self, func_name):
            getattr(self, func_name)()
        else:
          self.send_error(404, message="Method not supported by ESCAPE!")
      else:
        self.send_error(501)
    else:
      self.send_error(400, message="URL not recognized!")

  def _parse_json_body (self):
    """
    Parse HTTP request body in JSON format
    Parsed JSON object is unicode
    GET, DELETE messages don't contain parameters - Return empty dict by default
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
    """
    response_body = json.dumps(data, encoding=encoding)
    self.send_response(200)
    self.send_header('Content-Type', 'text/json; charset=' + encoding)
    self.send_header('Content-Length', len(response_body))
    self.end_headers()
    self.wfile.write(response_body)
    return

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

  def proceed_API_call (self, function, *args, **kwargs):
    """
    Fail-safe method to call API function
    The cooperative microtask context is handled by actual APIs
    Should call this with params, not directly the function of actual API
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