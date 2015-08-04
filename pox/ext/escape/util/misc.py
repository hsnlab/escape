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
import copy
from distutils.util import strtobool
from functools import wraps
import importlib
import json
import logging
import os
from subprocess import check_call, STDOUT, Popen, PIPE
import weakref

from mininet.clean import cleanup
from pox.core import core, log
from pox.lib.revent.revent import EventMixin
from escape.service import LAYER_NAME as SERVICE
from escape.orchest import LAYER_NAME as ORCHEST
from escape.adapt import LAYER_NAME as ADAPT
from escape.infr import LAYER_NAME as INFR


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
  core.callLater(func, *args, **kwargs)


def run_silent (*cmd):
  """
  Run the given shell command silent.

  :param cmd: command as a list
  :type cmd: list
  :return: return code of the subprocess call
  :rtype: int
  """
  DEVNULL = open(os.devnull, 'wb')
  return check_call(cmd, stdout=DEVNULL, stderr=STDOUT, close_fds=True)


def cleanup_after_ESCAPE ():
  """
  Do cleanup steps.

  :return: None
  """
  # Kill remained clickhelper.py/click
  run_silent("sudo", "pkill", "click")
  # Remove remained veth pairs used in EE
  veths = Popen(['/bin/sh', '-c', r"ip link show | egrep -o '(uny_\w+)'"],
                stdout=PIPE).communicate()[0].split('\n')
  print veths
  # only need to del one end of the veth pair
  for veth in veths[::2]:
    if veth != '':
      run_silent("sudo", "ip", "link", "del", veth)
  # Call Mininet's own cleanup stuff
  cleanup()


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
    core.getLogger("StandaloneHelper").getChild(self._cover_name).info(
      "Got event: %s from %s Layer" % (
        event.__class__.__name__, str(event.source._core_name).title()))


class Singleton(type):
  """
  Metaclass for classes need to be created only once.

  Realize Singleton design pattern in a pythonic way.
  """
  _instances = {}

  def __call__ (cls, *args, **kwargs):
    if cls not in cls._instances:
      cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
    return cls._instances[cls]


