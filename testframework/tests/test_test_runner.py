import unittest

from testframework.runner import TestRunner, Escape, TestRunnerConfig


class TestRunnerTest(unittest.TestCase):
  def test_given_an_nffg_file_calls_escape_with_correct_path (self):
    escape = MockEscape()
    config = TestRunnerConfig("test_dir")
    runner = TestRunner(escape, config)
    runner.run_testcase("blah.nffg")
    self.assertEqual("test_dir/blah.nffg", escape.got_filepath)


class MockEscape(Escape):

  def run (self, filepath):
    self.got_filepath = filepath
