# Copyright 2015 Lajos Gerecs, Janos Czentye
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
import httplib
import json
import logging
import os
import pprint
import urllib
import urlparse
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Lock, Timer

import requests
from requests import ConnectionError

from testframework.testcases.basic import BasicSuccessfulTestCase

log = logging.getLogger()

# Basic REST interface calls
RPC_PING = "ping"
RPC_VERSION = "version"
RPC_OPERATIONS = "operations"
# Virtualizer interface RPC names
RPC_GET_CONFIG = "get-config"
RPC_EDIT_CONFIG = "edit-config"
# Extended RPC names
RPC_STATUS = "status"
RPC_MAPPINGS = "mappings"
RPC_INFO = "info"


class RPCCallMock(object):
  """
  A mock class for an RPC call.
  """

  def __init__ (self, rpc_name, response_path=None, code=None, timeout=None):
    """
    :param rpc_name: name of the rpc call e.g get-config
    :type rpc_name: str
    :param response_path: path of the response body file
    :type response_path: str
    :param code: return code
    :type code: int
    """
    self.call = rpc_name
    self.response_path = response_path
    self.code = code if code else httplib.OK
    self.timeout = timeout

  def __repr__ (self):
    return "CallMock(response: %s, code: %s, timeout=%s)" \
           % (self.response_path, self.code, self.timeout)

  def get_response_body (self):
    if not self.response_path:
      return
    with open(self.response_path) as f:
      log.debug("Read response from file: %s" % self.response_path)
      return f.read()


class DomainMock(object):
  """
  Main mock class wich represent a domain aka a Domain Orchestrator REST-API.
  Contains call mock objects for registered mocked responses.
  """
  DEFAULT_RESPONSE_CODE = httplib.OK

  def __init__ (self, domain):
    self.domain = domain
    self.calls = {}

  def add_call (self, rpc_name, **kwargs):
    """
    Register a mocked call object.

    :param rpc_name: rpc name e.g. get-config
    :type rpc_name: str
    :param kwargs: params for :class:`PRCCallMock` class
    :type kwargs: dict
    :return: None
    """
    self.calls[rpc_name] = RPCCallMock(rpc_name=rpc_name, **kwargs)

  def get_call (self, rpc_name):
    """
    :rtype: RPCCallMock
    """
    return self.calls.get(rpc_name, None)

  def __repr__ (self):
    return "ResponseMock(domain: %s, calls: %s)" % (self.domain, self.calls)


