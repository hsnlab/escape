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

:func:`schedule_as_coop_task()` helps invoking a function in POX's cooperative
microtask environment

:func:`call_as_coop_task()` hides POC core functionality and schedule a
function in
the coop microtask environment directly

:class:`SimpleStandaloneHelper` is a helper class for mimic a minimal layer
API as a
dependency for other layer APIs to handles events
"""
from functools import wraps
import weakref

from pox.core import core
from pox.lib.revent.revent import EventMixin


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
    if isinstance(container, EventMixin):
      self._container = weakref.proxy(container)
      self._cover_name = cover_name
    else:
      raise TypeError("container is not subclass of EventMixin")
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