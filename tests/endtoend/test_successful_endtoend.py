from testframework.testcases import EndToEndTestCase


class SuccessfulEndToEndTest(EndToEndTestCase):
  success_cases = [
    "test-small.nffg",
    "test-escape-mn-req.nffg",
  ]

  def test_given_a_configuration_file_successfully_instantiates_network (self):
    for test_case in self.success_cases:
      self.assert_successful(test_case)

  def assert_successful (self, test_case):
    result = self.runner.run_testcase(test_case)
    self.assert_successful_installation(result)
