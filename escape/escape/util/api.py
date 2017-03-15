# Copyright 2017 Janos Czentye
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
Contains abstract classes for concrete layer API modules.
"""
import httplib
import json
import os.path
import threading
import urllib
import urlparse
import uuid
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from Queue import Queue
from SocketServer import ThreadingMixIn

import requests
from requests.exceptions import Timeout, RequestException

from escape import __project__
from escape.util.config import CONFIG
from escape.util.misc import SimpleStandaloneHelper, quit_with_error, \
  get_escape_version
from escape.util.pox_extension import POXCoreRegisterMetaClass
from pox.core import core
from pox.lib.revent import EventMixin


class AbstractAPI(EventMixin):
  """
  Abstract class for UNIFY's API.

  Contain common functions.

  Follows Facade design pattern -> simplified entry/exit point ot the layers.
  """
  # Default value for logger. Should be overwritten by child classes
  _core_name = "AbstractAPI"
  """Default value for logger. Should be overwritten by child classes"""
  # Explicitly defined dependencies as POX components
  dependencies = ()
  """Explicitly defined dependencies as POX components"""

  # Events raised by this class, but already defined in superclass
  # _eventMixin_events = set()

  def __init__ (self, standalone=False, **kwargs):
    """
    Abstract class constructor.

    Handle core registration along with :func:`_all_dependencies_met()`.

    Set given parameters (standalone parameter is mandatory) automatically as:

    >>> self._param_name = param_value

    Base constructor functions have to be called as the last step in derived
    classes. Same situation with :func:`_all_dependencies_met()` respectively.
    Must not override these function, just use :func:`initialize()` for
    init steps. Actual API classes must only call :func:`super()` in their
    constructor with the form:

    >>> super(SpecificAPI, self).__init__(standalone=standalone, **kwargs)

    .. warning::
      Do not use prefixes in the name of event handlers, because of automatic
      dependency discovery considers that as a dependent component and this
      situation cause a dead lock (component will be waiting to each other to
      set up)!

    :param standalone: started in standalone mode or not
    :type standalone: bool
    :return: None
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
      # Wait for the necessary POX component until they are resolved and set
      # up event handlers. The dependencies are given explicitly which are
      # defined in the actual API and not use automatic event handler based
      # dependency discovery to avoid issues come from fully event-driven
      # structure.
      # See more in POXCore document.
      core.core.listen_to_dependencies(self, getattr(self, 'dependencies', ()))

  def _all_dependencies_met (self):
    """
    Called when every component on which depends are initialized on POX core.

    Contain dependency relevant initialization.

    :return: None
    """
    try:
      self.initialize()
      # With fully event-driven communication between the layers the dependency
      # handling takes care by listen_to_dependencies() run into a dead-lock.
      # The root of this problem is the bidirectional or cyclic dependency
      # between the components, so basically the layers will always wait to each
      # other to be registered on core. To avoid this situation the naming
      # convention of event handlers on which the dependency checking based is
      # not followed (a.k.a. leave _handle_<component name>_<event name>) and
      # the event listeners is set up manually. For automatic core registration
      # the components have to contain dependencies explicitly.
      for dep in self.dependencies:
        if not self._standalone:
          if core.core.hasComponent(dep):
            dep_layer = core.components[dep]
            # Register actual event handlers on dependent layer
            dep_layer.addListeners(self)
            # Register dependent layer's event handlers on actual layer
            self.addListeners(dep_layer)
          else:
            raise AttributeError("Component is not registered on core")
        else:
          # In case of standalone mode set up a StandaloneHelper in this object
          # with the name of the dependency to handle raised events
          # automatically
          setattr(self, dep, SimpleStandaloneHelper(self, dep))
      # Subscribe for GoingDownEvent to finalize API classes
      # shutdown() function will be called if POX's core going down
      core.addListenerByName('GoingDownEvent', self.shutdown)
      # Subscribe core event for advanced functions
      # Listeners' name must follow POX naming conventions
      core.addListeners(self)
      # Everything is set up an "running" so register the component on pox.core
      # as a final step. Other dependent component can finish initialization
      # now.
      core.core.register(self._core_name, self)
      # Set "running" config for convenience purposes
      CONFIG.set_layer_loaded(self._core_name)
    except KeyboardInterrupt:
      quit_with_error(
        msg="Initialization of %s was interrrupted by user!" %
            self.__class__.__name__)
    except Exception as e:
      quit_with_error(msg="Abort ESCAPEv2 initialization...", exception=e)

  def initialize (self):
    """
    Init function for child API classes to simplify dynamic initialization.

    Called when every component on which depends are initialized and registered
    in POX core.

    This function should be overwritten by child classes.

    :return: None
    """
    pass

  def shutdown (self, event):
    """
    Finalization, deallocation, etc. of actual component.

    Should be overwritten by child classes.

    :param event: shutdown event raised by POX core
    :type event: GoingDownEvent
    :return: None
    """
    pass

  @staticmethod
  def _read_data_from_file (graph_file):
    """
    Read the given file and return a string formatted as JSON.

    :param graph_file: file path
    :type graph_file: str
    :return: JSON data
    :rtype: str
    """
    if graph_file and not graph_file.startswith('/'):
      graph_file = os.path.abspath(graph_file)
    with open(graph_file) as f:
      graph = f.read()
    return graph

  def __str__ (self):
    """
    Print class type and non-private attributes with their types for debugging.

    :return: specific string
    :rtype: str
    """
    print '<%s.%s object at %s>' % (
      self.__class__.__module__, self.__class__.__name__, hex(id(self)))
    print "Non-private attributes:"
    import pprint

    return pprint.pformat(
      [(f, type(getattr(self, f))) for f in dir(self) if
       not f.startswith('_')])


