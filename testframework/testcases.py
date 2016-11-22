import os
from unittest import TestCase
from unittest.case import TestCase
from unittest.suite import TestSuite
from unittest.util import strclass

from testframework.runner import CommandLineEscape, TestRunnerConfig, TestRunner, EscapeRunResult, RunnableTestCaseInfo


class OutputAssertions:
  ADAPTATION_SUCCESS = "All installation process has been finished with success!"
  VIRTUALIZER_DIFFERENT_VERSION = "Version is different!"

  def assert_successful_installation (self, escape_run_result):
    """

    :type escape_run_result: EscapeRunResult
    """
    if (self.ADAPTATION_SUCCESS not in escape_run_result.log_output):
      raise AssertionError("Unsucessful run.")
    else:
      return True

  def assert_virtualizer_version_matches (self, escape_run_result):
    """

    :type escape_run_result: testframework.runner.EscapeRunResult
    """
    if self.VIRTUALIZER_DIFFERENT_VERSION in escape_run_result.log_output:
      raise AssertionError("Virtualizer version mismatch")


class EndToEndTestCase(TestCase, OutputAssertions):
  escape = CommandLineEscape()
  runner_config = TestRunnerConfig(
    test_case_directory="tests/endtoend/testcases"
  )
  runner = TestRunner(escape, runner_config)


class EscapeTestCase(TestCase, OutputAssertions):
  """
  EscapeTestCase is a test case for the case01, case02 structure. It will run ESCAPE
  then place the result into the self.result field.
  """

  def __init__ (self, test_case_info, command_runner):
    """
    :type test_case_info: testframework.runner.RunnableTestCaseInfo
    :type command_runner: CommandRunner
    """
    TestCase.__init__(self)
    self.command_runner = command_runner
    self.test_case_info = test_case_info

  def run_escape (self):
    command = [self.test_case_info.full_testcase_path() + "/run.sh"]
    proc = self.command_runner.execute(command)
    self.result = EscapeRunResult(output=proc.before)

  def setUp (self):
    super(EscapeTestCase, self).setUp()
    self.run_escape()

  def __str__ (self):
    return "%s (%s)" % (self.test_case_info.testcase_dir_name(), strclass(self.__class__))

  def id (self):
    return super(EscapeTestCase, self).id() + str(self.test_case_info.full_testcase_path())


class TestCaseBuilder():
  def __init__ (self, command_runner):
    """

    :type command_runner: testframework.runner.CommandRunner
    """
    self.command_runner = command_runner

  def build_from_config (self, test_case_config):
    """

    :type test_case_config: testframework.runner.RunnableTestCaseInfo
    :rtype: TestCase
    """
    dir = test_case_config.full_testcase_path()
    if not os.path.isfile(dir + "/run.sh"):
      raise Exception("No run.sh in directory " + dir)

    return BasicSuccessfulTestCase(test_case_config, self.command_runner)

  def to_suite (self, tests):
    """

    :type tests: list[RunnableTestCaseInfo]
    :rtype: TestSuite
    """
    suite = [self.build_from_config(config) for config in tests]
    test_suite = TestSuite(suite)
    return test_suite


class BasicSuccessfulTestCase(EscapeTestCase):
  def runTest (self):
    self.assert_successful_installation(self.result)
