# Copyright 2017 Janos Czentye <czentye@tmit.bme.hu>
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
import httplib
import json

from escape.orchest import log as log
from escape.orchest.ros_API import BasicUnifyRequestHandler
from escape.util.api import RESTServer
from escape.util.misc import VERBOSE
from virtualizer_info import Info
from virtualizer_mappings import Mappings


class CfOrRequestHandler(BasicUnifyRequestHandler):
  """
  Request Handler for the Cf-OR interface.

  .. warning::
    This class is out of the context of the recoco's co-operative thread
    context! While you don't need to worry much about synchronization between
    recoco tasks, you do need to think about synchronization between recoco task
    and normal threads. Synchronisation is needed to take care manually: use
    relevant helper function of core object: `callLater`/`raiseLater` or use
    `schedule_as_coop_task` decorator defined in util.misc on the called
    function.

  Contains handler functions for REST-API.
  """
  # Bind HTTP verbs to UNIFY's API functions
  request_perm = {
    'GET': ('ping', 'version', 'operations', 'get_config'),
    'POST': ('ping', 'get_config', 'edit_config')
  }
  """Bind HTTP verbs to UNIFY's API functions"""
  # Statically defined layer component to which this handler is bounded
  # Need to be set by container class
  bounded_layer = 'orchestration'
  """Statically defined layer component to which this handler is bounded"""
  static_prefix = "cfor"
  # Logger name
  LOGGER_NAME = "Cf-Or"
  """Logger name"""
  log = log.getChild("[%s]" % LOGGER_NAME)
  # Use Virtualizer format
  virtualizer_format_enabled = True
  """Use Virtualizer format"""
  # Default communication approach
  DEFAULT_DIFF = True
  """Default communication approach"""
  # Name mapper to avoid Python naming constraint
  rpc_mapper = {
    'get-config': "get_config",
    'edit-config': "edit_config"
  }
  """Name mapper to avoid Python naming constraint"""
  # Bound function
  API_CALL_RESOURCE = 'api_cfor_get_config'
  API_CALL_REQUEST = 'api_cfor_edit_config'

  def __init__ (self, request, client_address, server):
    """
    Init.

    :param request: request type
    :type request: str
    :param client_address: client address
    :type client_address: str
    :param server: server object
    :type server: :any:`BaseHTTPServer.HTTPServer`
    :return: None
    """
    BasicUnifyRequestHandler.__init__(self, request, client_address, server)

  def get_config (self):
    """
    Response configuration.

    :return: None
    """
    self.log.debug("Call %s function: get-config" % self.LOGGER_NAME)
    # Forward call to main layer class
    resource = self._proceed_API_call(self.API_CALL_RESOURCE)
    self._topology_view_responder(resource_nffg=resource)
    self.log.debug("%s function: get-config ended!" % self.LOGGER_NAME)

  def edit_config (self):
    """
    Receive configuration and initiate orchestration.

    :return: None
    """
    self.log.debug("Call %s function: edit-config" % self.LOGGER_NAME)
    nffg = self._service_request_parser()
    if nffg:
      self._proceed_API_call(self.API_CALL_REQUEST, nffg)
      self.send_acknowledge(message_id=nffg.id)
    self.log.debug("%s function: edit-config ended!" % self.LOGGER_NAME)


