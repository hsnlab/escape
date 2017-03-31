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
"""
Contains miscellaneous helper functions.
"""
import cProfile
import io
import logging
import os
import pstats
import re
import socket
import time
import warnings
import weakref
from functools import wraps
from subprocess import STDOUT, Popen, PIPE

# Log level constant for additional VERBOSE level
VERBOSE = 5
"""Verbose logging level"""


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
    return core.callLater(func, *args, **kwargs)

  return decorator


def schedule_delayed_as_coop_task (delay=0):
  """
  Decorator functions for running functions delayed in recoco's cooperative
  multitasking context.

  :param delay: delay in sec (default: 1s)
  :type delay: int
  :return: decorator function
  :rtype: func
  """

  def decorator (func):
    from pox.core import core
    if delay:
      # If delay is set use callDelayed to call function delayed
      @wraps(func)
      def delayed_wrapper (*args, **kwargs):
        # Use POX internal thread-safe wrapper for scheduling
        return core.callDelayed(delay, func, *args, **kwargs)

      # Return specific wrapper
      return delayed_wrapper
    else:
      # If delay is not set use regular callLater to call function
      @wraps(func)
      def one_time_wrapper (*args, **kwargs):
        # Use POX internal thread-safe wrapper for scheduling
        return core.callLater(func, *args, **kwargs)

      # Return specific wrapper
      return one_time_wrapper

  # Return the decorator
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


def call_delayed_as_coop_task (func, delay=0, *args, **kwargs):
  """
  Schedule a coop microtask with a given time.

  Use POX core logic directly.

  :param delay: delay of time
  :type delay: int
  :param func: function need to run
  :type func: func
  :param args: nameless arguments
  :type args: tuple
  :param kwargs: named arguments
  :type kwargs: dict
  :return: None
  """
  from pox.core import core
  core.callDelayed(delay, func, *args, **kwargs)


def run_cmd (cmd):
  """
  Run a shell command and return the output.

  It's advisable to give the command with a raw string literal e.g.: r'ps aux'.

  :param cmd: command
  :type cmd: str or list or tuple
  :return: output of the command
  :rtype: str
  """
  shell_cmd = ['/bin/sh', '-c']
  if isinstance(cmd, basestring):
    shell_cmd.append(cmd)
  elif isinstance(cmd, (list, tuple)):
    shell_cmd.append(' '.join(cmd))
  return Popen(shell_cmd, stdout=PIPE, stderr=STDOUT).communicate()[0]


def enum (*sequential, **named):
  """
  Helper function to define enumeration. E.g.:

    >>> Numbers = enum(ONE=1, TWO=2, THREE='three')
    >>> Numbers = enum('ZERO', 'ONE', 'TWO')
    >>> Numbers.ONE
    1
    >>> Numbers.reversed[2]
    'TWO'

  :param sequential: support automatic enumeration
  :type sequential: str
  :param named: support definition with unique keys
  :type named: dict
  :return: Enum object
  :rtype: dict
  """
  enums = dict(zip(sequential, range(len(sequential))), **named)
  enums['reversed'] = dict((value, key) for key, value in enums.iteritems())
  return type('enum', (), enums)


def quit_with_error (msg, logger=None, exception=None):
  """
  Helper function for quitting in case of an error.

  :param msg: error message
  :type msg: str
  :param logger: logger name or logger object (default: core)
  :type logger: str or :any:`logging.Logger`
  :param exception: print stacktrace before quit (default: None)
  :type exception: :any:`exceptions.Exception`
  :return: None
  """
  from pox.core import core
  if isinstance(logger, str):
    logger = core.getLogger(logger)
  elif not isinstance(logger, logging.Logger):
    logger = core.getLogger("core")
  logger.fatal(msg)
  if exception:
    logger.exception("Caught exception: %s" % exception)
  core.quit()
  os._exit(1)


def quit_with_ok (msg=None, logger=None):
  """
  Helper function for quitting in case of an error.

  :param msg: exit message
  :type msg: str
  :param logger: logger name or logger object (default: core)
  :type logger: str or :any:`logging.Logger`
  :return: None
  """
  from pox.core import core
  if isinstance(logger, str):
    logger = core.getLogger(logger)
  elif not isinstance(logger, logging.Logger):
    logger = core.getLogger("core")
  logger.info(msg if msg else "Exiting from ESCAPE...")
  core.quit()


