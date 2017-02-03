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
import uuid

from escape.nffg_lib.nffg import NFFG
from escape.orchest import log as log
from escape.util.api import AbstractRequestHandler, RESTServer
from escape.util.conversion import NFFGConverter
from escape.util.misc import VERBOSE
from virtualizer import Virtualizer
from virtualizer_info import Info
from virtualizer_mappings import Mappings


class BasicUnifyRequestHandler(AbstractRequestHandler):
  """
  Request Handler for agent behaviour in Resource Orchestration SubLayer.

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
    'GET': ('ping', 'version', 'operations', 'get_config', 'status'),
    'POST': ('ping', 'get_config', 'edit_config'),
    # 'DELETE': ('edit_config',),
    'PUT': ('edit_config',)
  }
  # Statically defined layer component to which this handler is bounded
  # Need to be set by container class
  bounded_layer = 'orchestration'
  """Statically defined layer component to which this handler is bounded"""
  # Set special prefix to imitate OpenStack agent API
  static_prefix = "escape"
  """Special prefix to imitate OpenStack agent API"""
  # Logger name
  LOGGER_NAME = "Sl-Or"
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
  API_CALL_RESOURCE = 'api_ros_get_config'
  API_CALL_REQUEST = 'api_ros_edit_config'

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
    AbstractRequestHandler.__init__(self, request, client_address, server)

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
    params = self._get_request_params()
    self.log.debug("Detected request parameters: %s" % params)
    if 'message-id' in params:
      self.log.debug("Detected message id: %s" % params['message-id'])
    else:
      params['message-id'] = str(uuid.uuid1())
      self.log.debug("No message-id! Generated id: %s" % params['message-id'])
    if nffg:
      if nffg.service_id is None:
        nffg.service_id = nffg.id
      nffg.id = params['message-id']
      nffg.metadata['params'] = params
      self._proceed_API_call(self.API_CALL_REQUEST,
                             nffg=nffg,
                             params=params)
      self.send_acknowledge(message_id=params['message-id'])
    self.log.debug("%s function: edit-config ended!" % self.LOGGER_NAME)

  def status (self):
    params = self._get_request_params()
    message_id = params.get('message-id')
    if not message_id:
      self.send_error(code=httplib.BAD_REQUEST, message="message-id is missing")
      return
    code, result = self._proceed_API_call('api_ros_status', message_id)
    if not result:
      self.send_acknowledge(code=code, message_id=message_id)
      self.log.debug("Responded status code: %s" % code)
    else:
      # TODO collect bad NFFG
      self.send_raw_response(raw_data=result, code=code,
                             content="application/xml")
      self.log.debug("Responded status code: %s, data: %s" % (code, result))

  def _topology_view_responder (self, resource_nffg, message_id=None):
    """
    Process the required topology data and sent back to the REST client.

    :param resource_nffg: required data
    :type resource_nffg: :any: `NFFG`
    :return: None
    """
    if resource_nffg is None:
      self.send_error(code=httplib.NOT_FOUND,
                      message="Resource info is missing!")
      return
    # Global resource has not changed -> respond with the cached topo
    if resource_nffg is False:
      self.log.debug(
        "Global resource has not changed! Respond with cached topology...")
      if self.server.last_response is None:
        log.warning("Cached topology is missing!")
        self.send_error(code=httplib.NOT_FOUND,
                        message="Cached info is missing from API!")
        return
      if self.virtualizer_format_enabled:
        data = self.server.last_response.xml()
      else:
        data = self.server.last_response.dump()
    else:
      # Convert required NFFG if needed
      if self.virtualizer_format_enabled:
        self.log.debug("Convert internal NFFG to Virtualizer...")
        converter = NFFGConverter(logger=log)
        v_topology = converter.dump_to_Virtualizer(nffg=resource_nffg)
        # Cache converted data for edit-config patching
        self.log.debug("Cache converted topology...")
        self.server.last_response = v_topology
        # Dump to plain text format
        data = v_topology.xml()
        # Setup HTTP response format
      else:
        self.log.debug("Cache acquired topology...")
        self.server.last_response = resource_nffg
        data = resource_nffg.dump()
    # Setup OK status for HTTP response
    self.send_response(httplib.OK)
    if self.virtualizer_format_enabled:
      self.send_header('Content-Type', 'application/xml')
    else:
      self.send_header('Content-Type', 'application/json')
    # Setup length for HTTP response
    self.send_header('Content-Length', len(data))
    self.send_header('message-id',
                     message_id if message_id else str(uuid.uuid1()))
    self.end_headers()
    self.log.debug("Send back topology description...")
    self.wfile.write(data)
    self.log.log(VERBOSE, "Responded topology:\n%s" % data)

  def _service_request_parser (self):
    """
    Process the received service request.

    :return: Parsed service request
    :rtype: :any:`NFFG`
    """
    # Obtain NFFG from request body
    self.log.debug("Detected message format: %s" %
                   self.headers.get("Content-Type"))
    raw_body = self._get_body()
    # log.getChild("REST-API").debug("Request body:\n%s" % body)
    if raw_body is None or not raw_body:
      log.warning("Received data is empty!")
      self.send_error(code=httplib.BAD_REQUEST, message="Missing body!")
      return
    # Expect XML format --> need to convert first
    if self.virtualizer_format_enabled:
      if self.headers.get("Content-Type") != "application/xml" and \
         not raw_body.startswith("<?xml version="):
        self.log.error("Received data is not in XML format despite of the "
                       "UNIFY interface is enabled!")
        self.send_error(code=httplib.UNSUPPORTED_MEDIA_TYPE)
        return
      # Get received Virtualizer
      received_cfg = Virtualizer.parse_from_text(text=raw_body)
      self.log.log(VERBOSE, "Received request:\n%s" % raw_body)
      # If there was not get-config request so far
      if self.DEFAULT_DIFF:
        if self.server.last_response is None:
          self.log.info("Missing cached Virtualizer! Acquiring topology now...")
        else:
          self.log.debug("Check topology changes...")
        config = self._proceed_API_call(self.API_CALL_RESOURCE)
        if config is None:
          self.log.error("Requested resource info is missing!")
          self.send_error(code=httplib.NOT_FOUND,
                          message="Resource info is missing!")
          return
        elif config is False:
          self.log.debug("Topo description is unchanged!")
        else:
          # Convert required NFFG if needed
          if self.virtualizer_format_enabled:
            self.log.debug("Convert internal NFFG to Virtualizer...")
            converter = NFFGConverter(logger=log)
            v_topology = converter.dump_to_Virtualizer(nffg=config)
            # Cache converted data for edit-config patching
            self.log.debug("Cache converted topology...")
            self.server.last_response = v_topology
          else:
            self.log.debug("Cache acquired topology...")
            self.server.last_response = config
        # Perform patching
        full_cfg = self.__recreate_full_request(diff=received_cfg)
      else:
        full_cfg = received_cfg
      self.log.log(VERBOSE, "Generated request:\n%s" % full_cfg.xml())
      # Convert response's body to NFFG
      self.log.info("Converting full request data...")
      converter = NFFGConverter(domain="REMOTE", logger=log)
      nffg = converter.parse_from_Virtualizer(vdata=full_cfg)
    else:
      if self.headers.get("Content-Type") != "application/json":
        self.log.error("Received data is not in JSON format despite of the "
                       "UNIFY interface is disabled!")
        self.send_error(code=httplib.UNSUPPORTED_MEDIA_TYPE)
        return
      # Initialize NFFG from JSON representation
      self.log.info("Parsing request into internal NFFG format...")
      nffg = NFFG.parse(raw_body)
    if nffg.mode:
      self.log.info(
        "Detected mapping mode in request body: %s" % nffg.mode)
    else:
      command = self.command.upper()
      if command == 'POST':
        nffg.mode = NFFG.MODE_ADD
        self.log.debug(
          'Add mapping mode: %s based on HTTP verb: %s' % (nffg.mode, command))
      elif command == 'PUT':
        nffg.mode = NFFG.MODE_DEL
        self.log.debug(
          'Add mapping mode: %s based on HTTP verb: %s' % (nffg.mode, command))
      else:
        self.log.info('No mode parameter has been defined in body!')
    self.log.debug("Parsed NFFG install request: %s" % nffg)
    self.log.log(VERBOSE, "Full request:\n%s" % nffg.dump())
    return nffg

  def __recreate_full_request (self, diff):
    """
    Recreate the full domain install request based on previously sent
    topology config and received diff request.

    :return: recreated request
    :rtype: :any:`NFFG`
    """
    self.log.info("Patching cached topology with received diff...")
    full_request = self.server.last_response.full_copy()
    full_request.bind(relative=True)
    # Do not call bind on diff to avoid resolve error in Virtualizer
    # diff.bind(relative=True)
    # Adapt changes on  the local config
    full_request.patch(source=diff)
    # full_request.bind(relative=True)
    # return full_request
    # Perform hack to resolve inconsistency
    return Virtualizer.parse_from_text(full_request.xml())


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


class ExtendedMonitoringRESTServer(RESTServer):
  pass


class MonitoringManager(object):
  def __init__ (self):
    self.__waiting = []
    self.__cache = {}

  def register_request (self, domain, data):
    if domain not in self.__cache:
      log.debug("Register domain: %s for recursive monitoring..." % domain)
      self.__waiting = []
      self.__cache[domain] = data
    else:
      log.warning("Domain: %s is already managed! Skip re-adding..." % domain)

  def update_domain (self, domain, data):
    if domain in self.__cache:
      log.debug("Update monitoring data of domain: %s" % domain)
      self.__cache = data
      self.__waiting.remove(domain)
    else:
      log.warning("Domain: %s is not managed! Skip updating..." % domain)
