from unittest import TestCase

from testframework.runner import default_cmd_opts, parse_cmd_opts


class TestParseCmdOpts(TestCase):
  def test_given_no_opts_returns_default (self):
    self.assertEqual(default_cmd_opts, parse_cmd_opts([]))

  def test_given_show_output_then_show_output_option_is_true (self):
    self.assertTrue(parse_cmd_opts(["--show-output"])["show_output"])
    self.assertTrue(parse_cmd_opts(["-o"])["show_output"])

  def test_given_a_test_name_run_only_is_test_name (self):
    self.assertEqual(["case005"], parse_cmd_opts(["case005"])["testcases"])
    self.assertTrue(parse_cmd_opts(["--show-output", "case005"])["show_output"])