def set_global_parameter (name, value):
  """
  Set the given parameter globally based on the `core` object of POX.

  Use the :any:`get_global_parameter`

  :param name: global parameter name
  :type name: str or int
  :param value: parameter value
  :type value: object
  :return: None
  """
  from pox.core import core
  setattr(core, name, value)


def get_global_parameter (name):
  """
  Return with the value of the given parameter which has been set by
  :any`set_global_parameter` else None.

  :param name: global parameter name
  :type name: str or int
  :return: parameter value
  :rtype: object
  """
  from pox.core import core
  return getattr(core, name, None)


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
    :return: None
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
    """
    Override.
    """
    if cls not in cls._instances:
      cls._instances[cls] = super(Singleton, cls).__call__(*args)
    return cls._instances[cls]


def deprecated (func):
  """
  This is a decorator which can be used to mark functions as deprecated. It
  will result in a warning being emitted when the function is used.

  :param func: original function
  :type func: :any:`collections.Callable`
  :return: decorated func
  :rtype: :any:`collections.Callable`
  """

  def newFunc (*args, **kwargs):
    warnings.warn("Call to deprecated function %s." % func.__name__,
                  category=DeprecationWarning, stacklevel=2)
    return func(*args, **kwargs)

  newFunc.__name__ = func.__name__
  newFunc.__doc__ = func.__doc__
  newFunc.__dict__.update(func.__dict__)
  return newFunc


def remove_junks_at_shutdown (log=logging.getLogger("cleanup")):
  """
  Remove junk files used/created by ESCAPE.

  :param log: optional logger
  :type log: :any:`logging.Logger`
  :return: None
  """
  if os.geteuid() != 0:
    log.error("Cleanup process requires root privilege!")
    return
  log.debug("Remove SAP names from /etc/hosts...")
  # Reset /etc/hosts file
  os.system("sed '/# BEGIN ESCAPE SAPS/,/# END ESCAPE SAPS/d' "
            "/etc/hosts > /etc/hosts2")
  os.system("mv /etc/hosts2 /etc/hosts")
  log.debug("Cleanup still running VNF-related processes...")
  # Kill remained clickhelper.py/click
  run_cmd(r"sudo pkill -9 -f netconfd")
  run_cmd(r"sudo pkill -9 -f clickhelper")
  run_cmd(r"sudo pkill -9 -f click")
  log.debug("Delete any remained veth pair...")
  veths = run_cmd(r"ip link show | egrep -o '(uny_\w+)'").split('\n')
  # only need to del one end of the veth pair
  for veth in veths[::2]:
    if veth != '':
      run_cmd(r"sudo ip link del %s" % veth)
  log.debug("Remove remained xterms and stacked netconfd sockets...")
  run_cmd("sudo pkill -f '%s'" % 'xterm -title "SAP')
  # os.system("sudo pkill -f 'xterm -title SAP'")
  log.debug("Cleanup any Mininet-specific junk...")
  # Call Mininet's own cleanup stuff
  from mininet.clean import cleanup
  cleanup()


def remove_junks_at_boot (log=logging.getLogger("cleanup")):
  """
  Remove junk files used/created by ESCAPE.

  :param log: optional logger
  :type log: :any:`logging.Logger`
  :return: None
  """
  if os.geteuid() != 0:
    log.error("Cleanup process requires root privilege!")
    return
  log.debug("Remove remained log files of VNF, agent and netconfd instances "
            "from previous run...")
  log.debug("Remove trails...")
  trails = os.getcwd() + "/log/trails"
  if os.path.exists(trails):
    for f in os.listdir(os.getcwd() + "/log/trails"):
      if f != ".placeholder":
        os.remove(os.path.join(os.getcwd(), "log/trails", f))
  run_cmd('rm -f /tmp/*.log')
  for f in os.listdir('/tmp'):
    if re.search('.*-startup-cfg.xml|ncxserver_.*', f):
      os.remove(os.path.join('/tmp/', f))


def get_ifaces ():
  """
  Return the list of all defined interface. Rely on 'ifconfig' command.

  :return: list of interfaces
  :rtype: list
  """
  return [iface.split(' ', 1)[0] for iface in os.popen('ifconfig -a -s') if
          not iface.startswith('Iface')]


