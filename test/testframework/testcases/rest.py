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

  def __init__ (self, url=None, **kwargs):
    super(RESTBasedServiceMixIn, self).__init__(**kwargs)
    self.url = url if url else self.DEFAULT_URL
    self.thread = None
    self._suppress_requests_logging()

  @staticmethod
  def _suppress_requests_logging ():
    logging.getLogger("requests").setLevel(logging.WARNING)

  def runTest (self):
    try:
      self.thread = Thread(target=self.run_escape)
      self.thread.setDaemon(True)
      self.thread.start()

      time.sleep(self.REQUEST_DELAY)

      self.send_requests()

      self.thread.join(timeout=self.command_runner.kill_timeout + 1)
    except KeyboardInterrupt:
      log.error("Received KeyboardInterrupt! Abort running thread...")
      self.command_runner.kill_process()
      raise

    if self.thread.isAlive():
      self.command_runner.kill_process()
      raise RuntimeError("ESCAPE's runner thread has got TIMEOUT!")

    self.verify_result()
    # TODO - Move validation into loop of send requests
    # TODO - handle buffered file logging and do not crash if escape-log is
    # empty
    # Mark test case as success
    self.success = True

  def send_requests (self):
    testcase_dir = self.test_case_info.testcase_dir_name
    reqs = sorted([os.path.join(testcase_dir, file_name)
                   for file_name in os.listdir(testcase_dir)
                   if file_name.startswith(self.REQUEST_PREFIX)])
    for request_file in reqs:
      with open(request_file, 'r') as f:
        ext = request_file.rsplit('.', 1)[-1]
        ret = self._send_request(data=f.read(), ext=ext)
        self.assertTrue(ret, msg="Request: %s - ESCAPE responded with ERROR "
                                 "status!" % request_file)

  def _send_request (self, data, ext):
    headers = dict()
    if ext.upper() == 'XML':
      headers['Content-Type'] = "application/xml"
    elif ext.upper() == 'NFFG':
      headers['Content-Type'] = "application/json"
    ret = requests.post(url=self.url, data=data, headers=headers,
                        timeout=self.REQUEST_TIMEOUT)
    if ret.status_code == self.REQUEST_SUCCESS_CODE:
      return True
    else:
      return False


class RESTBasedSuccessfulTestCase(BasicSuccessfulTestCase,
                                  RESTBasedServiceMixIn):
  def __init__ (self, **kwargs):
    super(RESTBasedSuccessfulTestCase, self).__init__(**kwargs)
