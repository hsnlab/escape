import os
from unittest.util import strclass

import sys

from testframework.testcases import OutputAssertions

escape_root_dir = os.path.dirname(__file__) + "/../"
sys.path.insert(0, escape_root_dir)

from unittest.case import TestCase
from unittest.suite import TestSuite

import xmlrunner

from testframework.runner import TestReader, CommandRunner, EscapeRunResult


class TestAroo(TestCase, OutputAssertions):
  def __init__ (self, test_case_info, command_runner):
    """

    :type test_case_info: testframework.runner.RunnableTestCaseInfo
    :type command_runner: CommandRunner
    """
    TestCase.__init__(self)
    self.command_runner = command_runner
    self.test_case_info = test_case_info

  def runTest (self):
    command = [self.test_case_info.full_testcase_path() + "/run.sh"]
    proc = self.command_runner.execute(command)
    result = EscapeRunResult(output=proc.before)

    self.assert_successful_installation(result)

  def __str__ (self):
    return "%s (%s)" % (self.test_case_info.testcase_dir_name(), strclass(self.__class__))

  def id (self):
    return super(TestAroo, self).id() + str(self.test_case_info.full_testcase_path())


def main ():
  print(os.getcwd())
  escape_root_dir = os.path.dirname(__file__) + "/../"

  results_xml = "results.xml"
  if (os.path.isfile(results_xml)):
    os.remove(results_xml)

  test_reader = TestReader()

  tests_dir = os.path.dirname(__file__)

  tests = test_reader.read_from(tests_dir)

  command_runner = CommandRunner(cwd=escape_root_dir)

  results = []
  with open(results_xml, 'wb') as output:

    test_runner = xmlrunner.XMLTestRunner(
      output=output,
      verbosity=3,
      buffer=True
    )

    suites = [
      TestSuite(
        [TestAroo(config, command_runner) for config in tests]
      )
    ]

    for suite in suites:
      results.append(test_runner.run(suite))

  suite_successes = map(lambda result: result.wasSuccessful(), results)
  was_success = all(suite_successes)

  for result in results:
    print (result)

  return 0 if was_success else 1


if __name__ == "__main__":
  sys.exit(main())
