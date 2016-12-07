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
import os
import sys
from collections import Iterable
from threading import Timer

import pexpect

KILL_TIMEOUT = 10


class Tee(object):
  """
  Inspired by the bash command: tee

  tee - read from standard input and write to standard output and files
  """

  def __init__ (self, filename):
    super(Tee, self).__init__()
    self.file = open(filename, mode="w", buffering=0)
    self.stdout = sys.stdout
    sys.stdout = self

  def __del__ (self):
    sys.stdout = self.stdout
    self.file.close()

  def write (self, data):
    self.file.write(data)
    self.stdout.write(data)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.__del__()


class EscapeRunResult():
  def __init__ (self, output=None, exception=None):
    self.log_output = output
    self.exception = exception
    self.success = False if exception else None

  def was_error (self):
    return self.success

  def __iter__ (self):
    return iter(self.log_output)


class CommandRunner(object):
  def __init__ (self, cmd, cwd=None, kill_timeout=None, on_kill=None,
                output_stream=None):
    self._command = self.__evaluate_cmd(cmd)
    self._cwd = cwd if cwd else os.path.dirname(__file__)
    self.kill_timeout = kill_timeout if kill_timeout else KILL_TIMEOUT
    self.on_kill_hook = on_kill
    self.output_stream = output_stream
    self.__process = None
    self.__kill_timer = None
    self.__killed = False

  @staticmethod
  def __evaluate_cmd (cmd):
    if isinstance(cmd, basestring):
      return cmd.split(' ')
    elif isinstance(cmd, Iterable):
      return list(cmd)
    else:
      return None

  @property
  def is_killed (self):
    return self.__killed

  def kill_process (self, *args, **kwargs):
    self.__process.sendcontrol('c')
    self.__kill_timer.cancel()
    self.__killed = True
    if self.on_kill_hook:
      self.on_kill_hook()

  def get_process_output_stream (self):
    return self.__process.before if self.__process.before else ""

  def execute (self):
    self.__process = pexpect.spawn(self._command[0],
                                   args=self._command[1:],
                                   timeout=120,
                                   cwd=self._cwd,
                                   logfile=self.output_stream)

    self.__kill_timer = Timer(self.kill_timeout, self.kill_process,
                              [self.__process])
    self.__kill_timer.start()
    self.__process.expect(pexpect.EOF)
    self.__kill_timer.cancel()
    if "No such file or directory" in self.__process.before:
      raise Exception("CommandRunner Error: %s" % self.__process.before)
    return self

  def cleanup (self):
    self.__process = None
    self.__kill_timer = None


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
    cases = [RunnableTestCaseInfo(case_path=os.path.join(self.tests_dir,
                                                         case_dir))
             for case_dir in case_dirs if
             case_dir.startswith(self.TEST_DIR_PREFIX)]
    return cases


class RunnableTestCaseInfo(object):
  def __init__ (self, case_path):
    # Removing trailing slash
    self.__case_path = os.path.normpath(case_path)

  @property
  def testcase_dir_name (self):
    return os.path.basename(self.__case_path)

  @property
  def full_testcase_path (self):
    return self.__case_path

  def __repr__ (self):
    return "RunnableTestCase [%s]" % self.testcase_dir_name
