# Copyright 2015 Janos Czentye <czentye@tmit.bme.hu>
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
"""
Contains miscellaneous helper functions.
"""
from functools import wraps
import logging
import os
from subprocess import check_call, CalledProcessError, STDOUT, Popen, PIPE
import warnings
import weakref


def schedule_as_coop_task (func):
  """
  Decorator functions for running functions in an asynchronous way as a
  microtask in recoco's cooperative multitasking context (in which POX was
  written).

  :param func: decorated function
  :type func: func
  :return: decorator function
  :rtype: func
  """
  from pox.core import core
  # copy meta info from func to decorator for documentation generation

  @wraps(func)
  def decorator (*args, **kwargs):
    # Use POX internal thread-safe wrapper for scheduling
    core.callLater(func, *args, **kwargs)

  return decorator


def call_as_coop_task (func, *args, **kwargs):
  """
  Schedule a coop microtask and run the given function with parameters in it.

  Use POX core logic directly.

  :param func: function need to run
  :type func: func
  :param args: nameless arguments
  :type args: tuple
  :param kwargs: named arguments
  :type kwargs: dict
  :return: None
  """
  from pox.core import core
  core.callLater(func, *args, **kwargs)


def run_silent (cmd):
  """
  Run the given shell command silent.

  It's advisable to give the command with a raw string literal e.g.: r'ps aux'.

  :param cmd: command
  :type cmd: str
  :return: return code of the subprocess call
  :rtype: int
  """
  try:
    return check_call(cmd.split(' '), stdout=open(os.devnull, 'wb'),
                      stderr=STDOUT, close_fds=True)
  except CalledProcessError:
    return None


def run_cmd (cmd):
  """
  Run a shell command and return the output.

  It's advisable to give the command with a raw string literal e.g.: r'ps aux'.

  :param cmd: command
  :type cmd: str
  :return: output of the command
  :rtype: str
  """
  return Popen(['/bin/sh', '-c', cmd], stdout=PIPE).communicate()[0]


def enum (*sequential, **named):
  """
  Helper function to define enumeration. E.g.:

  .. code-block:: python

    Numbers = enum(ONE=1, TWO=2, THREE='three')
    Numbers = enum('ZERO', 'ONE', 'TWO')
    Numbers.ONE
    1
    Numbers.reversed[2]
    'TWO'

  :param sequential: support automatic enumeration
  :type sequential: list
  :param named: support definition with unique keys
  :type named: dict
  :return: Enum object
  :rtype: dict
  """
  enums = dict(zip(sequential, range(len(sequential))), **named)
  enums['reversed'] = dict((value, key) for key, value in enums.iteritems())
  return type('enum', (), enums)


def quit_with_error (msg, logger=None):
  """
  Helper function for quitting in case of an error.

  :param msg: error message
  :type msg: str
  :param logger: logger name or logger object (default: core)
  :type logger: str or :any:`logging.Logger`
  :return: None
  """
  from pox.core import core
  import sys

  if isinstance(logger, logging.Logger):
    logger.fatal(msg)
  elif isinstance(logger, str):
    core.getLogger(logger).fatal(msg)
  else:
    core.getLogger("core").fatal(msg)
  core.quit()
  sys.exit(1)


class SimpleStandaloneHelper(object):
  """
  Helper class for layer APIs to catch events and handle these in separate
  handler functions.
  """

  def __init__ (self, container, cover_name):
    """
    Init.

    :param container: Container class reference
    :type: EventMixin
    :param cover_name: Container's name for logging
    :type cover_name: str
    """
    from pox.lib.revent.revent import EventMixin
    super(SimpleStandaloneHelper, self).__init__()
    assert isinstance(container,
                      EventMixin), "container is not subclass of EventMixin"
    self._container = weakref.proxy(container)
    self._cover_name = cover_name
    self._register_listeners()

  def _register_listeners (self):
    """
    Register event listeners.

    If a listener is explicitly defined in the class use this function
    otherwise use the common logger function

    :return: None
    """
    for event in self._container._eventMixin_events:
      handler_name = "_handle_" + event.__class__.__name__
      if hasattr(self, handler_name):
        self._container.addListener(event, getattr(self, handler_name),
                                    weak=True)
      else:
        self._container.addListener(event, self._log_event, weak=True)

  def _log_event (self, event):
    """
    Log given event.

    :param event: Event object which need to be logged
    :type event: Event
    :return: None
    """
    from pox.core import core
    core.getLogger("StandaloneHelper").getChild(self._cover_name).info(
      "Got event: %s from %s Layer" % (
        event.__class__.__name__, str(event.source._core_name).title()))


class Singleton(type):
  """
  Metaclass for classes need to be created only once.

  Realize Singleton design pattern in a pythonic way.
  """
  _instances = {}

  def __call__ (cls, *args):
    if cls not in cls._instances:
      cls._instances[cls] = super(Singleton, cls).__call__(*args)
    return cls._instances[cls]


def deprecated (func):
  """
  This is a decorator which can be used to mark functions as deprecated. It
  will result in a warning being emitted when the function is used.
  """

  def newFunc (*args, **kwargs):
    warnings.warn("Call to deprecated function %s." % func.__name__,
                  category=DeprecationWarning, stacklevel=2)
    return func(*args, **kwargs)

  newFunc.__name__ = func.__name__
  newFunc.__doc__ = func.__doc__
  newFunc.__dict__.update(func.__dict__)
  return newFunc


def remove_junks (log=logging.getLogger("cleanup")):
  # Kill remained clickhelper.py/click
  if os.geteuid() != 0:
    log.error("Cleanup process requires root privilege!")
    return
  log.debug("Cleanup still running VNF-related processes...")
  run_silent(r"sudo pkill -9 -f netconfd")
  run_silent(r"sudo pkill -9 -f clickhelper")
  run_silent(r"sudo pkill -9 -f click")
  log.debug("Cleanup any remained veth pair...")
  veths = run_cmd(r"ip link show | egrep -o '(uny_\w+)'").split('\n')
  # only need to del one end of the veth pair
  for veth in veths[::2]:
    if veth != '':
      run_silent(r"sudo ip link del %s" % veth)
  log.debug("Cleanup any Mininet-specific junk...")
  log.debug("Cleanup remained tmp files...")
  run_silent(r"rm  /tmp/*-startup-cfg.xml")
  # Call Mininet's own cleanup stuff
  from mininet.clean import cleanup
  cleanup()