class Extended5GExRequestHandler(BasicUnifyRequestHandler):
  """
  Extended handler class for UNIFY interface.
  Contains RPCs for providing additional information.
  """
  # Bind HTTP verbs to UNIFY's API functions
  request_perm = {
    'GET': ('ping', 'version', 'operations', 'get_config', 'mapping_info',
            'status'),
    'POST': ('ping', 'get_config', 'edit_config', 'mappings', "info"),
    # 'DELETE': ('edit_config',),
    'PUT': ('edit_config',)
  }
  # Name mapper to avoid Python naming constraint
  rpc_mapper = {
    'get-config': "get_config",
    'edit-config': "edit_config",
    'mapping-info': "mapping_info"
  }
  # Bound function
  API_CALL_MAPPING_INFO = 'api_ros_mapping_info'
  API_CALL_MAPPINGS = 'api_ros_mappings'
  API_CALL_INFO = 'api_ros_info'

  def mapping_info (self):
    """
    Respond the corresponding node IDs of a mapped request given by service ID.

    :return: None
    """
    self.log.debug("Call %s function: mapping-info" % self.LOGGER_NAME)
    service_id = self.__get_service_id()
    if not service_id:
      self.send_error(code=httplib.BAD_REQUEST,
                      message="Service ID is missing!")
      return
    self.log.debug("Detected service id: %s" % service_id)
    ret = self._proceed_API_call(self.API_CALL_MAPPING_INFO, service_id)
    self.log.debug("Sending collected mapping info...")
    if isinstance(ret, basestring):
      # Got error message
      self.send_error(code=httplib.BAD_REQUEST, message=ret)
      return
    self.__respond_info(ret)
    self.log.debug("%s function: mapping-info ended!" % self.LOGGER_NAME)

  def __get_service_id (self):
    """
    Return the service id given in the URL.

    :return: service id
    :rtype: str
    """
    splitted = str(self.path).split("/mapping-info/", 1)
    if len(splitted) < 2:
      return None
    else:
      return splitted[1]

  def __respond_info (self, data=None):
    """
    Send back requested data.

    :param data: raw info
    :type data: dict
    :return: None
    """
    data = json.dumps(data if data else {})
    self.send_response(httplib.OK)
    self.send_header('Content-Type', 'application/json')
    self.send_header('Content-Length', len(data))
    self.end_headers()
    self.wfile.write(data)
    self.log.log(VERBOSE, "Responded mapping info:\n%s" % data)
    return

  def mappings (self):
    """
    Respond the mapping of requested NFs and corresponding node IDs.

    :return: None
    """
    self.log.debug("Call %s function: mappings" % self.LOGGER_NAME)
    self.log.debug("Detected message format: %s" %
                   self.headers.get("Content-Type"))
    raw_body = self._get_body()
    # log.getChild("REST-API").debug("Request body:\n%s" % body)
    if raw_body is None or not raw_body:
      log.warning("Received data is empty!")
      self.send_error(httplib.BAD_REQUEST, "Missing body!")
      return
    mappings = Mappings.parse_from_text(text=raw_body)
    self.log.log(VERBOSE, "Full request:\n%s" % mappings.xml())
    ret = self._proceed_API_call(self.API_CALL_MAPPINGS, mappings)
    if ret is None:
      log.warning("Calculated mapping data is missing!")
      self.send_error(httplib.INTERNAL_SERVER_ERROR)
      return
    self.log.debug("Sending collected mapping info...")
    response_data = ret.xml()
    self.send_response(httplib.OK)
    self.send_header('Content-Type', 'application/xml')
    self.send_header('Content-Length', len(response_data))
    self.end_headers()
    self.wfile.write(response_data)
    self.log.log(VERBOSE, "Responded mapping info:\n%s" % response_data)
    self.log.debug("%s function: mapping-info ended!" % self.LOGGER_NAME)

  def info (self):
    self.log.debug("Call %s function: info" % self.LOGGER_NAME)
    raw_body = self._get_body()
    if raw_body is None or not raw_body:
      log.warning("Received data is empty!")
      self.send_error(httplib.BAD_REQUEST, "Missing body!")
      return
    info = Info.parse_from_text(text=raw_body)
    self.log.log(VERBOSE, "Full request:\n%s" % info.xml())
    self._proceed_API_call(self.API_CALL_INFO, info)
    # Return accepted code due to async mode
    self.send_response(code=httplib.ACCEPTED)
    self.end_headers()
    self.log.debug("%s function: info ended!" % self.LOGGER_NAME)


class MonitoringCache(object):
  pass


class ExtendedMonitoringRESTServer(RESTServer):
  def __init__ (self, RequestHandlerClass, address='127.0.0.1', port=8008):
    super(ExtendedMonitoringRESTServer, self).__init__(RequestHandlerClass,
                                                       address,
                                                       port)
    self.monitor_cache = MonitoringCache()
