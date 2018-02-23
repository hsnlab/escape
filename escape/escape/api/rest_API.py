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
import hashlib
import httplib
import json
import logging
import threading
import uuid

import requests
from flask import request, Response
from flask.app import Flask
from flask.views import View
from flask_httpauth import HTTPBasicAuth
from requests import RequestException, Timeout
from werkzeug.serving import make_server

from escape.api import LAYER_NAME, log
from escape.nffg_lib import NFFG
from escape.util.api import AbstractAPI, RequestScheduler, RequestCache
from escape.util.com_logger import MessageDumper
from escape.util.config import CONFIG
from escape.util.conversion import NFFGConverter
from escape.util.misc import get_escape_version, \
  call_as_coop_task, quit_with_ok, quit_with_code
from escape.util.stat import stats
from virtualizer import Virtualizer
from virtualizer_info import Info
from virtualizer_mappings import Mappings

RESTART_VALUE = 42
UPDATE_VALUE = 142
STOP_VALUE = 242


class RestInterfaceAPI(AbstractAPI):
  """
  Entry point for REST-API.
  """
  _core_name = LAYER_NAME
  ENTRY_POINT_PREFIX = 'rest_api_'

  def __init__ (self, standalone=False, **kwargs):
    log.info("Starting REST-API Sublayer...")
    self.__server = MainApiServer()
    self.__entry_point_cache = {}
    self.mgrs = {}
    self.is_up = False
    self.prefix = CONFIG.get_rest_api_prefix()
    super(RestInterfaceAPI, self).__init__(standalone, **kwargs)

  def post_up_hook (self, event):
    self.is_up = True
    self.__server.start()

  @staticmethod
  def incoming_logger ():
    log.debug(">>> Got HTTP %s request: %s --> %s, body: %s"
              % (request.method, request.remote_addr, request.url,
                 len(request.data)))

  @staticmethod
  def outcoming_logger (response):
    log.debug(">>> HTTP request: [%s] %s - %s ended!"
              % (request.method, request.url, response.status))
    return response

  def initialize (self):
    log.debug("Initializing REST-API Sublayer...")
    self.__server.flask.before_request(self.incoming_logger)
    self.__server.flask.after_request(self.outcoming_logger)
    # Add <prefix>/version rule by default
    AdminView().register_rules(app=self.__server.flask)
    # Add custom exception handling
    self.__server.flask.register_error_handler(Exception,
                                               self.unhandled_exception)

  def shutdown (self, event):
    log.info("REST-API Sublayer is going down...")
    self.__server.stop()

  def register_component (self, component):
    component_name = component._core_name
    mgr_klass = CONFIG.get_rest_api_resource_class(layer=component_name)
    if mgr_klass is None:
      log.error("REST-API configuration is missing for component: %s"
                % component_name)
      return
    mgr = mgr_klass(layer_api=self)
    mgr.register_routes(app=self.__server.flask)
    self._register_entry_points(component=component)
    self.mgrs[mgr.LAYER_NAME] = mgr
    log.debug(
      "Register component: %s into %s" % (component_name, self.__server))

  @staticmethod
  def pythonify_rpc_name (name):
    return str(name.replace('-', '_'))

  def _register_entry_points (self, component):
    for meth in filter(lambda n: n.startswith(self.ENTRY_POINT_PREFIX),
                       dir(component)):
      layer_name = component._core_name
      rpc_name = self.pythonify_rpc_name(meth[len(self.ENTRY_POINT_PREFIX):])
      self.__entry_point_cache[(layer_name, rpc_name)] = getattr(component,
                                                                 meth)
    log.debug("Registered RPC call handlers: %s"
              % map(lambda e: e[1], self.__entry_point_cache.iterkeys()))

  def get_entry_point (self, layer, rpc):
    """
    """
    entry_point = self.__entry_point_cache.get((layer,
                                                self.pythonify_rpc_name(rpc)))
    if entry_point is not None and callable(entry_point):
      return entry_point
    else:
      raise RuntimeError(
        'Mistyped or not implemented API function call: %s' % rpc)

  @staticmethod
  def unhandled_exception (ex):
    log.exception("Got unexpected exception: %s" % ex)
    return Response(status=httplib.INTERNAL_SERVER_ERROR)


