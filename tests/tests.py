from __future__ import print_function
from testframework import runner as testrunner


def main ():
  escape = testrunner.CommandLineEscape()
  runner_config = testrunner.TestRunnerConfig(
    test_case_directory="tests/endtoend/testcases"
  )
  runner = testrunner.TestRunner(escape, runner_config)
  runner.run_testcase("test-1-success.nffg")
  pass

if __name__ == "__main__":
  main()
