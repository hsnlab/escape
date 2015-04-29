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
"""
Contains features for NF-FG processing, parsing, creating, and handling
"""
import os


class NFFG(object):
  """
  Wrapper class which represent an NF-FG
  """

  def __init__ (self, json=None, file = None):
    """
    Init
    """
    super(NFFG, self).__init__()
    self.id = None
    if json:
      self._init_from_json(json)
    elif file and not file.startswith('/'):
      file = os.path.abspath(file)
      with open(file, 'r') as f:
        self._init_from_json(json.load(f))
    self.error = "NotImplementedYet"

  def _init_from_json (self, json_data):
    """
    Initialize the NFFG object from JSON data

    :param json_data: NF-FG represented in JSON format
    :type json_data: str
    :return: None
    """
    # TODO - implement! This function has already used in layer APIs

  def to_json (self):
    """
    Return a JSON string represent this instance

    :return: JSON formatted string
    :rtype: str
    """