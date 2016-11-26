from unittest import TestCase

from testframework.runner import EscapeRunResult
from testframework.testcases import WarningChecker


class TestWarningChecker(TestCase):
  warning_checker = WarningChecker()

  def test_given_a_response_when_filtering_warns_returns_all_warnings (self):
    warnings = self.warning_checker._filter_warnings([
      "Log line 1",
      self.acceptable_warning(),
      "Log line 2"
    ])
    self.assertEqual([self.acceptable_warning()], warnings)

  def test_given_a_not_acceptable_warning_throws_exception (self):
    warning = "|WARNING|tests|2015|This is a warning I have not seen before"
    with self.assertRaises(AssertionError) as raised:
      self.warning_checker.assert_no_unusual_warnings([warning])

    self.assertEqual("Got unusual warning: " + warning, raised.exception.message)

  def test_given_an_acceptable_warning_doesnt_throw_exception(self):
    lines = [ self.acceptable_warning() ]
    self.warning_checker.assert_no_unusual_warnings(lines)

  def acceptable_warning (self):
    return ("|WARNING|service|2016-11-26 19:01:07,198| Mapping algorithm in Layer: service is disabled! "
            "Skip mapping step and forward service request to lower layer...")