def get_escape_version ():
  """
  Return the current ESCAPE version based on ``git describe``
  in format: version-revision where version is the last found tag and revision
  is the number of commits following the tag.

  :return: version in format: vmajor.minor.patch[-revision-commit]
  :rtype: str
  """
  # Only match version tag like v2.0.0
  # cmd = "git describe --always --first-parent --tags --match v*"
  with open(os.devnull, 'wb') as DEVNULL:
    desc = Popen("git describe --always --tags",
                 stdout=PIPE,
                 stderr=DEVNULL,
                 shell=True).communicate()[0].strip()
  # If Git is not installed or command is failed
  if not desc:
    from escape import __version__
    return __version__
  else:
    # If no tag is defined in the repo
    if not desc.count('-'):
      return "2.0.0-%s" % desc
    else:
      return desc


def get_escape_branch_name ():
  """
  Return the current branch name.

  :return: current branch
  :rtype: str
  """
  with open(os.devnull, 'wb') as DEVNULL:
    branch = Popen("git symbolic-ref --short HEAD",
                   stdout=PIPE,
                   stderr=DEVNULL,
                   shell=True).communicate()[0]
  return branch.strip() if branch else "N/A"


def get_escape_revision ():
  """
  Return the initiation message for the current ESCAPE version.
  Acquiring information from escape package.

  :return: name and version
  :rtype: tuple
  """
  import escape
  return escape.__project__, get_escape_version(), get_escape_branch_name()


def notify_remote_visualizer (data, url=None, **kwargs):
  """
  Send the given data to a remote visualization server.
  If url is given use this address to send instead of the url defined in the
  global config.

  :param data: data need to send
  :type data: :class:`NFFG` or Virtualizer
  :param id: id of the data, needs for the remote server
  :type id: str
  :param url: additional URL (acquired from config by default)
  :type url: str
  :param kwargs: optional parameters for request lib
  :type kwargs: dict
  :return: response
  :rtype: str
  """
  from pox.core import core
  if core.hasComponent('visualizer'):
    return core.visualizer.send_notification(data=data, url=url, **kwargs)


def do_profile (func):
  """
  Decorator to profile a function.

  :param func: decorated function
  :return: result of the decorated function
  """

  def decorator_func (*args, **kwargs):
    """
    Decorator function.

    :return: tuple of the result of decorated function and statistics as str
    :rtype: tuple
    """
    profile = cProfile.Profile(builtins=False)
    profile.enable()
    try:
      result = func(*args, **kwargs)
    finally:
      profile.disable()
    profile.create_stats()
    with io.BytesIO() as stat:
      pstats.Stats(profile, stream=stat).sort_stats('cumulative').print_stats()
      ret = stat.getvalue()
    return result, ret

  return decorator_func


def unicode_to_str (raw):
  """
  Converter function to avoid unicode.

  :param raw: raw data from
  :return: converted data
  """
  if isinstance(raw, dict):
    return {unicode_to_str(key): unicode_to_str(value) for key, value in
            raw.iteritems()}
  elif isinstance(raw, list):
    return [unicode_to_str(element) for element in raw]
  elif isinstance(raw, unicode):
    return raw.encode('utf-8').replace(' ', '_')
  else:
    return raw


def remove_units (raw):
  """
  Remove units from resource values.

  :param raw: raw resource value
  :type raw: str
  :return: resource value
  :rtype: int
  """
  return filter(lambda x: x.isdigit(), raw)


def check_service_status (name):
  """
  Return if a Linux process given by ``name`` is running or not.

  :param name: process name
  :type name: str
  :return: process is running or not
  :rtype: bool
  """
  status_all = run_cmd("sudo service --status-all")
  for line in status_all.splitlines():
    status, service = line.split(']')
    if name == service.strip():
      if "+" in status:
        return True
      else:
        return False
  return False


def port_tester (host, port, interval=1, period=5,
                 log=logging.getLogger("port_tester")):
  """
  Test the given port with the interval (in sec) until the attempts reach the
  given period.

  :param host: host
  :type host: str
  :param port: port number
  :type port: int
  :param interval: delay betwwen the attempts
  :type interval: int
  :param period: number of checks
  :type period: int
  :param log: additional log object
  :return: port is open or not
  :rtype: bool
  """
  log.debug(
    "Testing port: %s on host: %s with interval: %ss" % (host, port, interval))
  for i in xrange(1, period):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
      s.connect((socket.gethostbyname(host), port))
      log.log(VERBOSE, "Port open: %s!" % port)
      return True
    except socket.error:
      log.log(VERBOSE, "Attempt: %s - Port closed!" % i)
      s.close()
      time.sleep(interval)
  return False
