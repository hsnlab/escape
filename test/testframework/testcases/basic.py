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
import logging
import os
from unittest.case import TestCase
from unittest.util import strclass

from testframework.runner import EscapeRunResult, RunnableTestCaseInfo, \
  ESCAPECommandRunner

log = logging.getLogger()
ESCAPE_LOG_FILE_NAME = "escape.log"


class BasicErrorChecker(object):
  """
  Container class for the basic result detection functions.
  """
  WARNING_PREFIX = "|WARNING|"
  ERROR_PREFIX = "|ERROR|"
  CRITICAL_PREFIX = "|CRITICAL|"

  SEPARATOR = "|---|"

  PRE_CONTEXT = 5
  POST_CONTEXT = 5

  ADAPTATION_ENDED = "All installation process has been finished!"
  RESULT_LOG = "instantiation has been finished"
  SUCCESS_RESULTS = ("SUCCESS", "DEPLOYED")
  ERROR_RESULTS = "DEPLOYMENT_ERROR"

  @classmethod
  def detect_error (cls, result):
    """
    Detect messages logged in ERROR or CRITICAL log level.

    :param result: result object of ESCAPE test run
    :type result: EscapeRunResult
    :return: detected error message
    :rtype: str or None
    """
    for i, line in enumerate(reversed(result.log_output)):
      if line.startswith(cls.ERROR_PREFIX) or \
         line.startswith(cls.CRITICAL_PREFIX):
        pos = len(result.log_output) - i
        return ''.join(
          result.log_output[pos - cls.PRE_CONTEXT:pos + cls.POST_CONTEXT])

  @classmethod
  def detect_unsuccessful_result (cls, result):
    """
    Detect the unsuccessful orchestration message in the result log.

    :param result: result object of ESCAPE test run
    :type result: EscapeRunResult
    :return: detected error message
    :rtype: str or None
    """
    for line in reversed(result.log_output):
      if cls.ADAPTATION_ENDED in line:
        break
      if cls.RESULT_LOG in line:
        for sr in cls.ERROR_RESULTS:
          if sr in line:
            return None
        else:
          return line
    return "No result line detected!"


class WarningChecker(BasicErrorChecker):
  """
  Container class for the unexpected warning detection functions.
  """
  ACCEPTABLE_WARNINGS = [
    "Mapping algorithm in Layer: service is disabled!",
    "Mapping algorithm in Layer: orchestration is disabled!",
    "Scheduler didn't quit in time",
    "No domain has been detected!",
    "No SGHops were given in the Service Graph!",
    "Resource parameter delay is not given",
    "Version are different!",
    "Resource parameter bandwidth is not given in",
    "If multiple infra nodes are present in the substrate graph",
    "No SAPs could be found,",
    "No SAP - SAP chain were given!",
    "Physical interface:",
    "Skip starting xterms on SAPS according to global config"
  ]

  @classmethod
  def _get_iterator_over_warnings (cls, log):
    """
    Return the iterator which iterates over only the warning logs.

    :param log: logged lines
    :type log: list[str]
    :return: iterator
    """
    return (line.split(cls.SEPARATOR)[-1]
            for line in log if line.startswith(cls.WARNING_PREFIX))

  @classmethod
  def detect_unexpected_warning (cls, result):
    """
    Detect unexpected warning log.

    :param result: result object of ESCAPE test run
    :type result: EscapeRunResult
    :return: detected warning message
    :rtype: str or None
    """
    for warning in cls._get_iterator_over_warnings(result.log_output):
      acceptable = False
      for acc_warn in cls.ACCEPTABLE_WARNINGS:
        if warning.startswith(acc_warn):
          acceptable = True
          break
      if acceptable:
        continue
      else:
        return warning
    return None


