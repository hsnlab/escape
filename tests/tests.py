from __future__ import print_function

import os
import sys

import unittest
from unittest import loader
from unittest.loader import TestLoader

import xmlrunner

print(os.getenv("PYTHONPATH"))


def main ():

  print(os.getcwd())
  top_level_dir = os.path.dirname(__file__) + "/../"

  results_xml = "results.xml"
  os.remove(results_xml)
  results = []
  with open(results_xml, 'wb') as output:
    test_loader = TestLoader()
    testframework_tests = test_loader.discover("../testframework/tests", top_level_dir=top_level_dir)
    endtoend_tests = test_loader.discover("../tests/endtoend", top_level_dir=".")

    test_runner = xmlrunner.XMLTestRunner(
      output=output,
      verbosity=2
    )

    suites = [
      testframework_tests,
      endtoend_tests
    ]

    for suite in suites:
      results.append(test_runner.run(suite))

  suite_successes = map(lambda result: result.wasSuccessful(), results)
  was_success = all(suite_successes)

  return 0 if was_success else 1


if __name__ == "__main__":
  sys.exit(main())
