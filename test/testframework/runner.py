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
import argparse
import os
import time
from threading import Timer
from unittest.case import TestCase

import pexpect


class EscapeRunResult():
  def __init__ (self, output=""):
    self.log_output = output


class CommandRunner(object):
  KILL_TIMEOUT = 30

  def __init__ (self, cwd, kill_timeout=KILL_TIMEOUT, on_kill=None,
                output_stream=None):
    self.output_stream = output_stream
    self._cwd = cwd
    self.on_kill = on_kill
    self.kill_timeout = kill_timeout
    self.kill_timer = None
    self.start_time = None
    self.proc = None

  def kill_process (self, *args, **kwargs):
    self.proc.sendcontrol('c')
    self.kill_timer.cancel()
    if self.on_kill:
      self.on_kill(self.proc)
    else:
      self.__default_on_kill_handler(self.proc)

  def __default_on_kill_handler (self, process):
    """

    :param process:
    :return:
    """
    print "\nCommand: [%s] was killed after %.1f seconds." \
          % (process.command, time.time() - self.start_time)

  def execute (self, command):
    self.proc = pexpect.spawn(command[0],
                              args=command[1:],
                              timeout=120,
                              cwd=self._cwd,
                              logfile=self.output_stream)

    self.kill_timer = Timer(self.kill_timeout, self.kill_process, [self.proc])
    self.kill_timer.start()
    self.start_time = time.time()
    self.proc.expect(pexpect.EOF)
    self.kill_timer.cancel()
    if "No such file or directory" in self.proc.before:
      raise Exception("CommandRunner Error:" + self.proc.before)
    return self.proc


class TestReader(object):
  TEST_DIR_PREFIX = "case"

  def read_from (self, test_cases_dir):
    """

    :rtype: list[RunnableTestCaseInfo]
    """
    dirs = sorted(os.listdir(test_cases_dir))
    cases = []
    for case_dir in dirs:
      if case_dir.startswith(self.TEST_DIR_PREFIX):
        cases.append(RunnableTestCaseInfo(testcase_dir_name=case_dir,
                                          full_testcase_path="%s/%s" % (
                                            test_cases_dir, case_dir)))
    return cases


class RunnableTestCaseInfo(object):
  def __init__ (self, testcase_dir_name, full_testcase_path):
    self.__full_testcase_path = full_testcase_path
    self.__testcase_dir_name = testcase_dir_name

  def testcase_dir_name (self):
    # type: () -> str
    return self.__testcase_dir_name

  def full_testcase_path (self):
    return self.__full_testcase_path

  def __repr__ (self):
    return "RunnableTestCase [%s]" % self.__testcase_dir_name


default_cmd_opts = {"show_output": False,
                    "testcases": []}


def parse_cmd_args (argv):
  parser = get_cmd_arg_parser()
  args = parser.parse_args(argv)
  kwargs = args._get_kwargs()
  return dict(default_cmd_opts.items() + kwargs)


def get_cmd_arg_parser ():
  parser = argparse.ArgumentParser(description="ESCAPE Test runner",
                                   add_help=True,
                                   prog="run_tests.py")
  parser.add_argument("--show-output", "-o", action="store_true",
                      help="Show ESCAPE output")
  parser.add_argument("testcases", nargs="*",
                      help="list test case names you want to run. Example: "
                           "./run_tests.py case05 case03 --show-output")
  return parser


class SimpleTestCase(TestCase):
  def __init__ (self, test_case_config, command_runner):
    """

    :type command_runner: CommandRunner
    :type test_case_config: RunnableTestCaseInfo
    """
    super(SimpleTestCase, self).__init__()
    self.command_runner = command_runner
    self.test_case_config = test_case_config

  def runTest (self):
    self.result = self.command_runner.execute("%s/run.sh" %
                                              self.test_case_config)
