import os
from unittest import TestCase

from testframework.runner import TestReader


class TestTestReader(TestCase):
  TESTS_DIR = os.path.dirname(__file__) + "/testresources/testreader/"
  _reader = None

  def setUp (self):
    super(TestTestReader, self).setUp()
    self._reader = TestReader()

  def test_given_no_testcases_in_dir_returns_empty_list (self):
    self.assertListEqual([], self.read(self.empty_dir()))

  def test_given_testcases_in_dir_returns_testcase_objects (self):
    dir = self.testcases_dir()
    expected_case_names = ["case01", "case02", "case123123"]
    cases = self.read(dir)

    case_names = [case.testcase_dir_name() for case in cases]
    case_names.sort()
    self.assertListEqual(expected_case_names, case_names)

  def test_given_a_testcase_returns_full_path (self):
    case = self.read_first_testcase()
    self.assertEqual(self.testcases_dir() + "/case01/", case.full_testcase_path())

  def read_first_testcase (self):
    return [case for case in self.read(self.testcases_dir()) if case.testcase_dir_name() == "case01"][0]

  def read (self, dir):
    return self._reader.read_from(dir)

  def testcases_dir (self):
    dir = self.TESTS_DIR + "nonempty"
    return dir

  def empty_dir (self):
    return self.TESTS_DIR + "empty"
