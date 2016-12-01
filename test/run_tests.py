#!/usr/bin/env python
# Copyright 2015 Lajos Gerecs
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

import os
import sys

from xmlrunner import XMLTestRunner

from testframework.runner import TestReader, CommandRunner, parse_cmd_args
from testframework.testcases import TestCaseBuilder

CWD = os.path.dirname(os.path.abspath(__file__))
REPORT_FILE = "results.xml"


def main (argv):
  print "Start ESCAPE test"
  cmd_args = parse_cmd_args(argv)
  test_suite = create_test_suite(tests_dir=CWD,
                                 show_output=cmd_args["show_output"],
                                 run_only_tests=cmd_args["testcases"])
  print "=" * 70
  print "Read %d test cases" % test_suite.countTestCases()
  results = []
  with open(REPORT_FILE, 'w') as output:
    test_runner = XMLTestRunner(output=output, verbosity=2)
    try:
      results.append(test_runner.run(test_suite))
    except KeyboardInterrupt:
      print "\n\nReceived KeyboardInterrupt from user! Abort test suite..."
  was_success = all(map(lambda result: result.wasSuccessful(), results))
  print "=" * 70
  print "End ESCAPE test"
  return 0 if was_success else 1


def create_test_suite (tests_dir, show_output=False, run_only_tests=None):
  test_configs = TestReader().read_from(tests_dir)
  if run_only_tests:
    test_configs = [config for config in test_configs if
                    config.testcase_dir_name in run_only_tests]
  clear_test_environment(test_configs)
  command_runner = CommandRunner(cwd=CWD,
                                 output_stream=sys.stdout if show_output else
                                 None)
  test_suite = TestCaseBuilder(command_runner).to_suite(test_configs)
  return test_suite


def clear_test_environment (config):
  print "=" * 70
  print "Clear test environment:"
  for case_info in config:
    log_file = os.path.join(CWD, case_info.testcase_dir_name, "escape.log")
    if os.path.exists(log_file):
      os.remove(log_file)
      print "  DEL", log_file


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