class RequestStatus(object):
  # State constants
  INITIATED = "INITIATED"
  PROCESSING = "PROCESSING"
  SUCCESS = "SUCCESS"
  ERROR = "ERROR"
  UNKNOWN = "UNKNOWN"

  def __init__ (self, message_id, status, nffg_id=None, params=None):
    self.message_id = message_id
    self.status = status
    self.nffg_id = nffg_id
    self.params = params if params else {}

  def get_callback (self):
    if 'call-back' in self.params:
      return urllib.unquote(self.params['call-back'])
    else:
      return None


class RequestCache(object):
  """
  Store HTTP request states.
  """

  def __init__ (self):
    """
    Init.

    :return: None
    """
    super(RequestCache, self).__init__()
    self.__cache = dict()

  def cache_request (self, message_id, status=None, params=None):
    status = status if status else RequestStatus.INITIATED
    self.__cache[message_id] = RequestStatus(message_id=message_id,
                                             status=status,
                                             params=params)

  def cache_request_by_nffg (self, nffg):
    """
    Add a request to the cache.

    :param nffg: request id
    :type nffg: :class:`NFFG`
    """
    try:
      key = nffg.metadata['params']['message-id']
      self.__cache[key] = RequestStatus(message_id=key,
                                        nffg_id=nffg.id,
                                        status=RequestStatus.INITIATED,
                                        params=nffg.metadata.pop('params'))
      return key
    except KeyError:
      return

  def set_in_progress (self, id):
    """
    Set the result of the request given by the ``id``.

    :param id: request id
    :type id: str or int
    """
    try:
      self.__cache[id].status = RequestStatus.PROCESSING
    except KeyError:
      pass

  def set_result (self, id, result):
    """
    Set the result of the request given by the ``id``.

    :param id: request id
    :type id: str or int
    :param result: the result
    :type result: bool or basestring
    """
    try:
      if type(result) is bool:
        if result:
          self.__cache[id].status = RequestStatus.SUCCESS
        else:
          self.__cache[id].status = RequestStatus.ERROR
      elif isinstance(result, basestring):
        self.__cache[id].status = result
      else:
        self.__cache[id] = RequestStatus.UNKNOWN
    except KeyError:
      pass

  def set_success_result (self, id):
    return self.set_result(id=id, result=RequestStatus.SUCCESS)

  def set_error_result (self, id):
    return self.set_result(id=id, result=RequestStatus.ERROR)

  def get_request (self, message_id):
    """

    :param message_id:
    :rtype: RequestStatus
    """
    try:
      return self.__cache[message_id]
    except KeyError:
      return None

  def get_request_by_nffg_id (self, nffg_id):
    """

    :param nffg_id:
    :rtype: RequestStatus
    """
    for req in self.__cache.itervalues():
      if req.nffg_id == nffg_id:
        return req
    return None

  def get_status (self, id):
    """
    Return the requested result.

    :param id: request id
    :type id: str or int
    """
    try:
      return self.__cache[id].status
    except KeyError:
      return RequestStatus.UNKNOWN


