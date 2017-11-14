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
from escape.api import LAYER_NAME, log
from escape.util.api import AbstractAPI


class RestInterfaceAPI(AbstractAPI):
  """
  Entry point for REST-API.
  """

  _core_name = LAYER_NAME

  def __init__ (self, standalone=False, **kwargs):
    log.info("Starting REST-API Sublayer...")
    super(RestInterfaceAPI, self).__init__(standalone, **kwargs)

  def initialize(self):
    pass

  def post_up_hook(self, event):
    pass

  def shutdown(self, event):
    pass

