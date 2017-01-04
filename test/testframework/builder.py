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
from unittest.suite import TestSuite

from runner import RunnableTestCaseInfo, CommandRunner
from testframework.testcases.basic import BasicSuccessfulTestCase

log = logging.getLogger()


class TestCaseReader(object):
  """
  Parse the test directory and return the assembled test case config objects
  for the individual test cases.
  """
  TEST_DIR_PREFIX = "case"

  def __init__ (self, tests_dir):
    """
    :type tests_dir: str
    """
    self.tests_dir = tests_dir

  def read_from (self, case_dirs=None):
    """
    Load the test case info from the test directory.

    :param case_dirs: filter the test cases based on the given case list
    :type case_dirs: list[str]
    :return: created test case config objects
    :rtype: list[RunnableTestCaseInfo]
    """
    if not case_dirs:
      case_dirs = sorted(os.listdir(self.tests_dir))
    cases = [RunnableTestCaseInfo(case_path=os.path.join(self.tests_dir,
                                                         case_dir))
             for case_dir in case_dirs if
             case_dir.startswith(self.TEST_DIR_PREFIX)]
    return cases


class TestSuitBuilder(object):
  """
  Builder class for creating the overall TestSuite object.
  """
  # TODO - check the possibility to refactor to unittest.TestLoader

  DEFAULT_TESTCASE_CLASS = BasicSuccessfulTestCase
  CONFIG_CONTAINER_NAME = "test"

  def __init__ (self, cwd, show_output=False, kill_timeout=None):
    self.cwd = cwd
    self.show_output = show_output
    self.kill_timeout = kill_timeout

  def _create_command_runner (self, case_info):
    """
    Create the specific runner object which runs and optionally kills ESCAPE.

    :type case_info: RunnableTestCaseInfo
    :rtype: CommandRunner
    """
    return CommandRunner(cwd=self.cwd,
                         cmd=case_info.test_command,
                         kill_timeout=self.kill_timeout,
                         output_stream=sys.stdout if self.show_output else None)

  def build_from_config (self, case_info):
    """
    Build a Testcase object based on the test config file and the given test
    case info object.

    :param case_info: config object contains the test case data
    :type case_info: RunnableTestCaseInfo
    :return: instantiated specific TestCase class
    :rtype: EscapeTestCase
    """
    # Check running script
    if not os.path.exists(case_info.test_command):
      raise Exception("Running script: %s for testcase: %s was not found"
                      % (case_info.test_command, case_info.full_testcase_path))
    # Create CommandRunner for test case
    cmd_runner = self._create_command_runner(case_info=case_info)
    # Create TestCase class
    if os.path.exists(case_info.config_file_name):
      TESTCASE_CLASS, test_args = case_info.load_test_case_class()
      if TESTCASE_CLASS:
        # log.debug(
        #   "Loaded class: %s, arguments: %s" % (TESTCASE_CLASS, test_args))
        return TESTCASE_CLASS(test_case_info=case_info,
                              command_runner=cmd_runner,
                              **test_args)
    return self.DEFAULT_TESTCASE_CLASS(test_case_info=case_info,
                                       command_runner=cmd_runner)

  def to_suite (self, tests):
    """
    Creates the container TestSuite object and populate with the TestCase
    objects based on the given test config objects.

    :param tests: test case config objects
    :type tests: list[RunnableTestCaseInfo]
    :return: overall TestSuite object
    :rtype: TestSuite
    """
    test_cases = list()
    for case_info in tests:
      try:
        test_cases.append(self.build_from_config(case_info=case_info))
      except Exception as e:
        log.error("Testcase loading failed: %s" % e.message)
    return TestSuite(test_cases)

