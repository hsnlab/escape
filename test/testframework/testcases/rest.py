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
import sys
import time
from threading import Thread

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


# noinspection PyAbstractClass
class RESTBasedServiceMixIn(EscapeTestCase):
  """
  Initiate ESCAPE on a separate thread and feed it with the request(s)
  through one of its REST-API.
  """
  REQUEST_DELAY = 3
  REQUEST_TIMEOUT = 1
  REQUEST_SUCCESS_CODE = 202
  REQUEST_PREFIX = "request"
  DEFAULT_URL = "http://localhost:8008/escape"
  RPC_REQUEST_NFFG = "sg"
  RPC_REQUEST_VIRTUALIZER = "edit-config"

  def __init__ (self, url=None, delay=None, **kwargs):
    super(RESTBasedServiceMixIn, self).__init__(**kwargs)
    self.url = url if url else self.DEFAULT_URL
    self.delay = delay if delay is not None else self.REQUEST_DELAY
    self.thread = None
    self._suppress_requests_logging()

  @staticmethod
  def _suppress_requests_logging ():
    logging.getLogger("requests").setLevel(logging.WARNING)

  def runTest (self):
    try:
      # Init ESCAPE process in separate thread to send request through its
      # REST API and be able to wait for the result
      self.thread = Thread(target=self.run_escape)
      self.thread.setDaemon(True)
      self.thread.start()
      self.send_requests()
      self.thread.join(timeout=self.command_runner.kill_timeout + 1)
    except KeyboardInterrupt:
      log.error("\nReceived KeyboardInterrupt! Abort running thread...")
      self.command_runner.kill_process()
      raise
    if self.thread.isAlive():
      log.error("ESCAPE process is still alive!")
      self.command_runner.kill_process()
      raise RuntimeError("ESCAPE's runner thread has got TIMEOUT!")
    # Verify result here because logging in file is slow compared to the
    # testframework
    self.verify_result()
    # TODO - Move validation into loop of send requests
    # TODO - handle buffered file logging and do not crash if escape-log is
    # empty
    # Mark test case as success
    self.success = True

  def send_requests (self):
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

  def _send_request (self, data, ext):
    """
    Send one request read from file to the configured URL.

    :param data: raw request data
    :type data: str
    :param ext: file extension to define request format
    :type ext: str
    :return: request sending was successful or not
    :rtype: bool
    """
    headers = dict()
    if ext.upper() == 'XML':
      headers['Content-Type'] = "application/xml"
    elif ext.upper() == 'NFFG':
      headers['Content-Type'] = "application/json"
    try:
      ret = requests.post(url=self.url, data=data, headers=headers,
                          timeout=self.REQUEST_TIMEOUT)
      return True if ret.status_code == self.REQUEST_SUCCESS_CODE else False
    except requests.RequestException as e:
      log.error("FAIL\nFailed to send request to ESCAPE: %s" % e.message)
      return False


class RESTBasedSuccessfulTestCase(BasicSuccessfulTestCase,
                                  RESTBasedServiceMixIn):
  def __init__ (self, **kwargs):
    super(RESTBasedSuccessfulTestCase, self).__init__(**kwargs)
