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
import threading
import urlparse
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from threading import Thread, Timer

from escape.adapt import log as log
from escape.util.config import CONFIG
from escape.util.misc import Singleton

log = log.getChild('callback')


class CallbackHandler(BaseHTTPRequestHandler):
  RESULT_PARAM_NAME = "response-code"
  MESSAGE_ID_NAME = "message-id"

  def log_message (self, format, *args):
    """
    Disable logging of incoming messages.

    :param format: message format
    :type format: str
    :return: None
    """
    pass

  def do_POST (self):
    self._dispatch_request()

  def _dispatch_request (self):
    self.__process_request()
    self.send_response(200)
    self.send_header('Connection', 'close')
    self.end_headers()

  def __process_request (self):
    log.debug("Received callback request with path: %s" % self.path)
    params = self.__get_request_params()
    if self.RESULT_PARAM_NAME in params and self.MESSAGE_ID_NAME in params:
      body = self._get_body()
      if body:
        log.debug("Received callback body size: %s" % len(body))
      else:
        log.debug("No callback body")
      domain = self.__get_domain()
      if not domain:
        log.warning("No domain was detected in URL: %s!" % self.path)
      self.server.invoke_hook(msg_id=params.get(self.MESSAGE_ID_NAME),
                              result=params.get(self.RESULT_PARAM_NAME),
                              domain=domain,
                              body=body)
    else:
      log.warning("Received callback with missing params: %s" % params)

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
    try:
      splitted_type = self.headers.get('Content-Type', "").split('charset=')
      if len(splitted_type) > 1:
        charset = splitted_type[1]
      content_len = int(self.headers['Content-Length'])
      raw_data = self.rfile.read(size=content_len).encode(charset)
      # Avoid missing param exception by hand over an empty json data
      return raw_data if content_len else ""
    except KeyError as e:
      # Content-Length header is not defined
      # or charset is not defined in Content-Type header.
      log.warning(str(e))
      if e.args[0] == 'Content-Length':
        log.warning("Missing content-type from request: %s" % e.args[0])
    except ValueError as e:
      # Failed to parse request body to JSON
      self.log_error("Request parsing failed: %s", e)

  def __get_request_params (self):
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
    return params

  def __get_domain (self):
    path = urlparse.urlparse(self.path).path.split('/')
    if len(path) < 2:
      log.warning("Domain part is missing from URL: %s!" % self.path)
      return None
    else:
      return path[1]


class Callback(object):
  def __init__ (self, hook, callback_id, domain, type, request_id=None,
                data=None):
    self.hook = hook
    self.callback_id = callback_id
    self.domain = domain
    self.type = type
    self.request_id = request_id
    self.__timer = None
    self.data = data
    self.result_code = None
    self.body = None

  def setup_timer (self, timeout, hook, **kwargs):
    if not timeout:
      log.debug("Timeout disabled for request callback: %s" % self.request_id)
      return
    if not self.__timer:
      log.debug("Setup timeout: %s for callback: %s"
                % (timeout, self.callback_id))
      self.__timer = Timer(timeout, hook, kwargs=kwargs)
      self.__timer.start()
    else:
      log.warning("Callback timer has already been set up!")

  def stop_timer (self):
    if self.__timer:
      self.__timer.cancel()
      self.__timer = None

  def get_timer_timeout (self):
    return float(self.__timer.interval)

  def short (self):
    return "Callback(id: %s, request_id: %s, domain: %s, result: %s)" \
           % (self.callback_id, self.request_id, self.domain, self.result_code)


