from unittest import TestCase

from testframework.runner import default_cmd_opts, parse_cmd_opts


class TestParseCmdOpts(TestCase):
  def test_given_no_opts_returns_default (self):
    self.assertEqual(default_cmd_opts, parse_cmd_opts([]))

  def test_given_show_output_then_show_output_option_is_true (self):
    self.assertTrue(parse_cmd_opts(["--show-output"])["show_output"])
    self.assertTrue(parse_cmd_opts(["-o"])["show_output"])