class RESTServer(ThreadingMixIn, HTTPServer, object):
  """
  Base HTTP server for RESTful API.

  Initiate an :class:`HTTPServer` and run it in different thread.
  """
  CALLBACK_TIMEOUT = 1.0

  def __init__ (self, RequestHandlerClass, address='127.0.0.1', port=8008):
    """
      Set up an :class:`BaseHTTPServer.HTTPServer` in a different
      thread.

      :param RequestHandlerClass: Class of a handler which handles HTTP request
      :type RequestHandlerClass: AbstractRequestHandler
      :param address: Used IP address
      :type address: str
      :param port: Used port number
      :type port: int
      :return: None
      """
    HTTPServer.__init__(self, (address, port), RequestHandlerClass)
    self._thread = threading.Thread(target=self.run,
                                    name="REST-%s:%s" % (address, port))
    self._thread.daemon = True
    self.started = False
    self.request_cache = RequestCache()
    self.api_id = None
    self.virtualizer_type = None
    # Cache for the last response to avoid topo recreation
    self.last_response = None
    self.topology_revision = None
    self.scheduler = RequestScheduler()

  def start (self):
    """
    Start RESTServer thread.

    :return: None
    """
    self.started = True
    self._thread.start()

  def stop (self):
    """
    Stop RESTServer thread.

    :return: None
    """
    if self.started:
      self.shutdown()

  def run (self):
    """
    Handle one request at a time until shutdown.

    :return: None
    """
    # Start API loop
    try:
      self.serve_forever()
    except Exception:
      pass

  def invoke_callback (self, message_id, body=None):
    status = self.get_status_by_message_id(message_id=message_id)
    if "call-back" not in status.params:
      return None
    callback_url = status.get_callback()
    if 'message-id' in status.params:
      msg_id = status.params.get('message-id')
    else:
      msg_id = status.message_id
    params = {'message-id': msg_id}
    if status.status == status.SUCCESS:
      params['response-code'] = httplib.OK
      if not body:
        body = "OK"
    else:
      params['response-code'] = httplib.INTERNAL_SERVER_ERROR
      if not body:
        # TODO - return with failed part of the request??
        body = "TODO"
    try:
      ret = requests.post(url=callback_url, params=params, data=body,
                          timeout=self.CALLBACK_TIMEOUT)
      return ret.status_code
    except (RequestException, Timeout):
      return -1

  def get_status_by_message_id (self, message_id):
    """

    :param message_id:
    :rtype: RequestStatus
    """
    return self.request_cache.get_request(message_id)


class RESTError(Exception):
  """
  Exception class for REST errors.
  """

  def __init__ (self, msg=None, code=0):
    """
    Init.

    :param msg: error message
    :type msg: str
    :param code: error code
    :type code: int
    :return: None
    """
    super(RESTError, self).__init__()
    self._msg = msg
    self._code = code

  @property
  def msg (self):
    """
    Return with the message.

    :return: error massage
    :rtype: str
    """
    return self._msg

  @property
  def code (self):
    """
    Return with the error code.

    :return: error code
    :rtype: int
    """
    return int(self._code)

  def __str__ (self):
    """
    Return with spec string representation.

    :return: error representation
    :rtype: str
    """
    return self._msg


