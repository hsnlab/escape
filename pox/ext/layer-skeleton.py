# Copyright 2013 <Your Name Here>
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
ESCAPEv2 layer skeleton
"""
from escape.util.api import AbstractAPI

from pox.core import core
import pox.lib.util as poxutil

# Initial parameters
init_param = {}


# noinspection PyUnusedLocal
class SkeletonAPI(AbstractAPI):
  def __init__ (self, standalone=False, **kwargs):
    super(SkeletonAPI, self).__init__(standalone=standalone, **kwargs)

  def initialize (self):
    # Init here
    pass

  # Define API functions here
  def unique_API_fuction (self):
    pass


def _start_layer (event):
  # Instantiate the API class and register into pox.core only once
  pass
  # Wait for the necessery POX component until they are resolved and set up
  # event handlers.
  SkeletonAPI(**init_param)


@poxutil.eval_args
def launch ():
  global init_param
  init_param.update(locals())
  core.addListenerByName("UpEvent", _start_layer)
