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
Contains miscellaneous helper functions
"""
from functools import wraps
import importlib
import weakref

from pox.core import core
from pox.lib.revent.revent import EventMixin
from escape.service import LAYER_NAME as SERVICE
from escape.orchest import LAYER_NAME as ORCHEST
from escape.adapt import LAYER_NAME as ADAPT
from escape.infr import LAYER_NAME as INFR


def schedule_as_coop_task (func):
  """
  Decorator functions for running functions in an asynchronous way as a
  microtask in recoco's cooperative multitasking context (in which POX was
  written)

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
  Schedule a coop microtask and run the given function with parameters in it

  Use POX core logic directly

  :param func: function need to run
  :type func: func
  :param args: nameless arguments
  :type args: tuple
  :param kwargs: named arguments
  :type kwargs: dict
  :return: None
  """
  core.callLater(func, *args, **kwargs)


class SimpleStandaloneHelper(object):
  """
  Helper class for layer APIs to catch events and handle these in separate
  handler functions
  """

  def __init__ (self, container, cover_name):
    """
    Init

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
    Register event listeners

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
    Log given event

    :param event: Event object which need to be logged
    :type event: Event
    :return: None
    """
    core.getLogger("StandaloneHelper").getChild(self._cover_name).info(
      "Got event: %s from %s Layer" % (
        event.__class__.__name__, str(event.source._core_name).title()))


def enum (*sequential, **named):
  """
  Helper function to define enumeration. E.g.:

  .. code-block:: python

    >>> Numbers = enum(ONE=1, TWO=2, THREE='three')
    >>> Numbers = enum('ZERO', 'ONE', 'TWO')
    >>> Numbers.ONE
    1
    >>> Numbers.reversed[2]
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


def quit_with_error (msg=None, logger="core"):
  """
  Helper function for quitting in case of an error

  :param msg: error message (optional)
  :type msg: str
  :param logger: logger name (default: core)
  :type logger: str
  :return: None
  """
  from pox.core import core
  import sys

  if msg:
    core.getLogger(logger).fatal(str(msg))
  core.quit()
  sys.exit(1)


class ESCAPEConfig(object):
  """
  Wrapper class for configuration to hide specialies with respect to storing,
  loading, parging and getting special data.

  Contains functions for config handling and manipulation.

  Should be instantiated once!
  """

  LAYERS = (SERVICE, ORCHEST, ADAPT, INFR)

  def __init__ (self, default=None):
    """
    Init configuration from given data or an empty dict

    :param default: default configuration
    :type default: dict
    """
    self.__configuration = default if default else dict.fromkeys(self.LAYERS,
                                                                 {})

  def add_cfg (self, cfg):
    """
    Override configuration

    :param cfg: new configuration
    :type cfg: dict
    :return: None
    """
    if isinstance(cfg, dict) and cfg:
      self.__configuration = cfg

  def load_config (self, config="escape.config"):
    """
    Load static configuration from file if it exist or leave the default intact.

    .. note::
      The CONFIG is updated per data under the Layer entries. This means that
      the
      minimal amount of data have to given is the hole sequence or collection
      unter the appropriate key. E.g. the hole data under the 'STRATEGY' key in
      'orchestration' layer.

    :param config: config file name relative to pox.py (optional)
    :type config: str
    :return: self
    :rtype: :class:`ESCAPEConfig`
    """
    from pox.core import log

    try:
      with open(config, 'r') as f:
        import json

        cfg = json.load(f)
        # Minimal syntax checking
        changed = []
        if len(cfg) > 0:
          for layer in self.__configuration:
            if layer in cfg.keys() and len(cfg[layer]) > 0:
              self.__configuration[layer].update(cfg[layer])
              changed.append(layer)
        if changed:
          log.info("Part(s) of running configuration has been loaded: %s",
                   changed)
          return self
    except IOError:
      log.debug("Additional configuration file not found:")
    except ValueError as e:
      log.error("An error occured when load configuration: %s" % e.message)
    log.info("Using default configuration...")
    return self

  def dump (self):
    """
    Return with the entire configuration in JSON.

    :return: config
    :rtype: str
    """
    import json

    return json.dumps(self.__configuration)

  def is_loaded (self, layer):
    """
    Return the value given UNIFY's layer is loaded or not.

    :param layer: layer name
    :type layer: str
    :return: layer condition
    :rtype: bool
    """
    return self.__configuration[layer].get('LOADED', False)

  def set_loaded (self, layer):
    """
    Set the given layer LOADED value.

    :param layer: layer name
    :type layer: str
    :return: None
    """
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

  def get_domain_component (self, component):
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
