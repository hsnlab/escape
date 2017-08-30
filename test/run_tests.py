#!/usr/bin/env python
# Copyright 2017 Lajos Gerecs, Janos Czentye
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
import logging
import os
import sys
import time
import unittest
from datetime import timedelta

from xmlrunner import XMLTestRunner

from testframework.builder import TestSuitBuilder, TestCaseReader
from testframework.runner import CommandRunner, Tee

logging.basicConfig(format="%(message)s",
                    level=logging.INFO)
log = logging.getLogger()

CWD = os.path.dirname(os.path.abspath(__file__))
REPORT_FILE = "results.xml"


def main (args):
  """
  Main function which runs the tests and generate the result file.

  :return: result value for the CI environments
  :rtype: int
  """
  # Print header
  tstart = time.time()
  log.info("Start ESCAPE tests")
  log.info("-" * 70)
  if args.timeout:
    log.info("Set kill timeout for test cases: %ds\n" % args.timeout)
  # Create overall test suite
  test_suite = create_test_suite(tests_dir=CWD,
                                 show_output=args.show_output,
                                 run_only_tests=args.testcases,
                                 kill_timeout=args.timeout,
                                 standalone=args.standalone)
  sum_test_cases = test_suite.countTestCases()
  log.info("-" * 70)
  log.info("Read %d test cases" % sum_test_cases)
  # Run test suite in the specific context
  results = []
  if args.verbose:
    output_context_manager = Tee(filename=REPORT_FILE)
  else:
    output_context_manager = open(REPORT_FILE, 'w', buffering=0)
  with output_context_manager as output:
    # Create the Runner class which runs the test cases collected in a
    # TestSuite object
    if args.failfast:
      log.info("Using failfast mode!")
    test_runner = XMLTestRunner(output=output,
                                verbosity=2,
                                failfast=args.failfast)
    try:
      # Run the test cases and collect the results
      if sum_test_cases:
        results.append(test_runner.run(test_suite))
    except KeyboardInterrupt:
      log.warning("\nReceived KeyboardInterrupt! "
                  "Abort running main test suite...")
  # Evaluate results values
  was_success = all(map(lambda res: res.wasSuccessful(), results))
  # Print footer
  log.info("-" * 70)
  delta = time.time() - tstart
  log.info("Total elapsed time: %s sec" % timedelta(seconds=delta))
  log.info("-" * 70)
  log.info("End ESCAPE tests")
  return 0 if was_success else 1


def create_test_suite (tests_dir, show_output=False, run_only_tests=None,
                       kill_timeout=None, standalone=None):
  """
  Create the container TestSuite class based on the config values.

  :param tests_dir: main test dir contains the test cases
  :type tests_dir: str
  :param show_output: print the test output on the console
  :type show_output: int
  :param run_only_tests: only run the given test cases
  :type run_only_tests: list[str]
  :param kill_timeout: kill timeout
  :type kill_timeout: int
  :return: created test suite object
  :rtype: unittest.TestSuite
  """
  log.info("Loading test cases...\n")
  reader = TestCaseReader(tests_dir=tests_dir)
  builder = TestSuitBuilder(cwd=CWD,
                            show_output=show_output,
                            kill_timeout=kill_timeout,
                            standalone=standalone)
  tests = reader.read_from(run_only_tests)
  if standalone:
    tests = tests[0:1]
    log.info("Detected standalone mode! "
             "Run only the first testcase: %s" % tests)
  test_suite = builder.to_suite(tests=tests)
  return test_suite


def parse_cmd_args ():
  """
  Parse the commandline arguments.
  """
  parser = argparse.ArgumentParser(description="ESCAPE Test runner",
                                   add_help=True,
                                   prog="run_tests.py")
  parser.add_argument("-f", "--failfast", action="store_true", default=False,
                      help="stop on first failure")
  parser.add_argument("-o", "--show-output", action="count", default=0,
                      help="show ESCAPE output (can use multiple "
                           "times for more verbose logging)")
  parser.add_argument("testcases", nargs="*",
                      help="list test case names you want to run. Example: "
                           "./run_tests.py case05 case03 --show-output")
  parser.add_argument("-t", "--timeout", metavar="t", type=int,
                      help="define explicit timeout in sec (default: %ss)" %
                           CommandRunner.KILL_TIMEOUT)
  parser.add_argument("-s", "--standalone", action="store_true", default=False,
                      help="run standalone mode: no timeout, no quitting")
  parser.add_argument("-v", "--verbose", action="store_true", default=False,
                      help="run testframework in verbose mode and show output")
  return parser.parse_args()


if __name__ == "__main__":
  args = parse_cmd_args()
  if args.verbose:
    log.setLevel(logging.DEBUG)
  result = main(args)
  sys.exit(result)
