from unittest import TestCase

from testframework.runner import EscapeRunResult
from testframework.testcases import OutputAssertions


class TestOutputAssertions(TestCase):
  assertions = OutputAssertions()

  def test_given_empty_stderr_when_testing_success_expect_failure (self):
    self.assertRaises(
      AssertionError, lambda: self.assertions.assert_successful_installation(EscapeRunResult(""))
    )

  def test_given_a_successful_stderr_when_testing_successful_installation_no_failure (self):
    self.assertions.assert_successful_installation(
      EscapeRunResult(" Blah Blah Blah "
                      "ABDEF All installation process has been finished with success! FGHI"
                      "Ehh")
    )