class AdminView(View):
  ADMIN_PREFIX = "_admin_"
  name = "admin"
  RULE_TEMPLATE = "/%s/admin/<any(%s):rpc>"
  prefix = CONFIG.get_rest_api_prefix()
  rpcs = ("shutdown", "restart", "update", "stop")
  methods = ('GET', 'POST')
  auth = HTTPBasicAuth()
  decorators = [auth.login_required]

  def __init__ (self):
    # Add authentication helpers
    self.auth.get_password(self.get_passwd)
    self.auth.hash_password(self.hash_passwd)

  @staticmethod
  def hash_passwd (passwd):
    return hashlib.md5(passwd).hexdigest()

  @staticmethod
  def get_passwd (username):
    if username == CONFIG.get_rest_api_user():
      return CONFIG.get_rest_api_secret()
    log.error("Invalid username!")

  def dispatch_request (self, rpc):
    if rpc not in self.rpcs:
      return Response(status=httplib.NOT_IMPLEMENTED)
    else:
      return getattr(self, rpc)()

  @classmethod
  def register_rules (cls, app):
    rule = "/%s/admin/version" % cls.prefix
    app.add_url_rule(rule="/%s/admin/version" % cls.prefix,
                     endpoint="admin/version",
                     view_func=cls.version)
    log.debug("Registered rule: %s" % rule)
    rule = cls.RULE_TEMPLATE % (cls.prefix, ','.join(cls.rpcs))
    app.add_url_rule(rule=rule,
                     endpoint=cls.name,
                     view_func=cls.as_view(name=cls.name))
    log.debug("Registered rule: %s" % rule)

  @staticmethod
  def version ():
    return Response(get_escape_version())

  @staticmethod
  def shutdown ():
    call_as_coop_task(func=quit_with_ok)
    log.info("Shutdown task scheduled")
    return Response("SHUTDOWN accepted.\n", httplib.ACCEPTED)

  @staticmethod
  def stop ():
    call_as_coop_task(func=quit_with_code, ret_code=STOP_VALUE)
    log.info("Shutdown task scheduled")
    return Response("SHUTDOWN accepted.\n", httplib.ACCEPTED)

  @staticmethod
  def restart ():
    call_as_coop_task(func=quit_with_code, ret_code=RESTART_VALUE)
    log.info("Restart task scheduled")
    return Response("RESTART accepted.\n", httplib.ACCEPTED)

  @staticmethod
  def update ():
    call_as_coop_task(func=quit_with_code, ret_code=UPDATE_VALUE)
    log.info("Update task scheduled")
    return Response("UPDATE accepted.\n", httplib.ACCEPTED)


class MainApiServer(object):
  """
  """
  DEFAULT_HOST = "0.0.0.0"
  DEFAULT_PORT = 8888

  def __init__ (self):
    self._thread = threading.Thread(target=self.run,
                                    name=LAYER_NAME)
    self._thread.daemon = True
    self.started = False
    self.__create_server()
    log.debug("Created RESTful API object with url_prefix: %s" %
              self.flask)

  def __str__ (self):
    return str(self.flask)

  def __create_server (self):
    host = CONFIG.get_rest_api_host()
    port = CONFIG.get_rest_api_port()
    self.flask = Flask(__name__)
    self.__werkzeug = make_server(host=host if host else self.DEFAULT_HOST,
                                  port=port if port else self.DEFAULT_PORT,
                                  app=self.flask)
    # Suppress low level logging
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

  def start (self):
    if not self.started:
      self._thread.start()
      self.started = True

  def stop (self):
    if self.started:
      self.shutdown()
      self.started = False

  def run (self):
    log.info("Starting REST server on: %s:%s" % self.__werkzeug.server_address)
    try:
      self.__werkzeug.serve_forever()
    except Exception as e:
      log.exception("Got exception in REST-API loop: %s" % e)

  def shutdown (self):
    log.debug("Shutdown REST server...")
    self.__werkzeug.shutdown()


