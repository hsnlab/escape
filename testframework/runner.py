from __future__ import print_function
import abc
import argparse
import os
import subprocess
from unittest.case import TestCase

import sys
import time
import signal
import pexpect
from pexpect import fdpexpect
from threading import Timer


class TestRunner:
  def __init__ (self, escape, test_runner_config):
    """

    :type escape: Escape
    :type test_runner_config: TestRunnerConfig
    """
    self._test_runner_config = test_runner_config
    self.escape = escape

  def run_testcase (self, filename):
    path = os.path.join(self._test_runner_config.test_case_directory, filename)
    return self.escape.run(path)


class Logger:
  def log_start (self, message):
    print(message)

  def log_end_output (self, output):
    print(output)
    pass

  def timed_out (self, pexpect_proc):
    print("Timed out: " + str(pexpect_proc))


class Escape():
  __metaclass__ = abc.ABCMeta

  def __init__ (self):
    pass

  @abc.abstractmethod
  def run (self, filepath):
    pass


class TestRunnerConfig():
  def __init__ (self, test_case_directory):
    self.test_case_directory = test_case_directory


class CommandLineEscape(Escape):
  OPT_QUIT_ON_DEPLOY = "-q"
  OPT_DEBUG = "-d"
  OPT_TEST_OUTPUT = "-t"
  OPT_RUN_INFRA = "-f"
  OPT_SOURCE_FILE = "-s"
  KILL_TIMEOUT = 30

  def __init__ (self, escape_path=__file__ + "/../../escape.py", logger=Logger(), command_runner=None):
    self.logger = logger
    self._escape_path = os.path.abspath(escape_path)
    self._cwd = os.path.dirname(self._escape_path)
    self.command_runner = CommandRunner(
      cwd=self._cwd,
      kill_timeout=self.KILL_TIMEOUT,
      on_kill=
      self._kill_process) if command_runner is None else command_runner

  def _kill_process (self, p):
    self.logger.timed_out(p)
    self.logger.log_end_output(p.before)
    raise AssertionError("Process timed out" +
                         p.command + " " + str(p.args) +
                         "\n" + str(p)
                         )

  def run (self, filepath):
    command = [
      self._escape_path,
      self.OPT_DEBUG,
      self.OPT_TEST_OUTPUT,
      self.OPT_RUN_INFRA,
      self.OPT_QUIT_ON_DEPLOY,
      self.OPT_SOURCE_FILE,
      filepath,
    ]

    self.logger.log_start("Starting testcase " + filepath + " : " + ", ".join(command))

    proc = self.command_runner.execute(command)

    _, log_output = "", proc.before
    self.logger.log_end_output(log_output)
    return EscapeRunResult(log_output)


class EscapeRunResult():
  def __init__ (self, output=""):
    self.log_output = output


class CommandRunner:
  KILL_TIMEOUT = 30

  def __init__ (self, cwd, kill_timeout=KILL_TIMEOUT, on_kill=None, output_stream = None):
    self.output_stream = output_stream
    self._cwd = cwd
    self.on_kill = on_kill
    self.kill_timeout = kill_timeout

  def _kill_process (self, proc):
    proc.sendcontrol('c')
    if self.on_kill:
      self.on_kill(proc)
    else:
      self._default_on_kill_handler(proc)

  def _default_on_kill_handler (self, process):
    raise Exception(
      "Command was killed after " + str(self.kill_timeout) + " seconds " +
      "Command: " + str(process)
    )

  def execute (self, command):
    proc = pexpect.spawn(command[0],
                         args=command[1:],
                         timeout=120,
                         cwd=self._cwd,
                         logfile=self.output_stream
                         )

    kill_timer = Timer(self.KILL_TIMEOUT, self._kill_process, [proc])
    kill_timer.start()

    proc.expect(pexpect.EOF)
    kill_timer.cancel()
    if "No such file or directory" in proc.before:
      raise Exception("CommandRunner Error:" + proc.before)

    return proc


class TestReader:
  TEST_DIR_PREFIX = "case"

  def read_from (self, test_cases_dir):
    dirs = os.listdir(test_cases_dir)

    cases = [
      RunnableTestCaseInfo(
        testcase_dir_name=case_dir,
        full_testcase_path=test_cases_dir + "/" + case_dir + "/"
      )
      for case_dir in dirs if case_dir.startswith(self.TEST_DIR_PREFIX)
      ]
    return cases


class RunnableTestCaseInfo:
  def __init__ (self, testcase_dir_name, full_testcase_path):
    self._full_testcase_path = full_testcase_path
    self._testcase_dir_name = testcase_dir_name

  def testcase_dir_name (self):
    return self._testcase_dir_name

  def full_testcase_path (self):
    return self._full_testcase_path

  def __repr__ (self):
    return "RunnableTestCase [" + self._testcase_dir_name + "]"


default_cmd_opts = {
  "show_output": False,
  "run_only": None
}


def parse_cmd_opts (argv):
  parser = argparse.ArgumentParser(
    description="ESCAPE Test runner",
    add_help=True,
    prog="run_tests.py"
  )

  parser.add_argument("--show-output", "-o", action="store_true", help="Show ESCAPE output")
  args = parser.parse_args(argv)
  kwargs = args._get_kwargs()
  return dict(default_cmd_opts.items() + kwargs)


class SimpleTestCase(TestCase):
  def __init__ (self, test_case_config, command_runner):
    """

    :type command_runner: CommandRunner
    :type test_case_config: RunnableTestCaseInfo
    """
    self.command_runner = command_runner
    self.test_case_config = test_case_config

  def runTest (self):
    self.result = self.command_runner.execute(self.test_case_config + "/run.sh")
