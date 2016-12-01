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
from __future__ import print_function

import os
import sys

import xmlrunner

from testframework.runner import TestReader, CommandRunner, parse_cmd_args
from testframework.testcases import TestCaseBuilder

CWD = os.path.dirname(__file__)


def main (argv):
  results_xml = "results.xml"
  # delete_file(results_xml)
  cmd_args = parse_cmd_args(argv)

  test_suite = create_test_suite(tests_dir=CWD,
                                 show_output=cmd_args["show_output"],
                                 run_only_tests=cmd_args["testcases"])

  print("Found %d testcases" % test_suite.countTestCases())

  suites = [test_suite]

  results = []
  with open(results_xml, 'w') as output:
    test_runner = xmlrunner.XMLTestRunner(output=output, verbosity=2)
    for suite in suites:
      results.append(test_runner.run(suite))

  was_success = was_every_suite_successful(results)
  return 0 if was_success else 1


def delete_file (results_xml):
  if os.path.isfile(results_xml):
    os.remove(results_xml)


def was_every_suite_successful (results):
  suite_successes = map(lambda result: result.wasSuccessful(), results)
  was_success = all(suite_successes)
  return was_success


def create_test_suite (tests_dir, show_output=False, run_only_tests=None):
  command_runner = CommandRunner(cwd=CWD,
                                 output_stream=sys.stdout if show_output else
                                 None)
  test_reader = TestReader()
  test_case_builder = TestCaseBuilder(command_runner)
  test_configs = test_reader.read_from(tests_dir)

  if run_only_tests:
    test_configs = [config for config in test_configs if
                    config.testcase_dir_name() in run_only_tests]

  test_suite = test_case_builder.to_suite(test_configs)
  return test_suite


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
