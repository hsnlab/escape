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
Contains functionality related to policy enforcement.
"""
import repr
from functools import wraps

import escape.orchest.virtualization_mgmt
from escape.orchest import log as log


class PolicyEnforcementError(RuntimeError):
  """
  Exception class to signal policy enforcement error.
  """
  pass


class PolicyEnforcementMetaClass(type):
  """
  Meta class for handling policy enforcement in the context of classes inherited
  from :class:`AbstractVirtualizer
  <escape.orchest.virtualization_mgmt.AbstractVirtualizer>`.

  If the :class:`PolicyEnforcement` class contains a function which name
  matches one in the actual Virtualizer then PolicyEnforcement's function will
  be called first.

  .. warning::
    Therefore the function names must be identical!

  .. note::

    If policy checking fails a :class:`PolicyEnforcementError` should be
    raised and handled in a higher layer..

  To use policy checking set the following class attribute::

    __metaclass__ = PolicyEnforcementMetaClass
  """

  def __new__ (mcs, name, bases, attrs):
    """
    Magic function called before subordinated class even created

    :param name: given class name
    :type name: str
    :param bases: bases of the class
    :type bases: tuple
    :param attrs: given attributes
    :type attrs: dict
    :return: inferred class instance
    :rtype: AbstractVirtualizer
    """
    # Check Virtualizer methods
    for attr_name, attr_value in attrs.iteritems():
      # if non-private and callable
      if not attr_name.startswith('_') and callable(attr_value):
        # Get policy checking functions from PolicyEnforcement
        hooks = (getattr(PolicyEnforcement, "pre_" + attr_name, None),
                 getattr(PolicyEnforcement, "post_" + attr_name, None))
        # if pre and/or post hook is defined set a wrapper
        if any(hooks):
          attrs[attr_name] = mcs.get_wrapper(attr_value, hooks)

    return super(PolicyEnforcementMetaClass, mcs).__new__(mcs, name, bases,
                                                          attrs)

  @classmethod
  def get_wrapper (mcs, orig_func, hooks):
    """
    Return a decorator function which do the policy enforcement check.

    :param orig_func: original function
    :type orig_func: func
    :param hooks: tuple of pre and post checking functions
    :type hooks: tuple
    :raise: PolicyEnforcementError
    :return: decorator function
    :rtype: func
    """

    @wraps(orig_func)
    def wrapper (*args, **kwargs):
      """
      Wrapper function which call policy checking functions if they exist.
      """
      if len(args) > 0:
        if isinstance(args[0],
                      escape.orchest.virtualization_mgmt.AbstractVirtualizer):
          # Call Policy checking function before original
          if hooks[0]:
            log.debug("Invoke Policy checking function: [PRE] %s" % (
              hooks[0].__name__.split('pre_', 1)[1]))
            hooks[0](args, kwargs)
          # Call original function
          ret_value = orig_func(*args, **kwargs)
          # Call Policy checking function after original
          if hooks[1]:
            log.debug("Invoke Policy checking function: [POST] %s" % (
              hooks[1].__name__.split('post_', 1)[1]))
            hooks[1](args, kwargs, ret_value)
          return ret_value
        else:
          log.warning(
            "Binder class of policy checker function is not a subclass of "
            "AbstractVirtualizer!")
      else:
        log.warning("Something went wrong during binding Policy checker!")
      log.error("Abort policy enforcement checking!")
      raise PolicyEnforcementError("Policy enforcement checking is aborted")

    return wrapper


class PolicyEnforcement(object):
  """
  Proxy class for policy checking.

  Contains the policy checking function.

  Binding is based on function name (checking function have to exist in this
  class and its name have to stand for the `pre_` or `post_` prefix and the
  name of the checked function).

  .. warning::
    Every PRE policy checking function is classmethod and need to have two
    parameter for nameless (args) and named(kwargs) params:

  Example::

    def pre_sanity_check (cls, args, kwargs):

  .. warning::
    Every POST policy checking function is classmethod and need to have three
    parameter for nameless (args), named (kwargs) params and return value:

  Example::

    def post_sanity_check (cls, args, kwargs, ret_value):

  .. note::
    The first element of args is the supervised Virtualizer ('self' param in the
    original function)
  """

  def __init__ (self):
    """
    Init
    """
    super(PolicyEnforcement, self).__init__()

  @classmethod
  def pre_sanity_check (cls, args, kwargs):
    """
    Implements the the sanity check before virtualizer's sanity check is called.

    :param args: original nameless arguments
    :type args: tuple
    :param kwargs: original named arguments
    :type kwargs: dict
    :return: None
    """
    virtualizer = args[0]
    nffg = args[1]
    # TODO - implement
    log.debug("PolicyEnforcement: sanity_check NFFG(%s) <--> %s [OK]" % (
      nffg, repr.repr(virtualizer)))

  @classmethod
  def post_sanity_check (cls, args, kwargs, ret_value):
    """
    Implements the the sanity check after virtualizer's sanity check is called.

    :param args: original nameless arguments
    :type args: tuple
    :param kwargs: original named arguments
    :type kwargs: dict
    :param ret_value: return value of Virtualizer's policy check function
    :return: None
    """
    virtualizer = args[0]
    nffg = args[1]
    # TODO - implement
    log.debug("PolicyEnforcement: sanity_check NFFG(%s) <--> %s [OK]" % (
      nffg, repr.repr(virtualizer)))
