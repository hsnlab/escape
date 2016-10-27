import abc
import os


class TestRunner:
  def __init__ (self, escape, test_runner_config):
    """

    :type test_runner_config: TestRunnerConfig
    """
    self.test_runner_config = test_runner_config
    self.escape = escape

  def run_testcase (self, filename):
    path = os.path.join( self.test_runner_config.test_case_directory, filename)
    self.escape.run(path)


class Escape():
  def __init__ (self):
    pass

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def run (self, filepath):
    pass


class TestRunnerConfig():
  def __init__ (self, test_case_directory):
    self.test_case_directory = test_case_directory


class CommandLineEscape(Escape):
  pass


class EscapeRunResult():
  def __init__ (self):
    pass
