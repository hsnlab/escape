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
from pox.core import core


def schedule_as_coop_task (func):
  """
  Decorator fuctions for running functions in an asynchronous way as a
  microtask in recoco's cooperative multitasking context (in wich POX was
  written)
  """

  def decorator (*args, **kwargs):
    # Use POX internal thread-safe wrapper for scheduling
    core.callLater(func, *args, **kwargs)

  return decorator
