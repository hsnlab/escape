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

from xmlrunner import XMLTestRunner

from testframework.runner import TestReader, KILL_TIMEOUT
from testframework.testcases import TestCaseBuilder

CWD = os.path.dirname(os.path.abspath(__file__))
REPORT_FILE = "results.xml"


def main (args):
  print "Start ESCAPE test"
  test_suite = create_test_suite(tests_dir=CWD,
                                 show_output=args.show_output,
                                 run_only_tests=args.testcases,
                                 kill_timeout=args.timeout)
  print "-" * 70
  if args.timeout:
    print "Set kill timeout for test cases: %ds\n" % args.timeout
  print "Read %d test cases" % test_suite.countTestCases()
  results = []
  with open(REPORT_FILE, 'w') as output:
    test_runner = XMLTestRunner(output=output,
                                verbosity=2,
                                failfast=args.failfast)
    try:
      results.append(test_runner.run(test_suite))
    except KeyboardInterrupt:
      print "\n\nReceived KeyboardInterrupt from user! " \
            "Abort running test suite..."
  was_success = all(map(lambda result: result.wasSuccessful(), results))
  print "=" * 70
  print "End ESCAPE test"
  return 0 if was_success else 1


def create_test_suite (tests_dir, show_output=False, run_only_tests=None,
                       kill_timeout=None):
  test_cases = TestReader(tests_dir=tests_dir).read_from(run_only_tests)
  builder = TestCaseBuilder(cwd=CWD, show_output=show_output,
                            kill_timeout=kill_timeout)
  test_suite = builder.to_suite(test_cases)
  return test_suite


def parse_cmd_args ():
  parser = argparse.ArgumentParser(description="ESCAPE Test runner",
                                   add_help=True,
                                   prog="run_tests.py")
  parser.add_argument("--show-output", "-o", action="store_true", default=False,
                      help="Show ESCAPE output")
  parser.add_argument("--failfast", "-f", action="store_true", default=False,
                      help="Stop on first failure")
  parser.add_argument("testcases", nargs="*",
                      help="list test case names you want to run. Example: "
                           "./run_tests.py case05 case03 --show-output")
  parser.add_argument("--timeout", "-t", metavar="t", type=int,
                      help="define explicit timeout in sec (default: %ss)" %
                           KILL_TIMEOUT)
  return parser.parse_args()


if __name__ == "__main__":
  args = parse_cmd_args()
  result = main(args)
  sys.exit(result)
