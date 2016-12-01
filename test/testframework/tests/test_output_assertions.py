from unittest import TestCase

from testframework.runner import EscapeRunResult
from testframework.testcases import OutputAssertions


class TestOutputAssertions(TestCase):
  assertions = OutputAssertions()

  def test_given_empty_output_log_when_testing_success_expect_failure (self):
    self.assertRaises(
      AssertionError, lambda: self.assertions.assert_successful_installation(EscapeRunResult(""))
    )

  def test_given_a_successful_output_when_testing_successful_installation_no_failure (self):
    self.assertions.assert_successful_installation(
      self._create_result("ABDEF All installation process has been finished with success! FGHI")
    )

  def test_given_log_contains_versions_different_message_expect_failure (self):
    with self.assertRaises(AssertionError) as exception:
      self.assertions.assert_virtualizer_version_matches(
        self._create_result("[something] Version is different!")
      )

    self.assertEqual("Virtualizer version mismatch", exception.exception.message)

  def _create_result (self, message):
    return EscapeRunResult([
      "Random result text",
      "Random Pre Text| " + message,
      "More random text"
    ])
