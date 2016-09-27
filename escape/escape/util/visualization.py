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

import virtualizer as Virtualizer
from escape import CONFIG, __version__
from escape.adapt import LAYER_NAME as ADAPT
from escape.nffg_lib.nffg import NFFG
from escape.orchest import LAYER_NAME as ORCHEST
from escape.service import LAYER_NAME as SERVICE
from escape.util.conversion import NFFGConverter
from escape.util.misc import Singleton
from pox.core import core


class RemoteVisualizer(Session):
  """
  Main object for remote Visualization.
  """
  # Singleton
  __metaclass__ = Singleton
  """Singleton"""
  # name form POXCore
  _core_name = "visualizer"
  """Name form POXCore"""

  # Bindings of Layer IDs
  ID_MAPPER = {
    SERVICE: "ESCAPE-SERVICE",
    ORCHEST: "ESCAPE-ORCHESTRATION",
    ADAPT: "ESCAPE-ADAPTATION"
  }
  """Bindings of Layer IDs"""

  # Basic HTTP headers
  basic_headers = {
    'User-Agent': "ESCAPE/" + __version__,
    'Content-Type': "application/xml"}
  """Basic HTTP headers"""

  # Default timeout value in sec
  DEFAULT_TIMEOUT = 1
  """Default timeout value in sec"""

  def __init__ (self, url=None, rpc=None, timeout=DEFAULT_TIMEOUT,
                instance_id=None):
    """
    Init.

    :param url: URL of the remote server
    :type url: str
    :param rpc: RPC name
    :type rpc: str
    :param timeout: connections timeout
    :type timeout: int
    :param instance_id: additional id to join to the end of the id
    :type instance_id: str
    :return: None
    """
    super(RemoteVisualizer, self).__init__()
    self.log = core.getLogger("visualizer")
    if url is None:
      url = CONFIG.get_visualization_url()
    if rpc is None:
      rpc = CONFIG.get_visualization_rpc()
    self._url = urlparse.urljoin(url, rpc)
    if self._url is None:
      raise RuntimeError("Missing URL from %s" % self.__class__.__name__)
    self._timeout = timeout
    if instance_id is None:
      self.instance_id = CONFIG.get_visualization_instance_id()
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

  def send_notification (self, data, id, url=None, **kwargs):
    """
    Send given data to a remote server for visualization.
    Convert given NFFG into Virtualizer format if needed.

    :param data: topology description need to send
    :type data: :any:`NFFG` or Virtualizer
    :param id: id of the data, needs for the remote server
    :type id: str
    :param url: additional URL (optional)
    :type url: str
    :param kwargs: additional params to request
    :type kwargs: dict
    :return: response text
    :rtype: str
    """
    if url is None:
      url = self._url
    if url is None:
      self.log.error("Missing URL for remote visualizer! Skip notification...")
      return
    if 'timeout' not in kwargs:
      kwargs['timeout'] = self._timeout
    self.log.debug("Send visualization notification to %s" % self._url)
    try:
      if data is None:
        self.log.warning("Missing data! Skip notifying remote visualizer.")
        return False
      elif isinstance(data, NFFG):
        data = self.converter.dump_to_Virtualizer(nffg=data)
      elif not isinstance(data, Virtualizer.Virtualizer):
        self.log.warning(
          "Unsupported data type: %s! Skip notification..." % type(data))
        return
      _id = self.ID_MAPPER.get(id, "UNDEFINED")
      if self.instance_id is not None:
        _id += "-%s" % self.instance_id
      data.id.set_value(_id)
      # If additional params is not empty dict -> override the basic params
      if 'headers' not in kwargs:
        kwargs['headers'] = self.basic_headers
      else:
        kwargs['headers'] = self.basic_headers.copy().update(kwargs['headers'])
      self.log.debug("Sending visualization notification...")
      self._response = self.request(method='POST', url=url, data=data.xml(),
                                    **kwargs)
      self._response.raise_for_status()
      return self._response.text
    except (ConnectionError, HTTPError, KeyboardInterrupt) as e:
      self.log.warning(
        "Got exception during notifying remote Visualizer: %s!" % e)
      return False
    except Timeout:
      self.log.warning(
        "Got timeout(%ss) during notify remote Visualizer!" % kwargs['timeout'])
      return True
