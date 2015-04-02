# Copyright 2015 Janos Czentye
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
import types

from escape.orchest import log as log
import escape.orchest.virtualization_management


class PolicyEnforcementError(RuntimeError):
  """
  Exception class to signal policy enforcement error
  """
  pass


class PolicyEnforcementMetaClass(type):
  """
  Meta class for handling policy enforcement in the context of classes inhereted
  from AbstractVirtualizer

  If the PolicyEnforcement class contains a function which name matches one in
  the actual Virtualizer then PolicyEnforcement's function will be called first
  Therefore the function names must be identical!
  If the policy checking function retuns with True value, the original function
  will be called next.

  If policy checking fails a PolicyEnforcementError should be raised and handled
  in a higher layer or/and at least return with False value.

  To use policy checking set the following class attribute:

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
    for attr_name, attr_value in attrs.iteritems():
      if isinstance(attr_value,
          types.FunctionType) and not attr_name.startswith('__'):
        if hasattr(PolicyEnforcement, attr_name):
          attrs[attr_name] = mcs.get_wrapper(attr_name, attr_value)

    return super(PolicyEnforcementMetaClass, mcs).__new__(mcs, name, bases,
      attrs)

  @classmethod
  def get_wrapper (mcs, func_name, orig_func):
    """
    Return decorator function which do the policy enforment check

    :param func_name: function name
    :type func_name: str
    :param orig_func: original function
    :type orig_func: func
    :raise: PolicyEnforcementError
    :return: decorator function
    :rtype: func
    """

    def wrapper (*args, **kwargs):
      # existence of PEP function is checked before
      pep_function = getattr(PolicyEnforcement, func_name)
      log.debug("Invoke Policy checking function for %s" % func_name)
      if len(args) > 0:
        if isinstance(args[0],
            escape.orchest.virtualization_management.AbstractVirtualizer):
          # Call Policy checking function before original
          if pep_function(args, kwargs):
            return orig_func(*args, **kwargs)
            # Do nothing after the original function called
        else:
          log.warning(
            "Binder class of policy checker function is not a subclass of "
            "ESCAPEVirtualizer!")
      else:
        log.warning("Something went wrong during binding Policy checker!")
      log.error("Abort policy enforcement checking!")
      raise PolicyEnforcementError("Policy enforcement checking is aborted")

    return wrapper


class PolicyEnforcement(object):
  """
  Proxy class for policy checking

  Contains the policy checking function

  Binding is based on function name (cheking function have to exist in this
  class and tis name have to be identical to subordinate function's name)

  Every policy checking function is classmethod and need to have two parameter
  for nameless (args) and named(kwargs) params.
  The first element of args is the supervised Virtualizer ('self' param in the
  original function)
  """

  def __init__ (self):
    """
    Init
    """
    super(PolicyEnforcement, self).__init__()

  @classmethod
  def get_resource_info (cls, args, kwargs):
    virtualizer = args[0]
    # TODO - implement
    log.debug("PolicyEnforcement: check get_resource_info [OK]")
    return True

  @classmethod
  def sanity_check (cls, args, kwargs):
    virtualizer = args[0]
    nffg = kwargs['nffg']
    # TODO - implement
    log.debug("PolicyEnforcement: check NF-FG(%s) <--> %s [OK]" % (
      nffg.id, virtualizer))
    return True