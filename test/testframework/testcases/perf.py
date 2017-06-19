# Copyright 2017 Janos Czentye
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
import distutils.dir_util
import logging
import os
import shutil
import time

from testframework.testcases.basic import BasicSuccessfulTestCase
from testframework.testcases.domain_mock import DomainOrchestratorAPIMocker
from testframework.testcases.dynamic import DynamicallyGeneratedTestCase, \
  DynamicTestGenerator

log = logging.getLogger()


class PerformanceTestCase(BasicSuccessfulTestCase):
  """
  """

  def __init__ (self, result_folder=None, stat_folder=None, *args, **kwargs):
    super(PerformanceTestCase, self).__init__(*args, **kwargs)
    if not result_folder:
      result_folder = os.getcwd()
      log.warning("Result folder is missing! Using working dir: %s"
                  % result_folder)
    self.result_folder = os.path.join(result_folder,
                                      time.strftime("%Y%m%d%H%M%S"))
    self.stat_folder = stat_folder

  def tearDown (self):
    if self.result_folder is not None:
      target_dir = os.path.join(self.result_folder, self.test_case_info.name)
      if not os.path.exists(target_dir):
        os.makedirs(target_dir)
      log.debug("Store files into: %s" % target_dir)
      log.debug(self.stat_folder)
      if self.stat_folder is not None:
        distutils.dir_util.copy_tree(src=self.stat_folder, dst=target_dir)
      shutil.copytree(src=self.test_case_info.full_testcase_path,
                      dst=os.path.join(target_dir, "output"),
                      ignore=shutil.ignore_patterns('*.txt',
                                                    '*.sh',
                                                    '*.config'))
    super(PerformanceTestCase, self).tearDown()


class DynamicPerformanceTestCase(DynamicallyGeneratedTestCase):
  """
  """

  def __init__ (self, result_folder=None, stat_folder=None, *args, **kwargs):
    super(DynamicPerformanceTestCase, self).__init__(*args, **kwargs)
    if not result_folder:
      result_folder = os.getcwd()
      log.warning("Result folder is missing! Using working dir: %s"
                  % result_folder)
    self.result_folder = os.path.join(result_folder,
                                      time.strftime("%Y%m%d%H%M%S"))
    self.stat_folder = stat_folder

  def tearDown (self):
    if self.result_folder is not None:
      target_dir = os.path.join(self.result_folder, self.test_case_info.name)
      if not os.path.exists(target_dir):
        os.makedirs(target_dir)
      log.debug("Store files into: %s" % target_dir)
      log.debug(self.stat_folder)
      if self.stat_folder is not None:
        distutils.dir_util.copy_tree(src=self.stat_folder, dst=target_dir)
      shutil.copytree(src=self.test_case_info.full_testcase_path,
                      dst=os.path.join(target_dir, "output"),
                      ignore=shutil.ignore_patterns('*.txt',
                                                    '*.sh',
                                                    '*.config'))
    super(DynamicPerformanceTestCase, self).tearDown()


class DynamicMockingPerformanceTestCase(DynamicPerformanceTestCase):
  """
  """

  def __init__ (self, responses=None, *args, **kwargs):
    super(DynamicMockingPerformanceTestCase, self).__init__(*args, **kwargs)
    self.domain_mocker = DomainOrchestratorAPIMocker(**kwargs)
    dir = self.test_case_info.full_testcase_path
    if responses:
      self.domain_mocker.register_responses(dirname=dir, responses=responses)
    else:
      self.domain_mocker.register_responses_from_dir(dirname=dir)

  def setUp (self):
    super(DynamicMockingPerformanceTestCase, self).setUp()
    self.domain_mocker.start()

  def tearDown (self):
    super(DynamicMockingPerformanceTestCase, self).tearDown()
    self.domain_mocker.shutdown()


class DynamicPerformanceTestGenerator(DynamicTestGenerator):
  """
  """

  def __init__ (self, result_folder=None, stat_folder=None, *args, **kwargs):
    if not result_folder:
      result_folder = os.getcwd()
      log.warning("Result folder is missing! Using working dir: %s"
                  % result_folder)
    self.result_folder = os.path.join(result_folder,
                                      time.strftime("%Y%m%d%H%M%S"))
    self.stat_folder = stat_folder
    super(DynamicPerformanceTestGenerator, self).__init__(*args, **kwargs)

  def _create_test_cases (self):
    super(DynamicPerformanceTestGenerator, self)._create_test_cases()
    for tc in self._tests:
      if hasattr(tc, "result_folder"):
        tc.result_folder = self.result_folder
      if hasattr(tc, "stat_folder"):
        tc.stat_folder = self.stat_folder