class RESTAPIManager(object):
  CALLBACK_TIMEOUT = 3.0

  def __init__ (self, **kwargs):
    self.converter = NFFGConverter(**kwargs)
    self.request_cache = RequestCache()
    self.topology_revision = None
    self.last_response = None

  def invoke_callback (self, message_id, body=None):
    """
    Perform the callback call based on service status and callback URL.

    :param message_id: service request id
    :type message_id: str or int
    :param body: optional callback body
    :type body: str
    :return: status code of the call
    :rtype: int
    """
    status = self.request_cache.get_request(message_id)
    if "call-back" not in status.params:
      return None
    callback_url = status.get_callback()
    if 'message-id' in status.params:
      msg_id = status.params.get('message-id')
    else:
      msg_id = status.message_id
    params = {'message-id': msg_id}
    if status.status == status.SUCCESS:
      params['response-code'] = httplib.OK
      if not body:
        body = "OK"
    else:
      params['response-code'] = httplib.INTERNAL_SERVER_ERROR
      if not body:
        # TODO - return with failed part of the request??
        body = "TODO"
    try:
      ret = requests.post(url=callback_url, params=params, data=body,
                          timeout=self.CALLBACK_TIMEOUT)
      return ret.status_code
    except (RequestException, Timeout):
      return -1


class AbstractAPIView(View):
  MESSAGE_ID_NAME = "message-id"
  name = None
  method = None

  def __init__ (self, mgr):
    """

    :param mgr:
    :type mgr: :class:`AbstractAPIManager`
    """
    self.mgr = mgr

  def dispatch_request (self, *args, **kwargs):
    raise NotImplementedError

  def get_message_id (self):
    if self.MESSAGE_ID_NAME in request.args:
      return request.args[self.MESSAGE_ID_NAME]
    elif self.MESSAGE_ID_NAME in request.headers:
      return request.headers[self.MESSAGE_ID_NAME]
    else:
      return str(uuid.uuid1())

  def proceed (self, *args, **kwargs):
    return self.mgr.handle(rpc=self.name, *args, **kwargs)


class PingView(AbstractAPIView):
  name = 'ping'
  methods = ('GET', 'POST')

  def dispatch_request (self):
    if self.mgr.layer_api.is_up:
      return Response('OK', httplib.OK)
    else:
      return Response('INITIALIZING', httplib.ACCEPTED)


class GetConfigView(AbstractAPIView):
  name = 'get-config'
  methods = ('GET', 'POST')

  def dispatch_request (self):
    topo_resource = self.proceed()
    if topo_resource is None:
      return Response("Resource info is missing!", httplib.NOT_FOUND)
    else:
      if isinstance(topo_resource, Virtualizer):
        data, cont_type = topo_resource.xml(), "application/xml"
      elif isinstance(topo_resource, NFFG):
        data, cont_type = topo_resource.dump(), "application/json"
      else:
        log.error("Unexpected topology format!")
        return
    MessageDumper().dump_to_file(data=data,
                                 unique="ESCAPE-%s-get-config" %
                                        self.mgr.LAYER_NAME)
    return Response(response=data, status=httplib.OK, content_type=cont_type)


