from unittest.case import TestCase

from testframework.runner import CommandLineEscape, TestRunnerConfig, TestRunner


class OutputAssertions:
  ADAPTATION_SUCCESS = "All installation process has been finished with success!"

  def assert_successful_installation (self, escape_run_result):
    """

    :type escape_run_result: EscapeRunResult
    """
    if (self.ADAPTATION_SUCCESS not in escape_run_result.stderr):
      raise AssertionError()
    else:
      return True


class EndToEndTestCase(TestCase, OutputAssertions):
  escape = CommandLineEscape()
  runner_config = TestRunnerConfig(
    test_case_directory="tests/endtoend/testcases"
  )
  runner = TestRunner(escape, runner_config)

