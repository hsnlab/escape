#!/usr/bin/python2.7
from __future__ import print_function

import os

import sys

escape_root_dir = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + "/../")
sys.path.insert(0, escape_root_dir)

from unittest.runner import TextTestRunner
from unittest.case import TestCase
from xmlrunner import unittest

from testframework.testcases import BasicSuccessfulTestCase, TestCaseBuilder

from unittest.suite import TestSuite

import xmlrunner

from testframework.runner import TestReader, CommandRunner, TestRunnerConfig, RunnableTestCaseInfo, parse_cmd_opts


def main (argv):
  results_xml = "results.xml"
  delete_file(results_xml)

  tests_dir = escape_root_dir + "/test"
  cmd_settings = parse_cmd_opts(argv)

  test_suite = create_test_suite(tests_dir=tests_dir,
                                 show_output=cmd_settings["show_output"],
                                 run_only_tests=cmd_settings["testcases"]
                                 )

  print("Found %d testcases" % test_suite.countTestCases())

  suites = [
    test_suite
  ]

  results = []
  with open(results_xml, 'wb') as output:
    test_runner = xmlrunner.XMLTestRunner(
      output=output,
      verbosity=2,
    )

    for suite in suites:
      results.append(test_runner.run(suite))

  was_success = was_every_suite_successful(results)

  return 0 if was_success else 1


def delete_file (results_xml):
  if (os.path.isfile(results_xml)):
    os.remove(results_xml)


def was_every_suite_successful (results):
  suite_successes = map(lambda result: result.wasSuccessful(), results)
  was_success = all(suite_successes)
  return was_success


def create_test_suite (tests_dir, show_output=False, run_only_tests=None):
  command_runner = CommandRunner(cwd=escape_root_dir,
                                 output_stream=sys.stdout if show_output else None
                                 )
  test_reader = TestReader()
  test_case_builder = TestCaseBuilder(command_runner)
  test_configs = test_reader.read_from(tests_dir)

  if run_only_tests:
    test_configs = [config for config in test_configs if config.testcase_dir_name() in run_only_tests]

  test_suite = test_case_builder.to_suite(test_configs)
  return test_suite


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
