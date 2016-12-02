# Copyright 2015 Lajos Gerecs
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
import os
from threading import Timer

import pexpect


class EscapeRunResult():
  def __init__ (self, output=""):
    self.log_output = output


class CommandRunner(object):
  KILL_TIMEOUT = 20

  def __init__ (self, cwd, kill_timeout=KILL_TIMEOUT, on_kill=None,
                output_stream=None):
    self.output_stream = output_stream
    self._cwd = cwd
    self.on_kill_hook = on_kill
    self.kill_timeout = kill_timeout
    self.kill_timer = None
    self.last_process = None

  def kill_process (self, *args, **kwargs):
    self.last_process.sendcontrol('c')
    self.kill_timer.cancel()
    if self.on_kill_hook:
      self.on_kill_hook()

  def execute (self, command):
    self.last_process = pexpect.spawn(command[0],
                                      args=command[1:],
                                      timeout=120,
                                      cwd=self._cwd,
                                      logfile=self.output_stream)

    self.kill_timer = Timer(self.kill_timeout, self.kill_process,
                            [self.last_process])
    self.kill_timer.start()
    self.last_process.expect(pexpect.EOF)
    self.kill_timer.cancel()
    if "No such file or directory" in self.last_process.before:
      raise Exception("CommandRunner Error: %s" % self.last_process.before)
    return self.last_process


class TestReader(object):
  TEST_DIR_PREFIX = "case"

  def __init__ (self, tests_dir):
    self.tests_dir = tests_dir

  def read_from (self, case_dirs=None):
    """

    :rtype: list[RunnableTestCaseInfo]
    """
    if not case_dirs:
      case_dirs = sorted(os.listdir(self.tests_dir))
    cases = [RunnableTestCaseInfo(full_path=os.path.join(self.tests_dir,
                                                         case_dir))
             for case_dir in case_dirs if
             case_dir.startswith(self.TEST_DIR_PREFIX)]
    return cases


class RunnableTestCaseInfo(object):
  def __init__ (self, full_path):
    # Removing trailing slash
    self.__full_path = os.path.normpath(full_path)

  @property
  def testcase_dir_name (self):
    return os.path.basename(self.__full_path)

  @property
  def full_testcase_path (self):
    return self.__full_path

  def __repr__ (self):
    return "RunnableTestCase [%s]" % self.testcase_dir_name
