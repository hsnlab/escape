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
import importlib
import json
import os
from unittest import BaseTestSuite
from unittest.case import TestCase
from unittest.util import strclass

from runner import EscapeRunResult, RunnableTestCaseInfo, CommandRunner

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

  RESULT_LOG = "NF-FG instantiation has been finished"
  SUCCESS_RESULT = "DEPLOYED"
  ERROR_RESULT = "DEPLOYMENT_ERROR"

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
      if cls.RESULT_LOG in line:
        if cls.SUCCESS_RESULT in line:
          print "Successful result detected: %s" % line
          return None
        else:
          return line
    return "No result line detected!"


class WarningChecker(BasicErrorChecker):
  """
  Container class for the unexpected warning detection functions.
  """
  ACCEPTABLE_WARNINGS = [
    "Unidentified layer name in loaded configuration",
    "Mapping algorithm in Layer: service is disabled!",
    "Mapping algorithm in Layer: orchestration is disabled!",
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
    :type command_runner: CommandRunner
    """
    super(EscapeTestCase, self).__init__()
    self.test_case_info = test_case_info
    self.command_runner = command_runner
    self.result = None
    """:type result: testframework.runner.EscapeRunResult"""
    # print "Initiate testcase: %s" % self.test_case_info.testcase_dir_name

  def __str__ (self):
    return "Test:\t%s\t(%s)" % (
      self.test_case_info.name, self.__class__.__name__)

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

  def tearDown (self):
    """
    Tear down test fixture.

    It will be invoked only if the test is successful.
    """
    super(EscapeTestCase, self).tearDown()

  def run_escape (self):
    """
    Run ESCAPE with the prepared test config.
    """
    try:
      # Run ESCAPE test
      self.command_runner.execute()
      # Collect result
      self.result = self.collect_result_from_log()
    except KeyboardInterrupt:
      self.command_runner.kill_process()
      self.collect_result_from_log()
      raise

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
      return EscapeRunResult(output=str(e), exception=e)

  def get_result_from_stream (self):
    """
    Return the buffered ESCAPE log collected by pexpect spawn process.

    :rtype: str
    """
    output_stream = self.command_runner.get_process_output_stream()
    return output_stream if output_stream else ""

  def verify_result (self):
    """
    Template method for analyzing run result.
    """
    raise NotImplementedError('Not implemented yet!')


class BasicSuccessfulTestCase(EscapeTestCase, WarningChecker):
  """
  Basic successful result and warning checking.
  """

  def verify_result (self):
    # Detect ERROR messages first
    detected_error = self.detect_error(self.result)
    self.assertIsNone(detected_error,
                      msg="ERROR detected:\n%s" % detected_error)
    # Search for successful orchestration message
    error_result = self.detect_unsuccessful_result(self.result)
    self.assertIsNone(error_result,
                      msg="Unsuccessful result detected:\n%s" % error_result)
    # Detect unexpected WARNINGs that possibly means abnormal behaviour
    warning = self.detect_unexpected_warning(self.result)
    self.assertIsNone(warning,
                      msg="Unexpected WARNING detected:\n%s" % warning)


class RootPrivilegedSuccessfulTestCase(BasicSuccessfulTestCase):
  """
  Skip the test if the root password is requested on the console.
  """
  SUDO_KILL_TIMEOUT = 2

  def check_root_privilege (self):
    # Due to XMLTestRunner implementation test cannot skip in setUp()
    test_run = CommandRunner(cmd="sudo uname",
                             kill_timeout=self.SUDO_KILL_TIMEOUT).execute()
    if test_run.is_killed:
      self.skipTest("Root privilege is required to run the testcase: %s" %
                    self.test_case_info.testcase_dir_name)

  def runTest (self):
    # Check root privilege first
    self.check_root_privilege()
    # Run test case
    super(RootPrivilegedSuccessfulTestCase, self).runTest()


class DynamicallyGeneratedTestCase(BasicSuccessfulTestCase):
  """
  Test case class which generates the required resource and request files for
  the actual testcase on the fly based on the given parameters.
  Example config:

  "test": {
    "module": "testframework.testcases",
    "class": "DynamicallyGeneratedTestCase",
    "request_cfg": {
      "generator": "xxx",
      "seed": 11,
      ...
    },
    "topology_cfg": {
      "generator": "xxx",
      "seed": 15,
      ...
    }
  }

  """
  GENERATOR_MODULE = "testframework.generator.generator"
  GENERATOR_ENTRY_NAME = "generator"
  REQUEST_FILE_NAME = "gen-request.nffg"
  TOPOLOGY_FILE_NAME = "gen-topology.nffg"

  def __init__ (self, request_cfg=None, topology_cfg=None, **kwargs):
    """

    :type request_cfg: dict
    :type topology_cfg: dict
    :type kwargs: dict
    """
    super(DynamicallyGeneratedTestCase, self).__init__(**kwargs)
    self.request_cfg = request_cfg
    self.new_req = False
    self.topology_cfg = topology_cfg
    self.new_topo = False

  @classmethod
  def __generate_nffg (cls, cfg):
    """

    :type cfg: dict
    :rtype: :any:`NFFG`
    """
    # If config is not empty and testcase is properly configured
    if not cfg or cls.GENERATOR_ENTRY_NAME not in cfg:
      return None
    params = cfg.copy()
    try:
      generator_func = getattr(importlib.import_module(cls.GENERATOR_MODULE),
                               params.pop(cls.GENERATOR_ENTRY_NAME))
      return generator_func(**params)
    except AttributeError as e:
      raise Exception("Generator function is not found: %s" % e.message)

  def dump_generated_nffg (self, cfg, file_name):
    """

    :type file_name: str
    :return: generation was successful
    :rtype: bool
    """
    nffg = self.__generate_nffg(cfg=cfg)
    if nffg is not None:
      req_file_name = os.path.join(self.test_case_info.full_testcase_path,
                                   file_name)
      with open(req_file_name, "w") as f:
        # f.write(nffg.dump_to_json())
        json.dump(nffg.dump_to_json(), f, indent=2)

  def setUp (self):
    super(DynamicallyGeneratedTestCase, self).setUp()
    # Generate request
    self.new_req = self.dump_generated_nffg(cfg=self.request_cfg,
                                            file_name=self.REQUEST_FILE_NAME)
    # Generate topology
    self.new_topo = self.dump_generated_nffg(cfg=self.topology_cfg,
                                             file_name=self.TOPOLOGY_FILE_NAME)

  def tearDown (self):
    # Delete request if it is generated
    if self.new_req:
      try:
        os.remove(os.path.join(self.test_case_info.full_testcase_path,
                               self.REQUEST_FILE_NAME))
      except OSError:
        pass
    # Delete topology if it is generated
    if self.new_topo:
      try:
        os.remove(os.path.join(self.test_case_info.full_testcase_path,
                               self.TOPOLOGY_FILE_NAME))
      except OSError:
        pass
    super(DynamicallyGeneratedTestCase, self).tearDown()

  # def verify_result (self):
  #   pass


class DynamicTestGenerator(BaseTestSuite):
  """
  Special TestSuite class which populate itself with TestCases based on the
  given parameters.
  Example config:

  "test": {
    "module": "testframework.testcases",
    "class": "DynamicTestGenerator",
    "mode": "",
    "#oftopo": 10,
    "#ofrequest": 10,
    "testcase": {
      "module": "testframework.testcases",
      "class": "DynamicallyGeneratedTestCase",
      "request_cfg": {
        "generator": "xxx",
        "seed": 11
      },
      "topology_cfg": {
        "generator": "xxx",
        "seed": 15
      }
    }
  }
  """
  DEFAULT_TEST_CASE_CLASS = DynamicallyGeneratedTestCase

  def __init__ (self, **kwargs):
    """
    :type test_case_info: RunnableTestCaseInfo
    :type command_runner: CommandRunner
    """
    super(DynamicTestGenerator, self).__init__(**kwargs)
    self._create_test_cases()

  def _create_test_cases (self):
    # TODO - create test cases based on params in kwargs
    pass
