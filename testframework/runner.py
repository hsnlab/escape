import abc
import os
import subprocess
import time
import signal
import pexpect


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
    self.escape.run(path)


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
  def __init__ (self, escape_path="../escape.py"):
    self._escape_path = os.path.abspath(escape_path)
    self._cwd = os.path.dirname(self._escape_path)

  def run (self, filepath):
    command = [self._escape_path, "-dft", "-s", filepath]
    print (command)
    proc = subprocess.check_output(args=command,
                                   cwd=self._cwd
                                   )


class EscapeRunResult():
  def __init__ (self):
    pass
