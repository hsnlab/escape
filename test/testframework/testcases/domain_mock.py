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
import logging
import os
import pprint
import time
import urlparse
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

from testframework.testcases.basic import BasicSuccessfulTestCase

log = logging.getLogger()


class DORequestHandler(BaseHTTPRequestHandler):
  RPC_PING = "ping"
  RPC_GET_CONFIG = "get-config"
  RPC_EDIT_CONFIG = "edit-config"
  REQUEST_HEADER_MSG_ID = 'message-id'

  server_version = "DomainAPIMocker"

  def log_message (self, format, *args):
    """
    Disable logging of incoming messages.
    """
    log.debug("%s - - [%s] %s\n" %
              (self.__class__.__name__,
               self.log_date_time_string(),
               format % args))

  def do_POST (self):
    self.process_request()

  def do_GET (self):
    self.process_request()

  def process_request (self):
    p = urlparse.urlparse(self.path).path
    try:
      domain, call = p.strip('/').split('/', 1)
    except:
      log.error("Wrong URL: %s" % self.path)
      self.send_error(406)
      return
    if domain not in self.server.responses:
      self._return_default(call=call)
      return
    call_mock = self.server.responses[domain].get_call(call)
    if call_mock is None:
      self._return_default(call=call)
      return
    self._return_response(code=call_mock.code,
                          body=call_mock.get_response_body())

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
    if 'message-id' not in params:
      if 'message-id' in self.headers:
        params['message-id'] = self.headers['message-id']
    return params

  def _return_default (self, call):
    if call == self.RPC_PING:
      self._return_response(code=200, body="OK")
    if call == self.RPC_GET_CONFIG:
      self._return_response(code=404)
    elif call == self.RPC_EDIT_CONFIG:
      self._return_response(code=202)
    else:
      self._return_response(code=501)

  def _return_response (self, code, body=None):
    self.send_response(code=code)
    if self.REQUEST_HEADER_MSG_ID in self.headers:
      self.send_header(self.REQUEST_HEADER_MSG_ID,
                       self.headers[self.REQUEST_HEADER_MSG_ID])
    if body:
      self.send_header("Content-Type", "application/xml")
    self.end_headers()
    if body:
      self.wfile.write(body)
      self.wfile.flush()
    return


class CallMock(object):
  def __init__ (self, call, response_path=None, code=200):
    self.call = call
    self.response_path = response_path
    self.code = code

  def __repr__ (self):
    return "CallMock(response: %s, code: %s)" % (self.response_path, self.code)

  def get_response_body (self):
    if not self.response_path:
      return
    with open(self.response_path) as f:
      return f.read()


class DomainMock(object):
  DEFAULT_RESPONSE_CODE = 200

  def __init__ (self, domain):
    self.domain = domain
    self.calls = {}

  def add_call (self, call, **kwargs):
    self.calls[call] = CallMock(call=call, **kwargs)

  def get_call (self, call):
    return self.calls.get(call, None)

  def __repr__ (self):
    return "ResponseMock(domain: %s, calls: %s)" % (self.domain, self.calls)


class DomainOrchestratorAPIMocker(HTTPServer, Thread):
  DEFAULT_PORT = 7000
  FILE_PATH_SEPARATOR = "_"
  RESPONSE_PREFIX = "response"

  def __init__ (self, address="localhost", port=DEFAULT_PORT, daemon=True,
                **kwargs):
    Thread.__init__(self, name="%s(%s:%s)" % (self.__class__.__name__,
                                              address, port))
    HTTPServer.__init__(self, (address, port), DORequestHandler)
    self.daemon = daemon
    self.responses = {}

  def register_responses_from_dir (self, dirname):
    for f in os.listdir(dirname):
      if f.startswith(self.RESPONSE_PREFIX):
        parts = f.split(self.FILE_PATH_SEPARATOR, 2)
        if len(parts) < 3:
          log.error("Wrong filename: %s!")
          continue
        domain, call = parts[1:]
        if domain not in self.responses:
          self.responses[domain] = DomainMock(domain=domain)
        self.responses[domain].add_call(call=call.rsplit('.', 1)[0],
                                        response_path=os.path.join(dirname, f),
                                        code=202)
    log.debug("Registered responses: %s" % pprint.pformat(self.responses))

  def register_responses (self, dirname, responses):
    """

    :param responses: (domain, call, returned)
    :return:
    """
    for resp in responses:
      if len(resp) != 3:
        log.error("Defined response is malformed: %s!" % resp)
      domain, call, ret = resp
      if domain not in self.responses:
        self.responses[domain] = DomainMock(domain=domain)
      if isinstance(ret, int):
        self.responses[domain].add_call(call=call, code=ret)
      else:
        path = os.path.join(dirname, ret)
        self.responses[domain].add_call(call=call, response_path=path, code=202)
    log.debug("Registered responses: %s" % pprint.pformat(self.responses))

  def run (self):
    try:
      self.serve_forever()
    except KeyboardInterrupt:
      raise
    except Exception as e:
      log.error("Got exception in %s: %s" % (self.__class__.__name__, e))
    finally:
      self.server_close()


class DomainMockingSuccessfulTestCase(BasicSuccessfulTestCase):
  def __init__ (self, responses=None, **kwargs):
    super(DomainMockingSuccessfulTestCase, self).__init__(**kwargs)
    self.domain_mocker = DomainOrchestratorAPIMocker(**kwargs)
    dir = self.test_case_info.full_testcase_path
    if responses:
      self.domain_mocker.register_responses(dirname=dir, responses=responses)
    else:
      self.domain_mocker.register_responses_from_dir(dirname=dir)

  def runTest (self):
    self.domain_mocker.start()
    return super(DomainMockingSuccessfulTestCase, self).runTest()


if __name__ == '__main__':
  doam = DomainOrchestratorAPIMocker(daemon=False)
  dm = DomainMock(domain="escape")
  cm1 = CallMock(call="edit-config", code=500)
  cm2 = CallMock(call="get-config", code=200)
  cm2.get_response_body = lambda: "<TEST>testbody<TEST>"
  dm.calls["edit-config"] = cm1
  dm.calls["get-config"] = cm2
  doam.responses["escape"] = dm
  doam.start()
