from unittest.case import TestCase

from testframework.runner import CommandLineEscape, TestRunnerConfig, TestRunner


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
