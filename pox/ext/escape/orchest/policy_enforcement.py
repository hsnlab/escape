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

from escape.orchest import LAYER_NAME
import pox.core as core


log = core.getLogger(LAYER_NAME)


class PolicyEnforcementError(object):
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
    for attr_name, attr_value in attrs.iteritems():
      if isinstance(attr_value,
                    types.FunctionType) and not attr_name.startswith('__'):
        if hasattr(PolicyEnforcement, attr_name):
          attrs[attr_name] = mcs.get_wrapper(attr_name, attr_value)

    return super(PolicyEnforcementMetaClass, mcs).__new__(mcs, name, bases,
                                                          attrs)

  @classmethod
  def get_wrapper (mcs, func_name, orig_func):
    def wrapper (*args, **kwargs):
      pep_function = getattr(PolicyEnforcement(), func_name)
      # Call Policy checking function before original
      log.debug("Invoke Policy checking function for: " + func_name)
      if pep_function():
        return orig_func(*args, **kwargs)
      # Do nothing after the original function called
      return None

    return wrapper


class PolicyEnforcement(object):
  """
  Proxy class for policy checking
  """

  def __init__ (self):
    super(PolicyEnforcement, self).__init__()

  def test_func (self):
    """
    Test function for policy checking debug. Should be removed soon.
    """
    print 'Policy Enforcement test_func OK'
    return True