class AbstractRequestHandler(BaseHTTPRequestHandler, object):
  """
  Minimalistic RESTful API for Layer APIs.

  Handle /escape/* URLs.

  Method calling permissions represented in escape_intf dictionary.

  .. warning::
    This class is out of the context of the recoco's co-operative thread
    context! While you don't need to worry much about synchronization between
    recoco tasks, you do need to think about synchronization between recoco task
    and normal threads. Synchronisation is needed to take care manually - use
    relevant helper function of core object: :func:`callLater()`/
    :func:`raiseLater()` or use :func:`schedule_as_coop_task()
    <escape.util.misc.schedule_as_coop_task>` decorator defined in
    :mod:`escape.util.misc` on the called function!
  """
  # For HTTP Response messages
  server_version = "ESCAPE/" + get_escape_version()
  """server version for HTTP Response messages"""
  static_prefix = "escape"
  # Bound HTTP verbs to UNIFY's API functions
  request_perm = {
    'GET': ('ping', 'version', 'operations'),
    'POST': ('ping',)}
  """Bound HTTP verbs to UNIFY's API functions"""
  # Name of the layer API to which the server bounded
  bounded_layer = None
  """Name of the layer API to which the server bounded"""
  # Name mapper to avoid Python naming constraint (dict: rpc-name: mapped name)
  rpc_mapper = None
  """Name mapper to avoid Python naming constraint"""
  # Logger name
  LOGGER_NAME = "REST-API"
  """Logger name"""
  # Logger. Should be overrided in child classes
  log = core.getLogger("[%s]" % LOGGER_NAME)
  # Use Virtualizer format
  virtualizer_format_enabled = False
  """Use Virtualizer format"""
  # Default communication approach
  format = "FULL"
  """Default communication approach"""
  MESSAGE_ID_NAME = "message-id"

  def do_GET (self):
    """
    Get information about an entity. R for CRUD convention.
    """
    self._process_url()

  def do_POST (self):
    """
    Create an entity. C for CRUD convention.

    :return: None
    """
    self._process_url()

  def do_PUT (self):
    """
    Update an entity. U for CRUD convention.

    :return: None
    """
    self._process_url()

  def do_DELETE (self):
    """
    Delete an entity. D for CRUD convention.

    :return: None
    """
    self._process_url()

  # Unsupported HTTP verbs

  def do_OPTIONS (self):
    """
    Handling unsupported HTTP verbs.

    :return: None
    """
    self.send_error(httplib.NOT_IMPLEMENTED)
    self.wfile.close()

  def do_HEAD (self):
    """
    Handling unsupported HTTP verbs.

    :return: None
    """
    # self.send_error(501)
    self.wfile.close()

  def do_TRACE (self):
    """
    Handling unsupported HTTP verbs.

    :return: None
    """
    self.send_error(httplib.NOT_IMPLEMENTED)
    self.wfile.close()

  def do_CONNECT (self):
    """
    Handling unsupported HTTP verbs.

    :return: None
    """
    self.send_error(httplib.NOT_IMPLEMENTED)
    self.wfile.close()

  def get_request_params (self):
    params = {}
    query = urlparse.urlparse(self.path).query
    if query:
      query = query.split('&')
      for param in query:
        if '=' in param:
          name, value = param.split('=', 1)
          params[name] = value
        else:
          params[param] = True
    # Check message-id in headers as backup
    if self.MESSAGE_ID_NAME not in params:
      if self.MESSAGE_ID_NAME in self.headers:
        params[self.MESSAGE_ID_NAME] = self.headers[self.MESSAGE_ID_NAME]
        self.log.debug("Detected message id: %s" % params[self.MESSAGE_ID_NAME])
      else:
        params[self.MESSAGE_ID_NAME] = str(uuid.uuid1())
        self.log.debug("No message-id! Generated id: %s"
                       % params[self.MESSAGE_ID_NAME])
    else:
      self.log.debug("Detected message id: %s" % params[self.MESSAGE_ID_NAME])
    self.log.debug("Detected request parameters: %s" % params)
    return params

  def _process_url (self):
    """
    Split HTTP path and call the carved function if it is defined in this class
    and in request_perm.

    :return: None
    """
    self.log.debug(
      ">>> Got HTTP request: %s" % str(self.raw_requestline).rstrip())
    http_method = self.command.upper()
    real_path = urlparse.urlparse(self.path).path
    try:
      prefix = '/%s/' % self.static_prefix
      if real_path.startswith(prefix):
        self.func_name = real_path[len(prefix):].split('/')[0]
        if self.rpc_mapper:
          try:
            self.func_name = self.rpc_mapper[self.func_name]
          except KeyError:
            # No need for RPC name mapping, continue
            pass
        if http_method in self.request_perm:
          if self.func_name in self.request_perm[http_method]:
            if hasattr(self, self.func_name):
              # Response is assembled, and sent back by handler functions
              params = self.get_request_params()
              getattr(self, self.func_name)(params=params)
            else:
              self.send_error(httplib.INTERNAL_SERVER_ERROR,
                              "Missing handler for actual request!")
          else:
            self.send_error(httplib.NOT_ACCEPTABLE)
        else:
          self.send_error(httplib.NOT_IMPLEMENTED)
      else:
        self.send_error(httplib.NOT_FOUND,
                        "URL path is not valid or misconfigured!")
    except RESTError as e:
      # Handle all the errors
      if e.code:
        self.send_error(e.code, e.msg)
      else:
        self.send_error(httplib.INTERNAL_SERVER_ERROR, e.msg)
    except:
      # Got unexpected exception
      self.send_error(httplib.INTERNAL_SERVER_ERROR)
      raise
    finally:
      self.func_name = None
      self.wfile.flush()
      self.wfile.close()
    self.log.debug(
      ">>> HTTP request: %s ended!" % str(self.raw_requestline).rstrip())

  def _get_body (self):
    """
    Parse HTTP request body as a plain text.

    .. note::

      Call only once by HTTP request.

    .. note::

      Parsed JSON object is Unicode.

    GET, DELETE messages don't have body - return empty dict by default.

    :return: request body in str format
    :rtype: str
    """
    charset = 'utf-8'
    # json.loads returns an empty dict if it's called with an empty string
    # but this check we can avoid to respond with unnecessary missing
    # content-* error
    if self.command.upper() in ('GET', 'DELETE'):
      return {}
    try:
      splitted_type = self.headers['Content-Type'].split('charset=')
      if len(splitted_type) > 1:
        charset = splitted_type[1]
      content_len = int(self.headers['Content-Length'])
      raw_data = self.rfile.read(size=content_len).encode(charset)
      # Avoid missing param exception by hand over an empty json data
      return raw_data if content_len else "{}"
    except KeyError as e:
      # Content-Length header is not defined
      # or charset is not defined in Content-Type header.
      if e.args[0] == 'Content-Type':
        self.log.warning("Missing header from request: %s" % e.args[0])
      if e.args[0] == 'Content-Length':
        # 411: ('Length Required', 'Client must specify Content-Length.'),
        raise RESTError(code=httplib.LENGTH_REQUIRED)
      else:
        raise RESTError(code=httplib.PRECONDITION_FAILED,
                        msg="Missing header from request: %s" % e.args[0])
    except ValueError as e:
      # Failed to parse request body to JSON
      self.log_error("Request parsing failed: %s", e)
      raise RESTError(code=httplib.UNSUPPORTED_MEDIA_TYPE,
                      msg="Request parsing failed: %s" % e)

  def send_REST_headers (self):
    """
    Set the allowed REST verbs as an HTTP header (Allow).

    :return: None
    """
    try:
      if self.func_name:
        self.send_header('Allow', ','.join(
          [str(verbs) for verbs, f in self.request_perm.iteritems() if
           self.func_name in f]))
    except KeyError:
      pass

  def send_acknowledge (self, code=None, message_id=None):
    """
    Send back acknowledge message.

    :param message_id: response body
    :param message_id: dict
    :return: None
    """
    if code:
      self.send_response(int(code))
    else:
      self.send_response(httplib.ACCEPTED)
    if message_id:
      self.send_header('message-id', message_id)
    self.send_REST_headers()
    self.end_headers()

  def send_raw_response (self, raw_data, code=None, content="text/plain",
                         encoding='utf-8'):
    """
    Send requested data.

    :param raw_data: data in JSON format
    :type raw_data: dict
    :param encoding: Set data encoding (optional)
    :type encoding: str
    :return: None
    """
    if code:
      self.send_response(int(code))
    else:
      self.send_response(httplib.OK)
    self.send_header('Content-Type', '%s; charset=%s' % (content, encoding))
    self.send_header('Content-Length', len(raw_data))
    self.send_REST_headers()
    self.end_headers()
    self.wfile.write(raw_data)

  def send_json_response (self, data, code=None, encoding='utf-8'):
    """
    Send requested data in JSON format.

    :param data: data in JSON format
    :type data: dict
    :param encoding: Set data encoding (optional)
    :type encoding: str
    :return: None
    """
    response_body = json.dumps(data, encoding=encoding)
    return self.send_raw_response(raw_data=response_body,
                                  code=code,
                                  content="application/json",
                                  encoding=encoding)

  error_content_type = "text/json"
  """Content-Type for error responses"""

  def send_error (self, code, message=None):
    """
    Override original function to send back allowed HTTP verbs and set format
    to JSON.

    :param code: error code
    :type code: int
    :param message: error message
    :type message: str
    :return: None
    """
    try:
      short, long = self.responses[code]
    except KeyError:
      short, long = '???', '???'
    if message is None:
      message = short
    explain = long
    self.log_error("code %d, message %s", code, message)
    # using _quote_html to prevent Cross Site Scripting attacks (see bug
    # #1100201)
    content = {"title": "Error response",
               'Error code': code,
               'Message': message,
               'Explanation': explain}
    self.send_response(code, message)
    self.send_header("Content-Type", self.error_content_type)
    self.send_header('Connection', 'close')
    # self.send_REST_headers()
    self.end_headers()
    if self.command != 'HEAD' and code >= 200 and code not in (204, 304):
      self.wfile.write(json.dumps(content))

  def log_error (self, mformat, *args):
    """
    Overwritten to use POX logging mechanism.

    :param mformat: message format
    :type mformat: str
    :return: None
    """
    self.log.warning("%s - - [%s] %s" % (
      self.client_address[0], self.log_date_time_string(), mformat % args))

  def log_message (self, mformat, *args):
    """
    Disable logging of incoming messages.

    :param mformat: message format
    :type mformat: str
    :return: None
    """
    pass

  def log_full_message (self, mformat, *args):
    """
    Overwritten to use POX logging mechanism.

    :param mformat: message format
    :type mformat: str
    :return: None
    """
    self.log.debug("%s - - [%s] %s" % (
      self.client_address[0], self.log_date_time_string(), mformat % args))

  def _proceed_API_call (self, function, *args, **kwargs):
    """
    Fail-safe method to call API function.

    The cooperative micro-task context is handled by actual APIs.

    Should call this with params, not directly the function of actual API.

    :param function: function name
    :type function: str
    :param args: Optional params
    :type args: tuple
    :param kwargs: Optional named params
    :type kwargs: dict
    :return: None
    """
    if core.core.hasComponent(self.bounded_layer):
      layer = core.components[self.bounded_layer]
      if hasattr(layer, function):
        return getattr(layer, function)(*args, **kwargs)
      else:
        self.log.warning(
          'Mistyped or not implemented API function call: %s ' % function)
        raise RESTError(
          msg='Mistyped or not implemented API function call: %s ' % function)
    else:
      self.log.error('Error: No component has registered with the name: %s, '
                     'ABORT function call!' % self.bounded_layer)

  ##############################################################################
  # Basic REST-API functions
  ##############################################################################

  def ping (self, params):
    """
    For testing REST API aliveness and reachability.

    :return: None
    """
    response_body = "OK"
    self.send_response(httplib.OK)
    self.send_header('Content-Type', 'text/plain')
    self.send_header('Content-Length', len(response_body))
    self.send_REST_headers()
    self.end_headers()
    self.wfile.write(response_body)

  def version (self, params):
    """
    Return with version

    :return: None
    """
    self.log.debug("Call REST-API function: version")
    self.send_json_response({"name": __project__,
                             "version": get_escape_version()})

  def operations (self, params):
    """
    Return with allowed operations

    :return: None
    """
    self.log.debug("Call REST-API function: operations")
    self.send_json_response(self.request_perm)


