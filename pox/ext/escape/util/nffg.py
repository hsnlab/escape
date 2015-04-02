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


class NFFG(object):
  """
  Wrapper class which represent an NF-FG
  """

  def __init__ (self):
    """
    Init
    """
    super(NFFG, self).__init__()
    self.id = None
    # TODO - implement
    self.error = "NotImplemented"

  @staticmethod
  def init_from_json (json):
    """
    Create and initialize an NFFG object from JSON data

    :param json: NF-FG represented in JSON format
    :type json: str
    :return: NFFG instance
    :rtype: NFFG
    """
    # TODO - implement! This function has already used in layer APIs
    return NFFG()

  def to_json (self):
    """
    Return a JSON string represent this instance

    :return: JSON formatted string
    :rtype: str
    """