class CallbackManager(HTTPServer, Thread):
  # Singleton
  __metaclass__ = Singleton
  """Singleton"""
  DEFAULT_SERVER_ADDRESS = "0.0.0.0"
  DEFAULT_POSTFIX = "callback"
  DEFAULT_PORT = 9000
  DEFAULT_WAIT_TIMEOUT = 10.0

  def __init__ (self, address=DEFAULT_SERVER_ADDRESS, port=DEFAULT_PORT,
                timeout=DEFAULT_WAIT_TIMEOUT, **kwargs):
    Thread.__init__(self, name="%s(%s:%s)" % (self.__class__.__name__,
                                              address, port))
    HTTPServer.__init__(self, (address, port), CallbackHandler,
                        bind_and_activate=False)
    self.wait_timeout = float(timeout)
    self.__register = {}
    self.__domain_proxy = {}
    self.daemon = True
    self.__blocking_mutex = threading.Event()
    log.debug("Initiate %s" % self.__class__.__name__)

  @classmethod
  def initialize_on_demand (cls):
    global_cb_cfg = CONFIG.get_callback_config()
    callback_manager = cls(**global_cb_cfg)
    callback_manager.start()
    return callback_manager

  def register_url (self, domain, host, port):
    if domain in self.__domain_proxy:
      log.warning("Overriding domain address: %s for domain %s"
                  % (self.__domain_proxy[domain], domain))
    url = "http://%s:%s/%s/%s" % (host, port, domain, self.DEFAULT_POSTFIX)
    log.debug("Register explicit URL: %s for domain: %s" % (url, domain))
    self.__domain_proxy[domain] = url

  def get_url (self, domain):
    if domain in self.__domain_proxy:
      explicit_url = self.__domain_proxy[domain]
      log.debug("Using explicit URL for callback: %s" % explicit_url)
      return explicit_url
    else:
      log.debug("Using generated callback URL...")
      return "http://%s:%s/%s/%s" % (self.server_address[0],
                                     self.server_address[1],
                                     domain,
                                     self.DEFAULT_POSTFIX)

  def bind_and_activate (self):
    """
    Bind the listening socket and activate the HTTPServer.
    Moved from the constructor of :class:`HTTPServer`.
    """
    try:
      self.server_bind()
      self.server_activate()
    except:
      self.server_close()
      raise

  def run (self):
    self.bind_and_activate()
    try:
      log.debug("Start %s on %s:%s" % (self.__class__.__name__,
                                       self.server_address[0],
                                       self.server_address[1]))
      self.serve_forever()
    except KeyboardInterrupt:
      raise
    except Exception as e:
      log.error("Got exception in %s: %s" % (self.__class__.__name__, e))
    finally:
      self.server_close()

  def start (self):
    if not self.is_alive():
      super(CallbackManager, self).start()

  def shutdown (self):
    if self.is_alive():
      super(CallbackManager, self).shutdown()

  def subscribe_callback (self, hook, cb_id, domain, type, req_id=None,
                          data=None, timeout=None):
    log.debug("Register callback for response: %s on domain: %s" %
              (cb_id, domain))
    if cb_id not in self.__register:
      cb = Callback(hook=hook, callback_id=cb_id, type=type,
                    domain=domain, request_id=req_id, data=data)
      _timeout = timeout if timeout is not None else self.wait_timeout
      cb.setup_timer(_timeout, self.invoke_hook, msg_id=cb_id, result=0)
      self.__register[(domain, cb_id)] = cb
      return cb
    else:
      log.warning("Hook is already registered for id: %s on domain: %s"
                  % (cb_id, domain))

  def unsubscribe_callback (self, cb_id, domain):
    log.debug("Unregister callback for response: %s from domain: %s"
              % (cb_id, domain))
    cb = self.__register.pop((domain, cb_id), None)
    if cb:
      cb.stop_timer()
    return cb

  def invoke_hook (self, msg_id, domain, result, body=None):
    try:
      result = int(result)
    except ValueError:
      log.error("Received response code is not valid: %s! Abort callback..."
                % result)
      return
    if (domain, msg_id) not in self.__register:
      log.warning("Received unregistered callback with id: %s from domain: %s"
                  % (msg_id, domain))
      return
    log.debug("Received valid callback with id: %s, result: %s from domain: %s"
              % (msg_id, "TIMEOUT" if not result else result, domain))
    cb = self.__register.get((domain, msg_id))
    if cb is None:
      log.error("Missing callback: %s from register!" % msg_id)
      return
    cb.result_code = result
    cb.body = body
    if cb.hook is None:
      log.debug("No hook was defined!")
      self.__blocking_mutex.set()
      return
    elif callable(cb.hook):
      log.debug("Schedule callback hook: %s" % cb.short())
      cb.hook(callback=cb)
    else:
      log.warning("No callable hook was defined for the received callback: %s!"
                  % msg_id)

  def register_and_block_wait (self, cb_id, type, req_id=None, data=None,
                               timeout=None):
    cb = self.subscribe_callback(hook=None, cb_id=cb_id, type=type,
                                 req_id=req_id, domain=None,
                                 data=data, timeout=timeout)
    _timeout = timeout if timeout is not None else self.wait_timeout + 1
    log.debug("Waiting for callback result...")
    self.__blocking_mutex.wait(timeout=_timeout)
    self.__blocking_mutex.clear()
    return self.unsubscribe_callback(cb_id=cb.callback_id, domain=None)

  def wait_for_callback (self, cb):
    _timeout = cb.get_timer_timeout() + 1.0
    log.debug("Waiting for callback result...")
    self.__blocking_mutex.wait(timeout=_timeout)
    self.__blocking_mutex.clear()
    return self.unsubscribe_callback(cb_id=cb.callback_id,
                                     domain=cb.domain)