class APIRequest(object):
  def __init__ (self, id, layer, function, kwargs):
    self.id = id
    self.layer = layer
    self.function = function
    self.kwargs = kwargs

  def __str__ (self):
    return "Request(id: %s, %s  -->  %s, params: %s)" % (
      self.id, self.layer, self.function, self.kwargs.keys())


class RequestScheduler(threading.Thread):
  """
  """
  __metaclass__ = POXCoreRegisterMetaClass
  _core_name = "RequestScheduler"

  def __init__ (self):
    super(RequestScheduler, self).__init__(name=self._core_name)
    self.daemon = True
    self.__queue = Queue()
    self.__hooks = {}
    self.__condition = threading.Condition()
    self.__progress = None
    self.log = core.getLogger("SCHEDULER")
    self.start()
    self.log.info('Init %s' % self)

  @property
  def orchestration_in_progress (self):
    return self.__progress is not None

  def set_orchestration_finished (self, id):
    if self.__progress is None:
      self.log.debug("No orchestration in progress!")
    elif self.__progress != id:
      self.log.debug("Another request is in progress...")
    else:
      self.log.info("Set orchestration status of request: %s --> FINISHED"
                    % self.__progress)
      with self.__condition:
        self.__progress = None
        self.__condition.notify()

  def schedule_request (self, id, layer, function, **kwargs):
    self.__queue.put(APIRequest(id=id,
                                layer=layer,
                                function=function,
                                kwargs=kwargs))
    self.log.info("Schedule request on %s --> %s..." % (layer, function))
    self.log.debug("Remained requests: %s" % self.__queue.qsize())

  def _proceed_API_call (self, request):
    """
    Fail-safe method to call API function.
    The cooperative micro-task context is handled by actual APIs.
    Should call this with params, not directly the function of actual API.

    :param request: scheduled request container object
    :type request: APIRequest
    :return: None
    """
    self.log.info("Start request processing in coop-task: %s" % request)
    if core.core.hasComponent(request.layer):
      layer = core.components[request.layer]
      if hasattr(layer, request.function):
        return getattr(layer, request.function)(**request.kwargs)
      else:
        raise RESTError(msg='Mistyped or not implemented API function call: %s '
                            % request.function)
    else:
      raise RESTError(msg='Error: No component has registered with name: %s, '
                          'ABORT function call!' % request.layer)

  def run (self):
    while True:
      with self.__condition:
        if self.__progress:
          self.__condition.wait()
        request = self.__queue.get()
        self.__progress = request.id
        self._proceed_API_call(request=request)
