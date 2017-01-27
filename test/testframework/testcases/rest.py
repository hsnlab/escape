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
import logging
import os
import sys
import time
import urlparse
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Event

import requests

from testframework.testcases.basic import EscapeTestCase, \
  BasicSuccessfulTestCase

try:
  from escape.nffg_lib.nffg import NFFG
except:
  sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__),
                 "../../../escape/escape/nffg_lib/")))
  from nffg import NFFG

log = logging.getLogger()


class CallbackHandler(BaseHTTPRequestHandler):
  RESULT_PARAM_NAME = "response-code"

  def do_POST (self):
    self.__process_request()
    self.server.callback_event.set()
    self.send_response(200)
    self.send_header('Connection', 'close')
    self.end_headers()

  def log_message (self, format, *args):
    """
    Disable logging of incoming messages.

    :param mformat: message format
    :type mformat: str
    :return: None
    """
    log.debug("%s - - [%s] %s\n" %
              (self.__class__.__name__,
               self.log_date_time_string(),
               format % args))

  def do_GET (self):
    self.do_POST()

  def __process_request (self):
    result_code = self.__get_request_params().get(self.RESULT_PARAM_NAME, None)
    self.server._result = result_code

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


class CallbackManager(HTTPServer, Thread):
  DEFAULT_SERVER_ADDRESS = "localhost"
  DEFAULT_PORT = 9000
  DEFAULT_WAIT_TIMEOUT = 30

  def __init__ (self, address=DEFAULT_SERVER_ADDRESS, port=DEFAULT_PORT,
                wait_timeout=DEFAULT_WAIT_TIMEOUT):
    Thread.__init__(self, name="%s(%s:%s)" % (self.__class__.__name__,
                                              address, port))
    HTTPServer.__init__(self, (address, port), CallbackHandler)
    self.daemon = True
    self.callback_event = Event()
    self.wait_timeout = wait_timeout
    self._result = None

  @property
  def url (self):
    return "http://%s:%s/callback" % self.server_address

  @property
  def last_result (self):
    return self._result

  def run (self):
    try:
      self.serve_forever()
    except KeyboardInterrupt:
      raise
    except Exception as e:
      log.error("Got exception in %s: %s" % (self.__class__.__name__, e))
    finally:
      self.server_close()

  def wait_for_callback (self):
    # Always use a timeout value because without timeout wait() is not
    # interruptable by KeyboardInterrupt
    self.callback_event.wait(timeout=self.wait_timeout)
    self.callback_event.clear()
    return str(self.last_result) == str(httplib.OK)