class EditConfigView(AbstractAPIView):
  name = 'edit-config'
  methods = ('POST', 'PUT')

  def dispatch_request (self):
    """
    :return:
    """
    log.info("Received edit-config deploy request...")
    if not request.data:
      log.error("No data received!")
      return Response("Request data is missing!", httplib.BAD_REQUEST)
    # Get message-id
    unique = "ESCAPE-%s-edit-config" % self.mgr.LAYER_NAME
    # Trailing
    stats.init_request_measurement(request_id=unique)
    MessageDumper().dump_to_file(data=request.data, unique=unique)
    # Parsing
    log.debug("Parsing request (body_size: %s)..." % len(request.data))
    if CONFIG.get_rest_api_config(self.mgr.LAYER_NAME)['unify_interface']:
      req = Virtualizer.parse_from_text(text=request.data)
    else:
      req = NFFG.parse(raw_data=request.data)
      if req.mode:
        log.info("Detected mapping mode in request body: %s" % req.mode)
      else:
        if request.method == 'POST':
          req.mode = req.MODE_ADD
          log.debug(
            'Add mapping mode: %s based on HTTP verb: %s' % (req.mode,
                                                             request.method))
        elif request.method == 'PUT':
          req.mode = NFFG.MODE_DEL
          log.debug(
            'Add mapping mode: %s based on HTTP verb: %s' % (req.mode,
                                                             request.method))
        else:
          log.info('No mode parameter has been defined in body!')
    log.debug("Request parsing ended...")
    # Scheduling
    params = request.args.to_dict(flat=True)
    msg_id = self.get_message_id()
    log.info("Acquired message-id: %s" % msg_id)
    params[self.MESSAGE_ID_NAME] = msg_id
    entry_point = self.mgr.layer_api.get_entry_point(layer=self.mgr.LAYER_NAME,
                                                     rpc=self.name)
    self.mgr.scheduler.schedule_request(id=msg_id,
                                        layer=self.mgr.LAYER_NAME,
                                        hook=entry_point,
                                        data=req,
                                        params=params)
    return Response(status=httplib.ACCEPTED, headers={"message-id": msg_id})


class TopologyView(GetConfigView):
  name = 'topology'
  methods = ('GET', 'POST')


class SGView(EditConfigView):
  name = 'sg'
  methods = ('POST', 'PUT')


class StatusView(AbstractAPIView):
  name = 'status'
  methods = ('GET',)

  def dispatch_request (self):
    if self.MESSAGE_ID_NAME in request.args:
      message_id = request.args[self.MESSAGE_ID_NAME]
    elif self.MESSAGE_ID_NAME in request.headers:
      message_id = request.headers[self.MESSAGE_ID_NAME]
    else:
      return Response("No message-id was given!", status=httplib.BAD_REQUEST)
    log.debug("Detected message-id: %s" % message_id)
    code, result = self.proceed(message_id=message_id)
    log.debug("Responded status code: %s, data: %s" % (code, result))
    MessageDumper().dump_to_file(data=repr((code, result)),
                                 unique="ESCAPE-%s-status" %
                                        self.mgr.LAYER_NAME)
    return Response(result, status=code, headers={"message-id": message_id})


class MappingInfoView(AbstractAPIView):
  RULE_TEMPLATE = "/{prefix}/{layer}/{rpc}/<service_id>"
  name = 'mapping-info'
  methods = ('GET',)

  def dispatch_request (self, service_id):
    log.debug("Detected service id: %s" % service_id)
    mapping_info = self.proceed(service_id=service_id)
    if isinstance(mapping_info, basestring):
      return Response(response=mapping_info, status=httplib.BAD_REQUEST)
    MessageDumper().dump_to_file(data=json.dumps(mapping_info, indent=4),
                                 unique="ESCAPE-%s-status" %
                                        self.mgr.LAYER_NAME)
    log.debug("Sending collected mapping info...")
    return Response(response=json.dumps(mapping_info),
                    status=httplib.OK,
                    content_type="application/json")