class DORequestHandler(BaseHTTPRequestHandler):
  """
  Handler class to handle received request.
  """
  MSG_ID_NAME = 'message-id'
  CALLBACK_NAME = "call-back"
  # Override server name for HTTP response header: Server
  server_version = "DomainAPIMocker"

  def log_message (self, format, *args):
    """
    Disable default logging of incoming messages.
    """
    log.debug("%s - - [%s] Sending %s" %
              (self.__class__.__name__,
               self.log_date_time_string(),
               format % args))

  def do_POST (self):
    self.process_request()

  def do_GET (self):
    self.process_request()

  def process_request (self):
    """
    Process the received request and respond according to registered response
    mocks or the default response policy.

    :return: None
    """
    log.debug("\n%s - - [%s] Received %s" %
              (self.__class__.__name__,
               self.log_date_time_string(),
               self.path))
    p = urlparse.urlparse(self.path).path
    try:
      domain, call = p.strip('/').split('/', 1)
    except:
      log.error("Wrong URL: %s" % self.path)
      self.send_error(httplib.NOT_ACCEPTABLE)
      return
    if domain not in self.server.responses:
      self._return_default(call=call)
      return
    call_mock = self.server.responses[domain].get_call(call)
    if call_mock is None:
      self._return_default(call=call)
      return
    self._return_response(code=call_mock.code,
                          mock=call_mock,
                          timeout=call_mock.timeout)

  def __get_request_params (self):
    """
    Examine callback request params and header field to construct a parameter
    dict.

    :return: parameters of the callback call
    :rtype: dict
    """
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
    if self.MSG_ID_NAME not in params:
      if self.MSG_ID_NAME in self.headers:
        params[self.MSG_ID_NAME] = self.headers[self.MSG_ID_NAME]
    return params

  def _return_default (self, call):
    """
    Defined the default response behaviour if a received RPC request is not
    pre-defined.

    :param call: rpc call name e.g. get-config
    :type call. str
    :return: None
    """
    log.debug("Unregistered call! Sending default response...")
    if call == RPC_PING:
      self._return_ping()
    elif call == RPC_VERSION:
      self._return_version()
    elif call == RPC_OPERATIONS:
      self._response_operations()
    elif call == RPC_GET_CONFIG:
      self._return_response(code=httplib.NOT_FOUND)
    elif call == RPC_EDIT_CONFIG:
      self._return_response(code=httplib.ACCEPTED)
    elif call == RPC_MAPPINGS:
      # TODO - assemble default body ??
      self._return_response(code=httplib.OK)
    elif call == RPC_INFO:
      # TODO - assemble default body ??
      self._return_response(code=httplib.OK)
    else:
      self._return_response(code=httplib.NOT_IMPLEMENTED)

  def _return_ping (self):
    _body = "OK"
    self.send_response(code=httplib.OK)
    self.send_header('Content-Type', 'text/plain')
    self.send_header('Content-Length', len(_body))
    self.end_headers()
    self.wfile.write(_body)

  def _return_version (self):
    _body = json.dumps({"name": "ESCAPE Test Framework", "version": 1.0})
    self.send_response(code=httplib.OK)
    self.send_header('Content-Type', 'text/json')
    self.send_header('Content-Length', len(_body))
    self.end_headers()
    self.wfile.write(_body)

  def _response_operations (self):
    ops = [o for o in globals() if o.startswith("RPC_")]
    _body = {"GET": ops,
             "POST": ops}
    self.send_response(code=httplib.OK)
    self.send_header('Content-Type', 'text/json')
    self.send_header('Content-Length', len(_body))
    self.end_headers()
    self.wfile.write(_body)

  def _return_response (self, code, body=None, mock=None, timeout=None):
    """
    Generic function to response to an RPC call with related HTTP headers.

    :param code: response code
    :type code: int
    :param body: responded body:
    :type body: str
    :return: None
    """
    self.server.msg_cntr += 1
    params = self.__get_request_params()
    if self.MSG_ID_NAME in params:
      msg_id = params[self.MSG_ID_NAME]
    else:
      msg_id = self.server.msg_cntr
    body = mock.get_response_body() if mock else None
    if self.CALLBACK_NAME in params:
      cb_url = urllib.unquote(params[self.CALLBACK_NAME])
      self.server.setup_callback(url=cb_url,
                                 code=code,
                                 body=body,
                                 msg_id=msg_id,
                                 timeout=timeout)
      log.debug("Request accepted by default if callback is used")
      code = httplib.OK if body else httplib.ACCEPTED
    self.send_response(code=code)
    if body:
      self.send_header("Content-Type", "application/xml")
    self.send_header(self.MSG_ID_NAME, msg_id)
    self.end_headers()
    if body:
      self.wfile.write(body)
      self.wfile.flush()
    log.debug("%s - - End request with response: %s, message-id: %s"
              % (self.__class__.__name__, code, msg_id))
    return