# noinspection PyAbstractClass
class RESTBasedServiceMixIn(EscapeTestCase):
  """
  Initiate ESCAPE on a separate thread and feed it with the request(s)
  through one of its REST-API.
  """
  REQUEST_DELAY = 3
  REQUEST_TIMEOUT = 1.0
  REQUEST_SUCCESS_CODE = httplib.ACCEPTED
  REQUEST_PREFIX = "request"
  DEFAULT_URL = "http://localhost:8008/escape"
  RPC_REQUEST_NFFG = "sg"
  RPC_REQUEST_VIRTUALIZER = "edit-config"

  def __init__ (self, url=None, delay=None, callback=False, **kwargs):
    super(RESTBasedServiceMixIn, self).__init__(**kwargs)
    self.url = url if url else self.DEFAULT_URL
    self.delay = delay if delay is not None else self.REQUEST_DELAY
    self.callback = callback
    self._suppress_requests_logging()

  @staticmethod
  def _suppress_requests_logging ():
    logging.getLogger("requests").setLevel(logging.WARNING)

  def runTest (self):
    try:
      # Init ESCAPE process in separate thread to send request through its
      # REST API and be able to wait for the result
      thread = Thread(target=self.run_escape)
      thread.daemon = True
      thread.start()
      if self.callback:
        self.send_requests_with_callback()
      else:
        self.send_requests_with_delay()
      thread.join(timeout=self.command_runner.kill_timeout + 1.0)
    except KeyboardInterrupt:
      log.error("\nReceived KeyboardInterrupt! Abort running thread...")
      self.command_runner.kill_process()
      raise
    if thread.isAlive():
      log.error("ESCAPE process is still alive!")
      self.command_runner.kill_process()
      raise RuntimeError("ESCAPE's runner thread has got TIMEOUT!")
    # Verify result here because logging in file is slow compared to the
    # testframework
    self.verify_result()
    # Mark test case as success
    self.success = True

  def send_requests_with_delay (self):
    """
    Send all request started with a prefix in the test case folder to the
    REST API of ESCAPE.

    :return: None
    """
    testcase_dir = self.test_case_info.testcase_dir_name
    reqs = sorted([os.path.join(testcase_dir, file_name)
                   for file_name in os.listdir(testcase_dir)
                   if file_name.startswith(self.REQUEST_PREFIX)])
    for request_file in reqs:
      # Wait for ESCAPE coming up, flushing to file - no callback yet
      time.sleep(self.delay)
      with open(request_file) as f:
        ext = request_file.rsplit('.', 1)[-1]
        ret = self._send_request(data=f.read(), ext=ext)
        self.assertTrue(ret, msg="Got error while sending request: %s"
                                 % request_file)
    # Wait for last orchestration step before stop ESCAPE
    time.sleep(self.delay)
    self.command_runner.stop()

  def send_requests_with_callback (self):
    """
    Send all request started with a prefix in the test case folder to the
    REST API of ESCAPE.

    :return: None
    """
    testcase_dir = self.test_case_info.testcase_dir_name
    reqs = sorted([os.path.join(testcase_dir, file_name)
                   for file_name in os.listdir(testcase_dir)
                   if file_name.startswith(self.REQUEST_PREFIX)])
    cbmanager = CallbackManager(wait_timeout=self.command_runner.kill_timeout)
    cbmanager.start()
    self.command_runner.wait_for_ready()
    cb_url = cbmanager.url if self.callback else None
    for request in reqs:
      with open(request) as f:
        ext = request.rsplit('.', 1)[-1]
        ret = self._send_request(data=f.read(), ext=ext, callback_url=cb_url)
        self.assertTrue(ret,
                        msg="Got error while sending request: %s" % request)
      success = cbmanager.wait_for_callback()
      self.assertTrue(success, msg="Callback returned with error: %s" %
                                   cbmanager.last_result)
    self.command_runner.stop()

  def _send_request (self, data, ext, callback_url=None):
    """
    Send one request read from file to the configured URL.

    :param data: raw request data
    :type data: str
    :param ext: file extension to define request format
    :type ext: str
    :return: request sending was successful or not
    :rtype: bool
    """
    url = self.url
    headers = dict()
    if ext.upper() == 'XML':
      headers['Content-Type'] = "application/xml"
      url = urlparse.urljoin(url, self.RPC_REQUEST_VIRTUALIZER)
    elif ext.upper() == 'NFFG':
      headers['Content-Type'] = "application/json"
      url = urlparse.urljoin(url, self.RPC_REQUEST_NFFG)
    params = {"call-back": callback_url} if callback_url else {}
    try:
      ret = requests.post(url=url, data=data, headers=headers, params=params,
                          timeout=self.REQUEST_TIMEOUT)
      return True if ret.status_code == self.REQUEST_SUCCESS_CODE else False
    except requests.RequestException as e:
      log.error("FAIL\nFailed to send request to ESCAPE: %s" % e.message)
      return False


class RESTBasedSuccessfulTestCase(BasicSuccessfulTestCase,
                                  RESTBasedServiceMixIn):
  def __init__ (self, **kwargs):
    super(RESTBasedSuccessfulTestCase, self).__init__(**kwargs)
