#!/usr/bin/env python
# Copyright 2015 Lajos Gerecs, Janos Czentye
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import os
import sys
import unittest

from xmlrunner import XMLTestRunner

from testframework.builder import TestCaseBuilder, TestReader
from testframework.runner import CommandRunner, Tee

CWD = os.path.dirname(os.path.abspath(__file__))
REPORT_FILE = "results.xml"


def main (args):
  """
  Main function which runs the tests and generate the result file.

  :return: result value for the CI environments
  :rtype: int
  """
  # Print header
  print "Start ESCAPE test"
  print "-" * 70
  if args.timeout:
    print "Set kill timeout for test cases: %ds\n" % args.timeout
  # Create overall test suite
  test_suite = create_test_suite(tests_dir=CWD,
                                 show_output=args.show_output,
                                 run_only_tests=args.testcases,
                                 kill_timeout=args.timeout)
  sum_test_cases = test_suite.countTestCases()
  print "Read %d test cases" % sum_test_cases
  if not sum_test_cases:
    # Footer
    print "=" * 70
    print "End ESCAPE test"
    return 0
  # Run test suite in the specific context
  results = []
  if args.verbose:
    output_context_manager = Tee(filename=REPORT_FILE)
  else:
    output_context_manager = open(REPORT_FILE, 'w', buffering=0)
  with output_context_manager as output:
    # Create the Runner class which runs the test cases collected in a
    # TestSuite object
    test_runner = XMLTestRunner(output=output,
                                verbosity=2,
                                failfast=args.failfast)
    try:
      # Run the test cases and collect the results
      results.append(test_runner.run(test_suite))
    except KeyboardInterrupt:
      print "\n\nReceived KeyboardInterrupt! Abort running test suite..."
  # Evaluate results values
  was_success = all(map(lambda res: res.wasSuccessful(), results))
  # Print footer
  print "=" * 70
  print "End ESCAPE test"
  return 0 if was_success else 1


def create_test_suite (tests_dir, show_output=False, run_only_tests=None,
                       kill_timeout=None):
  """
  Create the container TestSuite class based on the config values.

  :param tests_dir: main test dir containes the test cases
  :type tests_dir: str
  :param show_output: print te test oputput on the console
  :type show_output: bool
  :param run_only_tests: only run the given test cases
  :type run_only_tests: list[str]
  :param kill_timeout: kill timeout
  :type kill_timeout: int
  :return: created test suite object
  :rtype: unittest.TestSuite
  """
  test_cases = TestReader(tests_dir=tests_dir).read_from(run_only_tests)
  builder = TestCaseBuilder(cwd=CWD, show_output=show_output,
                            kill_timeout=kill_timeout)
  test_suite = builder.to_suite(test_cases)
  return test_suite


def parse_cmd_args ():
  """
  Parse the commandline arguments.
  """
  parser = argparse.ArgumentParser(description="ESCAPE Test runner",
                                   add_help=True,
                                   prog="run_tests.py")
  parser.add_argument("--failfast", "-f", action="store_true", default=False,
                      help="Stop on first failure")
  parser.add_argument("--show-output", "-o", action="store_true", default=False,
                      help="Show ESCAPE output")
  parser.add_argument("testcases", nargs="*",
                      help="list test case names you want to run. Example: "
                           "./run_tests.py case05 case03 --show-output")
  parser.add_argument("--timeout", "-t", metavar="t", type=int,
                      help="define explicit timeout in sec (default: %ss)" %
                           CommandRunner.KILL_TIMEOUT)
  parser.add_argument("--verbose", "-v", action="store_true", default=False,
                      help="Run in verbose mode and show output")
  return parser.parse_args()


if __name__ == "__main__":
  args = parse_cmd_args()
  result = main(args)
  sys.exit(result)