class DomainOrchestratorAPIMocker(HTTPServer, Thread):
  DEFAULT_PORT = 7000
  FILE_PATH_SEPARATOR = "_"
  FILE_RESPONSE_PREFIX = "response"
  DEFAULT_CALLBACK_DELAY = 1.0

  def __init__ (self, address="localhost", port=DEFAULT_PORT,
                callback_delay=DEFAULT_CALLBACK_DELAY, **kwargs):
    Thread.__init__(self, name="%s(%s:%s)" % (self.__class__.__name__,
                                              address, port))
    # do not bind the socket in the constructor when the class is expected to be
    # initialized multiple times
    HTTPServer.__init__(self, (address, port), DORequestHandler,
                        bind_and_activate=False)
    self.callback_delay = float(callback_delay)
    self.daemon = True
    self.responses = {}
    self.msg_cntr = 0
    self.__callback_lock = Lock()  # Synchronize callback's Timer hook calls
    self._suppress_requests_logging()

  @staticmethod
  def _suppress_requests_logging (level=None):
    if level is not None:
      level = level
    elif log.getEffectiveLevel() < logging.INFO:
      level = log.getEffectiveLevel()
    else:
      level = logging.WARNING
    logging.getLogger("requests").setLevel(level)
    logging.getLogger("urllib3").setLevel(level)

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

  def register_responses_from_dir (self, dirname):
    """
    Register responses from the testcase dir.

    The defined response file names must follow the syntax:

    <dedicated_response_prefix>_<domain_name>_<rpc_call_name>.xml

    e.g. response_docker1_edit-config.xml

    Dedicated response code can not be defined with this function.

    If a received RPC or domain is not registered the default responder
    function will be invoked to response to the tested ESCAPE process.

    :param dirname: testcase dir path
    :type dirname: str
    :return: None
    """
    for f in os.listdir(dirname):
      if f.startswith(self.FILE_RESPONSE_PREFIX):
        parts = f.split(self.FILE_PATH_SEPARATOR, 2)
        if len(parts) < 3:
          log.error("Wrong filename: %s!")
          continue
        domain, call = parts[1:]
        if domain not in self.responses:
          self.responses[domain] = DomainMock(domain=domain)
        rpc = call.rsplit('.', 1)[0]
        path = os.path.join(dirname, f)
        code = httplib.ACCEPTED if rpc == RPC_EDIT_CONFIG else httplib.OK
        self.responses[domain].add_call(rpc_name=rpc,
                                        response_path=path,
                                        code=code)
    log.debug("Registered responses: %s" % pprint.pformat(self.responses))

  def register_responses (self, dirname, responses):
    """
    Register responses for Domain Orchestrators from a 3-element tuple.

    A response schema must contain the elements in that order:
      - domain name e.g. mininet
      - rpc call name e.g. edit-config
      - file name of the responded data relative to `dirname` or response
      code e.g. response1.xml or 404

    The used URL path for a mocked domain follows the syntax:

    http://localhost:<configured_port>/<domain_name>/<rpc_call_name>

    If a received RPC or domain is not registered the default responder
    function will be invoked to response to the tested ESCAPE process.

    :param dirname: testcase dir path
    :type dirname: str
    :param responses: list of (domain, call, return value)
    :type responses: list of tuples
    :return: None
    """
    for resp in responses:
      if not {"domain", "rpc", "return"}.issubset(set(resp)):
        log.error("Defined response is malformed: %s!" % resp)
      domain, rpc, ret = resp.get("domain"), resp.get("rpc"), resp.get("return")
      if domain not in self.responses:
        self.responses[domain] = DomainMock(domain=domain)
      if isinstance(ret, int):
        self.responses[domain].add_call(rpc_name=rpc,
                                        code=ret,
                                        timeout=resp.get('timeout'))
      else:
        path = os.path.join(dirname, ret)
        code = httplib.ACCEPTED if rpc == RPC_EDIT_CONFIG else httplib.OK
        self.responses[domain].add_call(rpc_name=rpc,
                                        response_path=path,
                                        code=code,
                                        timeout=resp.get('timeout'))
    log.debug("Registered responses: %s" % pprint.pformat(self.responses))

  def run (self):
    """
    Entry point of the worker thread.

    :return: None
    """
    self.bind_and_activate()
    try:
      self.serve_forever()
    except KeyboardInterrupt:
      raise
    except Exception as e:
      log.error("Got exception in %s: %s" % (self.__class__.__name__, e))
    finally:
      self.server_close()

  def setup_callback (self, url, code, msg_id, body=None, timeout=None):
    """
    Schedule a callback with the given parameters.

    :param url: callback URL
    :type url: str
    :param code: response code calculated for the original request
    :type code: int
    :param msg_id: message-id of the response
    :type msg_id: str
    :return: None
    """
    timeout = timeout if timeout is not None else self.callback_delay
    log.debug("Setup callback: %s, code: %s, message-id: %s, timeout: %s"
              % (url, code, msg_id, timeout))
    t = Timer(timeout, self.callback_hook,
              kwargs={"url": url, "code": code, "msg_id": msg_id, "body": body})
    t.start()

  def callback_hook (self, url, code, msg_id, body):
    """
    Send back a registered callback to the tested ESCAPE process ina
    synchronized way.

    :param url: callback URL
    :type url: str
    :param code: response-code
    :type code: int
    :param msg_id: message-id
    :type msg_id: str or int
    :return: None
    """
    with self.__callback_lock:
      params = {"message-id": msg_id,
                "response-code": 200 if code < 300 else 500}
      log.debug("\nInvoke callback: %s - %s" % (url, params))
      try:
        requests.post(url=url, data=body, params=params)
      except ConnectionError as e:
        log.error("Received exception during calling hook: %s" % e)


class DomainMockingSuccessfulTestCase(BasicSuccessfulTestCase):
  """
  Dedicated TestCase class with basic successful testing and mocked
  DomainOrchestrators.
  """

  def __init__ (self, responses=None, **kwargs):
    super(DomainMockingSuccessfulTestCase, self).__init__(**kwargs)
    self.domain_mocker = DomainOrchestratorAPIMocker(**kwargs)
    dir = self.test_case_info.full_testcase_path
    if responses:
      self.domain_mocker.register_responses(dirname=dir, responses=responses)
    else:
      self.domain_mocker.register_responses_from_dir(dirname=dir)

  def setUp (self):
    super(DomainMockingSuccessfulTestCase, self).setUp()
    self.domain_mocker.start()

  def tearDown (self):
    super(DomainMockingSuccessfulTestCase, self).tearDown()
    self.domain_mocker.shutdown()


if __name__ == '__main__':
  # Some tests
  doam = DomainOrchestratorAPIMocker(daemon=False)
  dm = DomainMock(domain="escape")
  cm1 = RPCCallMock(rpc_name="edit-config", code=500)
  cm2 = RPCCallMock(rpc_name="get-config", code=200)
  cm2.get_response_body = lambda: "<TEST>testbody<TEST>"
  dm.calls["edit-config"] = cm1
  dm.calls["get-config"] = cm2
  doam.responses["escape"] = dm
  doam.start()