class MappingsView(AbstractAPIView):
  name = 'mappings'
  methods = ('POST',)

  def dispatch_request (self):
    if not request.data:
      log.error("No data received!")
      return Response("Request data is missing!", httplib.BAD_REQUEST)
    # Get message-id
    MessageDumper().dump_to_file(data=request.data,
                                 unique="ESCAPE-%s-mappings" %
                                        self.mgr.LAYER_NAME)
    mappings = Mappings.parse_from_text(text=request.data)
    mappings = self.proceed(mappings=mappings)
    if not mappings:
      log.error("Calculated mapping data is missing!")
      return Response(status=httplib.INTERNAL_SERVER_ERROR)
    log.debug("Sending collected mapping info...")
    data = mappings.xml()
    MessageDumper().dump_to_file(data=data,
                                 unique="ESCAPE-%s-mappings-response" %
                                        self.mgr.LAYER_NAME)
    return Response(data, status=httplib.OK, content_type="application/xml")


class InfoView(AbstractAPIView):
  name = 'info'
  methods = ('POST',)

  def dispatch_request (self):
    if not request.data:
      log.error("No data received!")
      return Response("Request data is missing!", httplib.BAD_REQUEST)
    # Get message-id
    MessageDumper().dump_to_file(data=request.data,
                                 unique="ESCAPE-%s-info" %
                                        self.mgr.LAYER_NAME)
    info = Info.parse_from_text(text=request.data)
    msg_id = self.get_message_id()
    self.proceed(info=info, id=msg_id, params=request.args.to_dict(flat=True))
    return Response(status=httplib.ACCEPTED)


class AbstractAPIManager(object):
  RULE_TEMPLATE = "/{prefix}/{layer}/{rpc}"
  LAYER_NAME = None
  VIEWS = None

  def __init__ (self, layer_api):
    """
    :type layer_api: :class:`RestInterfaceAPI`
    """
    self.layer_api = layer_api
    self.scheduler = RequestScheduler()

  def __get_rule (self, view):
    if hasattr(view, "RULE_TEMPLATE"):
      return view.RULE_TEMPLATE.format(prefix=self.layer_api.prefix,
                                       layer=self.LAYER_NAME,
                                       rpc=view.name)
    else:
      return self.RULE_TEMPLATE.format(prefix=self.layer_api.prefix,
                                       layer=self.LAYER_NAME,
                                       rpc=view.name)

  def __get_endpoint (self, view):
    return "%s/%s" % (self.LAYER_NAME, view.name)

  def _add_route (self, app, view):
    """
    :type app: :class:`Flask`
    :type app: :class:`AbstractView`
    """
    app.add_url_rule(rule=self.__get_rule(view=view),
                     endpoint=self.__get_endpoint(view=view),
                     view_func=view.as_view(name=view.name, mgr=self))

  def register_routes (self, app):
    """
    :type app: :class:`Flask`
    """
    for view in self.VIEWS:
      rule = self.__get_rule(view=view)
      app.add_url_rule(rule=rule,
                       endpoint=self.__get_endpoint(view=view),
                       view_func=view.as_view(name=view.name, mgr=self))
      log.debug("Registered rule: %s" % rule)

  def handle (self, rpc, *args, **kwargs):
    entry_point = self.layer_api.get_entry_point(layer=self.LAYER_NAME, rpc=rpc)
    return entry_point(*args, **kwargs)


class ServiceAPIManager(AbstractAPIManager):
  LAYER_NAME = 'service'
  VIEWS = (PingView,
           TopologyView,
           SGView,
           StatusView)


class OrchestrationAPIManager(AbstractAPIManager):
  LAYER_NAME = 'orchestration'
  VIEWS = (PingView,
           GetConfigView,
           EditConfigView,
           StatusView,
           MappingInfoView,
           MappingsView,
           InfoView)


class AdaptationAPIManager(AbstractAPIManager):
  LAYER_NAME = 'adaptation'
  VIEWS = (PingView,
           GetConfigView,
           EditConfigView)
