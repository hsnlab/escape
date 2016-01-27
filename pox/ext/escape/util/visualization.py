# Copyright 2016 Janos Czentye <czentye@tmit.bme.hu>
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
Contains functions and classes for remote visualization.
"""
import logging
import urlparse
from requests import Session, ConnectionError, HTTPError, Timeout

from escape import CONFIG
from escape.util.conversion import NFFGConverter
from escape.util.misc import Singleton
from escape.util.nffg import NFFG
from pox.core import core


class RemoteVisualizer(Session):
  """
  Main object for remote Visualization.
  """
  # Singleton
  __metaclass__ = Singleton
  # name form POXCore
  _core_name = "visualizer"

  def __init__ (self, url=None, rpc=""):
    """
    Init.

    :param url: URL of the remote server
    :type url: str
    :param rpc: RPC name
    :type rpc: str
    :return: None
    """
    super(RemoteVisualizer, self).__init__()
    self.log = core.getLogger("visualizer")
    if url is None:
      url = CONFIG.get_visualization_url()
      rpc = CONFIG.get_visualization_rpc()
      if url.endswith('/'):
        self._url = urlparse.urljoin(url, rpc)
      else:
        self._url = urlparse.urljoin(url + '/', rpc)
    if self._url is None:
      raise RuntimeError("Missing URL from %s" % self.__class__.__name__)
    self.log.info("Setup remote Visualizer with URL: %s" % self._url)
    # Store the last request
    self._response = None
    self.converter = NFFGConverter(domain="ESCAPE", logger=self.log)
    # Suppress low level logging
    self.__suppress_requests_logging()

  @staticmethod
  def __suppress_requests_logging (level=None):
    """
    Suppress annoying and detailed logging of `requests` and `urllib3` packages.

    :param level: level of logging (default: WARNING)
    :type level: str
    :return: None
    """
    level = level if level is not None else logging.WARNING
    logging.getLogger("requests").setLevel(level)
    logging.getLogger("urllib3").setLevel(level)

  def send_notification (self, data, url=None, **kwargs):
    """
    Send given data to a remote server for visualization.
    Convert given NFFG into Virtualizer format if needed.

    :param data: topology description need to send
    :type data: :any:`NFFG` or Virtualizer
    :param kwargs: additional params to request
    :type kwargs: dict
    :return: response text
    :rtype: str
    """
    try:
      if isinstance(data, NFFG):
        data = self.converter.dump_to_Virtualizer(nffg=data)
      if url is None:
        url = self._url
      self.log.debug("Send visualization notification to %s" % self._url)
      self._response = self.request(method='POST', url=url, data=data.xml(),
                                    **kwargs)
      self._response.raise_for_status()
      return self._response.text
    except (ConnectionError, HTTPError, Timeout, KeyboardInterrupt) as e:
      self.log.error(
         "Got exception during notifying remote Visualizer: %s!" % e)