class ESCAPEConfig(object):
  """
  Wrapper class for configuration to hide specialties with respect to storing,
  loading, parsing and getting special data.

  Contains functions for config handling and manipulation.

  Should be instantiated once!
  """
  # Singleton
  __metaclass__ = Singleton
  # Predefined layer names
  LAYERS = (SERVICE, ORCHEST, ADAPT, INFR)
  # Default additional config name
  DEFAULT_CFG = "additional-config-file"

  def __init__ (self, default=None):
    """
    Init configuration from given data or an empty dict.

    :param default: default configuration
    :type default: dict
    """
    self.__configuration = default if default else dict.fromkeys(self.LAYERS,
                                                                 {})
    self.loaded = False

  def add_cfg (self, cfg):
    """
    Override configuration.

    :param cfg: new configuration
    :type cfg: dict
    :return: None
    """
    if isinstance(cfg, dict) and cfg:
      self.__configuration = cfg

  def load_config (self, config=None):
    """
    Load static configuration from file if it exist or leave the default intact.

    .. note::
      The CONFIG is updated per data under the Layer entries. This means that
      the minimal amount of data have to given is the hole sequence or
      collection under the appropriate key. E.g. the hole data under the
      'STRATEGY' key in 'orchestration' layer.

    :param config: config file name relative to pox.py (optional)
    :type config: str
    :return: self
    :rtype: :class:`ESCAPEConfig`
    """
    if config:
      # Config is set directly
      log.info(
        "Load explicitly given config file: %s" % os.path.basename(config))
    elif hasattr(core, "config_file_name"):
      # Config is set through POX's core object by a topmost module (unify)
      config = getattr(core, "config_file_name")
      log.info(
        "Load explicitly given config file: %s" % os.path.basename(config))
    else:
      # Detect default config
      config = os.path.abspath(
        os.path.dirname(__file__) + "../../../../" + self.__configuration[
          self.DEFAULT_CFG])
      log.debug("Load default config file: %s" % os.path.basename(config))
    try:
      # Load file
      with open(os.path.abspath(config), 'r') as f:
        cfg = json.load(f)
      # Iterate over layer config
      changed = False
      for layer in cfg:
        if layer in self.__configuration:
          if self.__parse_part(self.__configuration[layer], cfg[layer]):
            changed = True
        else:
          log.warning(
            "Unidentified layer name in loaded configuration: %s" % layer)
      if changed:
        log.info("Part(s) of running configuration has been updated!")
        return self
    except IOError as e:
      log.debug("Additional configuration file not found: %s" % config)
    except ValueError as e:
      log.error("An error occurred when load configuration: %s" % e)
    finally:
      # Register config into pox.core to be reachable for other future
      # components -not used currently
      self.loaded = True
      core.register("CONFIG", self)
    log.info("No change during config update! Using default configuration...")
    return self

  def __parse_part (self, inner_part, loaded_part):
    """
    Inner function to parse and check a part of configuration and update the
    stored one according the detected changes.
    Uses recursion.

    :param inner_part: part of inner representation of config (CONFIG)
    :type inner_part: dict
    :param loaded_part: part of loaded configuration (escape.config)
    :type loaded_part: dict
    :return: original config is changed or not.
    :rtype: bool
    """
    changed = False
    # If parsed part is not None or empty dict/tuple/list
    if loaded_part:
      # Iterating over the structure
      for key, value in loaded_part.iteritems():
        # If the loaded value is a dict
        if isinstance(value, dict):
          # If we need to check deeper
          if key in inner_part:
            # Recursion
            changed = self.__parse_part(inner_part[key], value)
          # If no entry in CONFIG just copying
          else:
            inner_part[key] = value
            # Config updated
            changed = True
        # If the loaded value is a str/tuple/list
        else:
          # If there is a default value for this key
          if key in inner_part:
            # If it is not the same
            if isinstance(value, (tuple, list)):
              if not set(inner_part[key]) & set(value):
                # Config overrided
                inner_part[key] = value
                changed = True
            else:
              if inner_part[key] != value:
                # Config overrided
                inner_part[key] = value
                changed = True
          else:
            # Config updated
            inner_part[key] = value
            changed = True
    return changed

  def dump (self):
    """
    Return with the entire configuration in JSON.

    :return: config
    :rtype: str
    """
    import json

    print json.dumps(self.__configuration, indent=4)

  def is_layer_loaded (self, layer):
    """
    Return the value given UNIFY's layer is loaded or not.

    :param layer: layer name
    :type layer: str
    :return: layer condition
    :rtype: bool
    """
    return self.__configuration[layer].get('LOADED', False)

  def set_layer_loaded (self, layer):
    """
    Set the given layer LOADED value.

    :param layer: layer name
    :type layer: str
    :return: None
    """
    if not self.loaded:
      self.load_config()
    self.__configuration[layer]['LOADED'] = True

  def __getitem__ (self, item):
    """
    Can be used the config as a dictionary: CONFIG[...]

    :param item: layer key
    :type item: str
    :return: layer config
    :rtype: dict
    """
    if not isinstance(item, str):
      raise TypeError("Unsupported operand type: Layer name must be str")
    elif item not in self.LAYERS:
      raise KeyError("No layer is defined with the name: %s" % item)
    else:
      return self.__configuration[item]

  def __setitem__ (self, key, value):
    """
    Disable explicit layer config modification.
    """
    raise RuntimeError("Explicit layer config modification is not supported!")

  def __delitem__ (self, key):
    """
    Disable explicit layer config deletion.
    """
    raise RuntimeError("Explicit layer config deletion is not supported!")

  ##############################################################################
  # Helper functions
  ##############################################################################

  def get_strategy (self, layer):
    """
    Return with the Strategy class of the given layer.

    :param layer: layer name
    :type layer: str
    :return: Strategy class
    :rtype: :any:`AbstractMappingStrategy`
    """
    try:
      return getattr(importlib.import_module(
        self.__configuration[layer]['STRATEGY']['module']),
        self.__configuration[layer]['STRATEGY']['class'], None)
    except (KeyError, AttributeError):
      return None

  def get_mapper (self, layer):
    """
    Return with th Mapper class of the given layer.

    :param layer: layer name
    :type layer: str
    :return: Mapper class
    :rtype: :any:`AbstractMapper`
    """
    try:
      return getattr(importlib.import_module(
        self.__configuration[layer]['MAPPER']['module']),
        self.__configuration[layer]['MAPPER']['class'], None)
    except (KeyError, AttributeError):
      return None

  def get_threaded (self, layer):
    """
    Return with the value if the mapping strategy is needed to run in
    separated thread or not. If value is not defined: return False.

    :param layer: layer name
    :type layer: str
    :return: threading value
    :rtype: bool
    """
    try:
      return self.__configuration[layer]['STRATEGY']['THREADED']
    except KeyError:
      return False

  def get_component (self, component):
    """
    Return with the class of the adaptation component.

    :param component: component name
    :type component: str
    :return: component class
    """
    try:
      return getattr(importlib.import_module(
        self.__configuration[ADAPT][component]['module']),
        self.__configuration[ADAPT][component]['class'], None)
    except KeyError:
      return None

  def get_component_params (self, component):
    """
    Return with the initial parameters of the given component defined in CONFIG.
    The param's name must be identical with the attribute name of the component
    constructor.

    :param component: component name
    :type component: str
    :return: initial params
    :rtype: dict
    """
    params = copy.deepcopy(self.__configuration[ADAPT][component])
    del params['module']
    del params['class']
    return params

  def get_default_mgrs (self):
    """
    Return the default DomainManagers for initialization on start.

    :return: list of :any:`AbstractDomainManager`
    :rtype: list
    """
    try:
      return self.__configuration[ADAPT]['DEFAULTS']
    except KeyError:
      return ()

  def get_mininet_topology (self):
    """
    Return the Mininet topology class.

    :return:  topo class
    """
    try:
      # Project root dir relative to this module which is/must be under pox/ext
      return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..",
                                          self.__configuration[INFR]["TOPO"]))
    except KeyError:
      return None

  def get_fallback_topology (self):
    """
    Return the fallback topology class.

    :return: fallback topo class
    :rtype: :any::`AbstractTopology`
    """
    try:
      return getattr(importlib.import_module(
        self.__configuration[INFR]["FALLBACK-TOPO"]['module']),
        self.__configuration[INFR]["FALLBACK-TOPO"]['class'], None)
    except KeyError:
      return None

  def get_clean_after_shutdown (self):
    """
    Return with the value if a cleaning process need to be done or not.

    :return: cleanup (default: False)
    :rtype: bool
    """
    try:
      return strtobool(str(self.__configuration[INFR]['SHUTDOWN-CLEAN']))
    except KeyError:
      return False

  def get_ros_agent_class (self):
    """
    Return with the request handler class of Agent REST API.

    :return: agent class
    :rtype: :any:`AbstractRequestHandler`
    """
    try:
      return getattr(importlib.import_module(
        self.__configuration[ORCHEST]["AGENT"]['module']),
        self.__configuration[ORCHEST]["AGENT"]['class'], None)
    except KeyError:
      return None

  def get_ros_agent_prefix (self):
    """
    Return the REST API prefix for agent request handler.

    :return: prefix
    :rtype: str
    """
    try:
      return self.__configuration[ORCHEST]["AGENT"]['prefix']
    except KeyError:
      return None

  def get_ros_agent_address (self):
    """
    Return the REST API (address, port) for agent REST server.

    :return: address and port
    :rtype: tuple
    """
    try:
      return (self.__configuration[ORCHEST]["AGENT"]['address'],
              self.__configuration[ORCHEST]["AGENT"]['port'])
    except KeyError:
      return None

  def get_sas_api_class (self):
    """
    Return with the request handler class of Service Layer REST API.

    :return: REST API class
    :rtype: :any:`AbstractRequestHandler`
    """
    try:
      return getattr(importlib.import_module(
        self.__configuration[SERVICE]["REST-API"]['module']),
        self.__configuration[SERVICE]["REST-API"]['class'], None)
    except KeyError:
      return None

  def get_sas_api_prefix (self):
    """
    Return the REST API prefix for Service Layer request handler.

    :return: prefix
    :rtype: str
    """
    try:
      return self.__configuration[SERVICE]["REST-API"]['prefix']
    except KeyError:
      return None

  def get_sas_api_address (self):
    """
    Return the REST API (address, port) for Service Layer REST server.

    :return: address and port
    :rtype: tuple
    """
    try:
      return (self.__configuration[SERVICE]["REST-API"]['address'],
              self.__configuration[SERVICE]["REST-API"]['port'])
    except KeyError:
      return None
