import os
from unittest import TestCase

from testframework.runner import RunnableTestCaseInfo
from testframework.testcases import TestCaseBuilder, BasicSuccessfulTestCase


class CommandRunnerDummy:
  pass


class TestTestCaseBuilder(TestCase):
  test_cases_dir = os.path.dirname(__file__) + "/testresources/testreader/"
  command_runner = CommandRunnerDummy()
  builder = TestCaseBuilder(command_runner)

  def test_given_a_path_when_directory_has_no_run_file_then_throws_exception (self):
    dir = self.test_cases_dir + "empty"

    with self.assertRaises(Exception) as raised:
      self.read_case_from_dir(dir)

  def test_given_a_path_when_dir_has_run_sh_file_returns_basic_successful_test_case (self):
    dir = self.test_cases_dir + "nonempty/case01"
    test_case = self.read_case_from_dir(dir)
    self.assertIsInstance(test_case, BasicSuccessfulTestCase)
    self.assertEqual(self.command_runner, test_case.command_runner)

  def read_case_from_dir (self, dir):
    return self.builder.build_from_config(RunnableTestCaseInfo(os.path.basename(dir), dir))
