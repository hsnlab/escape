from __future__ import print_function

import os
import unittest
from unittest import loader
from unittest.loader import TestLoader

import xmlrunner


def discoverTests (tests_dir, top_dir):
  pass


def main ():
  results_xml = "results.xml"
  os.remove(results_xml)
  with open(results_xml, 'wb') as output:
    test_loader = TestLoader()
    top_level_dir = os.path.dirname(__file__) + "/../"
    testframework_tests = test_loader.discover("../testframework/tests", top_level_dir=top_level_dir)
    endtoend_tests = test_loader.discover("../tests/endtoend", top_level_dir=".")

    test_runner = xmlrunner.XMLTestRunner(
      output=output,
      verbosity=2
    )

    test_runner.run(testframework_tests)
    test_runner.run(endtoend_tests)


if __name__ == "__main__":
  main()
