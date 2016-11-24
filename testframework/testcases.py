import os
from unittest.case import TestCase
from unittest.suite import TestSuite
from unittest.util import strclass
import imp

from testframework.runner import EscapeRunResult, RunnableTestCaseInfo


class OutputAssertions:
  ADAPTATION_SUCCESS = "All installation process has been finished with success!"
  VIRTUALIZER_DIFFERENT_VERSION = "Version is different!"

  def assert_successful_installation (self, escape_run_result):
    """

    :type escape_run_result: EscapeRunResult
    """
    if (self.ADAPTATION_SUCCESS not in escape_run_result.log_output):
      raise AssertionError(
        "\n".join(escape_run_result.log_output.split("\n")[-5:]) +
        "Success message is missing from log output."
      )
    else:
      return True

  def assert_virtualizer_version_matches (self, escape_run_result):
    """

    :type escape_run_result: testframework.runner.EscapeRunResult
    """
    if self.VIRTUALIZER_DIFFERENT_VERSION in escape_run_result.log_output:
      raise AssertionError("Virtualizer version mismatch")


class EscapeTestCase(TestCase, OutputAssertions):
  """
  EscapeTestCase is a test case for the case01, case02 structure. It will run ESCAPE
  then place the result into the self.result field.
  You should implement the runTest method to verify the result
  See BasicSuccessfulTestCase
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

    test_py_file = dir + "/" + test_case_config.testcase_dir_name() + ".py"
    if os.path.isfile(test_py_file):
      return self._load_dynamic_test_case(test_case_config, test_py_file)

    return BasicSuccessfulTestCase(test_case_config, self.command_runner)

  def _load_dynamic_test_case (self, test_case_config, test_py_file):
    try:
      module = imp.load_source(test_case_config.testcase_dir_name(), test_py_file)
      class_name = test_case_config.testcase_dir_name().capitalize()
      return getattr(module, class_name)(test_case_config, self.command_runner)
    except AttributeError:
      raise Exception(("No %s class found in %s file." % (class_name, test_py_file)))

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
