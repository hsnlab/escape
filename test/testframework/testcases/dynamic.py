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
import itertools
import json
import logging
import os
from pprint import pformat
from unittest import BaseTestSuite

from testframework.generator.generator import DEFAULT_SEED
from testframework.runner import RunnableTestCaseInfo, CommandRunner
from testframework.testcases.basic import BasicSuccessfulTestCase

log = logging.getLogger()


class DynamicallyGeneratedTestCase(BasicSuccessfulTestCase):
  """
  Test case class which generates the required resource and request files for
  the actual testcase on the fly based on the given parameters.
  Example config:

  "test": {
    "module": "testframework.testcases",
    "class": "DynamicallyGeneratedTestCase",
    "request_cfg": {
      "generator": "eight_loop_requests",
      "abc_nf_types_len": 10,
      "seed": 0,
      "eightloops": 3
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
    log.debug("request_cfg:\n%s\ntopology_cfg:\n%s"
              % (pformat(self.request_cfg, indent=2),
                 pformat(self.topology_cfg, indent=2)))

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
      return generator_func(**params) if generator_func else None
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
        json.dump(nffg.dump_to_json(), f, indent=2, sort_keys=True)
    return True

  def setUp (self):
    super(DynamicallyGeneratedTestCase, self).setUp()
    # Generate request
    self.new_req = self.dump_generated_nffg(cfg=self.request_cfg,
                                            file_name=self.REQUEST_FILE_NAME)
    # Generate topology
    self.new_topo = self.dump_generated_nffg(cfg=self.topology_cfg,
                                             file_name=self.TOPOLOGY_FILE_NAME)

  def tearDown (self):
    # Skip input deletion if the test case was unsuccessful for further
    # investigation
    if not self.success:
      return
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


class DynamicTestGenerator(BaseTestSuite):
  """
  Special TestSuite class which populate itself with TestCases based on the
  given parameters.
  Example config:

  "test": {
    "module": "testframework.testcases",
    "class": "DynamicTestGenerator",
    "full_combination": true,
    "num_of_requests": 3,
    "num_of_topos": 5,
    "testcase_cfg": {
      "module": "testframework.testcases",
      "class": "DynamicallyGeneratedTestCase",
      "request_cfg": {
        "generator": "eight_loop_requests",
        "seed": 0
      },
      "topology_cfg": {
        "generator": "xxx",
        "seed": 0
      }
    }
  }
  """
  DEFAULT_TESTCASE_CLASS = DynamicallyGeneratedTestCase
  REQUEST_CFG_NAME = "request_cfg"
  TOPOLOGY_CFG_NAME = "topology_cfg"
  SEED_NAME = "seed"

  def __init__ (self, test_case_info, command_runner, testcase_cfg=None,
                full_combination=False, num_of_requests=1, num_of_topos=1,
                **kwargs):
    """
    :type test_case_info: RunnableTestCaseInfo
    :type command_runner: CommandRunner
    """
    super(DynamicTestGenerator, self).__init__(**kwargs)
    self.test_case_info = test_case_info
    self.command_runner = command_runner
    self.testcase_cfg = testcase_cfg
    self.full_combination = full_combination
    self.num_of_requests = num_of_requests
    self.num_of_topos = num_of_topos
    self._create_test_cases()

  def __get_seed_generator (self):
    """
    Return an iterator which generates the tuple (request, topology) of seed
    values for test cases based on the config values:
      * default seed value which can be a number or a list of seed values
      * number of generated request/topology
      * test generation mode (full_combination or ordered pairs of request/topo)

    If the seed value is a number, this generator considers it as the first
    value of the used seed interval.
    If the seed value is a list, this generator considers it as the seed
    interval and the number_of_* parameters mark out the used values from the
    beginning of the seed intervals.

    Based on the request and topology seed intervals this function generates
    the pairs of seeds using the full_combination flag.

    Generation modes (full_combination, num_of_requests, num_of_topos):

    False, 0, 0,    -->  1          testcase WITHOUT generation
    False, N>0, 0   -->  1          testcase with ONLY request generation
    False, 0, M>0   -->  1          testcase with ONLY topology generation
    False, N>0, M>0 -->  min(N, M)  testcase with generated ordered pairs
    ---------------------------------------------------------------------
    True, 0, 0,     -->  1          testcase WITHOUT generation
    True, N>0, 0    -->  N          testcase with ONLY request generation
    True, 0, M>0    -->  M          testcase with ONLY topology generation
    True, N>0, M>0  -->  N x M      testcase with generated input (cartesian)

    :return: iterator
    """
    seed_iterators = []
    if not self.testcase_cfg:
      return
    if self.num_of_requests > 0 and self.REQUEST_CFG_NAME in self.testcase_cfg:
      if self.SEED_NAME in self.testcase_cfg[self.REQUEST_CFG_NAME]:
        seed = self.testcase_cfg[self.REQUEST_CFG_NAME][self.SEED_NAME]
        if isinstance(seed, list):
          seed_iterators.append(iter(seed))
        else:
          seed_iterators.append(xrange(seed, seed + self.num_of_requests))
      else:
        seed_iterators.append(
          xrange(DEFAULT_SEED, DEFAULT_SEED + self.num_of_requests))
    else:
      seed_iterators.append((None,))
    if self.num_of_topos > 0 and self.TOPOLOGY_CFG_NAME in self.testcase_cfg:
      if self.SEED_NAME in self.testcase_cfg[self.TOPOLOGY_CFG_NAME]:
        seed = self.testcase_cfg[self.TOPOLOGY_CFG_NAME][self.SEED_NAME]
        if isinstance(seed, list):
          seed_iterators.append(iter(seed))
        else:
          seed_iterators.append(xrange(seed, seed + self.num_of_topos))
      else:
        seed_iterators.append(
          xrange(DEFAULT_SEED, DEFAULT_SEED + self.num_of_topos))
    else:
      seed_iterators.append((None,))
    if self.full_combination:
      return itertools.product(*seed_iterators)
    else:
      return itertools.izip(*seed_iterators)

  def _create_test_cases (self):

    # Get testcase class
    if "module" in self.testcase_cfg and 'class' in self.testcase_cfg:
      TestCaseClass = getattr(importlib.import_module(
        self.testcase_cfg['module']),
        self.testcase_cfg['class'])
    else:
      log.warning("No testcase class was defined to testcase: %s! "
                  "Use default testcase class: %s" %
                  (self.test_case_info.name, self.DEFAULT_TESTCASE_CLASS))
      TestCaseClass = self.DEFAULT_TESTCASE_CLASS
    # Get generation config
    for req_seed, topo_seed in self.__get_seed_generator():
      testcase_cfg = self.testcase_cfg.copy() if self.testcase_cfg else {}
      # Create request config based on config file and generated seed value
      if req_seed is not None and testcase_cfg and \
            self.REQUEST_CFG_NAME in testcase_cfg:
        req_cfg = testcase_cfg[self.REQUEST_CFG_NAME].copy()
        req_cfg[self.SEED_NAME] = req_seed
      else:
        req_cfg = None
      # Create topology config based on config file and generated seed value
      if topo_seed is not None and testcase_cfg and \
            self.TOPOLOGY_CFG_NAME in testcase_cfg:
        topo_cfg = testcase_cfg.pop(self.TOPOLOGY_CFG_NAME).copy()
        topo_cfg[self.SEED_NAME] = topo_seed
      else:
        topo_cfg = None
      # Del unnecessary params
      for name in ('class', 'name',
                   self.REQUEST_CFG_NAME, self.TOPOLOGY_CFG_NAME):
        testcase_cfg.pop(name, None)
      tci = self.test_case_info.clone()
      tci.sub_name = self.countTestCases()
      # Create TestCase instance
      self.addTest(TestCaseClass(test_case_info=tci,
                                 command_runner=self.command_runner,
                                 request_cfg=req_cfg,
                                 topology_cfg=topo_cfg,
                                 **testcase_cfg))