class EscapeTestCase(TestCase):
  """
  EscapeTestCase is a test case for the case01, case02 structure. It will run
  ESCAPE
  then place the result into the self.result field.
  You should implement the runTest method to verify the result
  See BasicSuccessfulTestCase
  """

  def __init__ (self, test_case_info, command_runner, **kwargs):
    """
    :type test_case_info: RunnableTestCaseInfo
    :type command_runner: ESCAPECommandRunner
    """
    super(EscapeTestCase, self).__init__()
    self.test_case_info = test_case_info
    self.command_runner = command_runner
    self.run_result = None
    """:type result: testframework.runner.EscapeRunResult"""
    self.success = False
    log.debug(">>> Init  %r" % self)

  def __str__ (self):
    return "Test:   %s\t(%s)" % (
      self.test_case_info.name, self.__class__.__name__)

  def __repr__ (self):
    return "%s[name: %s]" % (self.__class__.__name__, self.test_case_info.name)

  def id (self):
    """
    Generate ID in specific format for XMLRunner to detect testcase class and
    name correctly.

    :return: id
    :rtype: str
    """
    return "%s.%s" % (strclass(self.__class__), self.test_case_info.name)

  def setUp (self):
    """
    Setup the test case fixture.

    :return:
    """
    log.debug("\nSetup fixture...")
    super(EscapeTestCase, self).setUp()
    log_file = os.path.join(self.test_case_info.full_testcase_path,
                            ESCAPE_LOG_FILE_NAME)
    # Remove escape.log it exists
    if os.path.exists(log_file):
      os.remove(log_file)
    # Add cleanup of commandRunner
    self.addCleanup(function=self.command_runner.cleanup)

  def runTest (self):
    """
    Run the test case and evaluate the result.
    """
    # Run test case
    self.run_escape()
    # Evaluate result
    self.verify_result()
    # Mark test case as success
    self.success = True

  def tearDown (self):
    """
    Tear down test fixture.

    It will be invoked only if the test is successful.
    """
    log.debug("\nTear down fixture...")
    self.terminate_testcase()
    super(EscapeTestCase, self).tearDown()

  def verify_result (self):
    """
    Template method for analyzing run result.
    """
    log.debug("\nVerifying results...")

  def run_escape (self):
    """
    Run ESCAPE with the prepared test config.
    """
    raise NotImplementedError

  def terminate_testcase (self):
    raise NotImplementedError


class BasicSuccessfulTestCase(EscapeTestCase, WarningChecker):
  """
  Basic successful result and warning checking.
  """

  def run_escape (self):
    """
    Run ESCAPE with the prepared test config.
    """
    try:
      # Run ESCAPE test
      self.command_runner.execute()
      # Collect result
      self.run_result = self.collect_result_from_log()
    except KeyboardInterrupt:
      log.error("\nReceived KeyboardInterrupt! Abort running testcase...")
      self.terminate_testcase()
      self.collect_result_from_log()
      raise

  def terminate_testcase (self):
    if self.command_runner.is_alive:
      self.command_runner.kill_process()

  def collect_result_from_log (self):
    """
    Parse the output log to memory as an EscapeResult object.

    :rtype: EscapeRunResult
    """
    log_file = os.path.join(self.test_case_info.full_testcase_path,
                            ESCAPE_LOG_FILE_NAME)
    try:
      with open(log_file) as f:
        return EscapeRunResult(output=f.readlines())
    except IOError as e:
      log.warning("Got exception during result processing: %s" % e.message)
      return EscapeRunResult(output=str(e), exception=e)

  def get_result_from_stream (self):
    """
    Return the buffered ESCAPE log collected by pexpect spawn process.

    :rtype: str
    """
    output_stream = self.command_runner.get_process_output_stream()
    return output_stream if output_stream else ""

  def verify_result (self):
    super(BasicSuccessfulTestCase, self).verify_result()
    if self.run_result.log_output is None:
      raise RuntimeError("log_output is missing!")
    # Detect TIMEOUT error
    self.assertFalse(self.command_runner.timeout_exceeded,
                     msg="Running timeout(%ss) is exceeded!" %
                         self.command_runner.kill_timeout)
    # Detect ERROR messages first
    detected_error = self.detect_error(self.run_result)
    self.assertIsNone(detected_error,
                      msg="ERROR detected:\n%s" % detected_error)
    # Search for successful orchestration message
    error_result = self.detect_unsuccessful_result(self.run_result)
    self.assertIsNone(error_result,
                      msg="Unsuccessful result detected:\n%s" % error_result)
    # Detect unexpected WARNINGs that possibly means abnormal behaviour
    warning = self.detect_unexpected_warning(self.run_result)
    self.assertIsNone(warning,
                      msg="Unexpected WARNING detected:\n%s" % warning)


class RootPrivilegedSuccessfulTestCase(BasicSuccessfulTestCase):
  """
  Skip the test if the root password is requested on the console.
  """
  SUDO_KILL_TIMEOUT = 2

  def check_root_privilege (self):
    # Due to XMLTestRunner implementation test cannot skip in setUp()
    enabled = ESCAPECommandRunner("sudo uname").test(self.SUDO_KILL_TIMEOUT)
    if not enabled:
      self.skipTest("Root privilege is required to run the testcase: %s" %
                    self.test_case_info.testcase_dir_name)

  def runTest (self):
    # Check root privilege first
    self.check_root_privilege()
    # Run test case
    super(RootPrivilegedSuccessfulTestCase, self).runTest()
