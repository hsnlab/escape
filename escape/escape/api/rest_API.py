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
import importlib
import threading

from flask import request
from flask.app import Flask
from flask_restful import Api, Resource
from werkzeug.serving import make_server

from escape import __project__
from escape.api import LAYER_NAME, log
from escape.util.api import AbstractAPI
from escape.util.config import CONFIG
from escape.util.misc import get_escape_version

AVAILABLE_RPCS = repr(('ping',
                       'get-config',
                       'edit-config'))


class RestInterfaceAPI(AbstractAPI):
  """
  Entry point for REST-API.
  """
  _core_name = LAYER_NAME
  ENTRY_POINT_PREFIX = 'rest_api_'
  BASIC_ROUTE_TEMPLATE = '/<any("version", "ping"):rpc>'
  URL_ROUTE_TEMPLATE = '/{layer_name!s}/<any%s:rpc>' % AVAILABLE_RPCS

  def __init__ (self, standalone=False, **kwargs):
    log.info("Starting REST-API Sublayer...")
    self.api = MainApiServer()
    self.__entry_point_cache = {}
    self.is_up = False
    super(RestInterfaceAPI, self).__init__(standalone, **kwargs)

  def post_up_hook (self, event):
    self.is_up = True
    self.api.start()

  @staticmethod
  def request_logger ():
    log.debug(">>> Got HTTP %s request: %s --> %s, body: %s"
              % (request.method, request.remote_addr, request.url,
                 len(request.data)))

  def initialize (self):
    log.debug("Initializing REST-API Sublayer...")
    self.api.server_api.app.before_request(self.request_logger)
    self.api.server_api.add_resource(AbstractLayerResourceHandler,
                                     self.BASIC_ROUTE_TEMPLATE,
                                     resource_class_kwargs={'layer_api': self})

  def shutdown (self, event):
    log.info("REST-API Sublayer is going down...")
    self.api.stop()

  def register_component (self, component):
    component_name = component._core_name
    resource_klass = CONFIG.get_rest_api_resource_class(layer=component_name)
    if resource_klass is None:
      log.eroor("REST-API configuration si missing for component: %s"
                % component_name)
    url_path = self.URL_ROUTE_TEMPLATE.format(layer_name=component_name)
    self.api.server_api.add_resource(resource_klass, url_path,
                                     resource_class_kwargs={'layer_api': self})
    log.debug("Register component: %s into %s" % (component_name, self.api))
    self._register_entry_points(component=component)

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
      log.debug("Registered call handler: %s" % meth)

  def proceed_API_call (self, layer, rpc, *args, **kwargs):
    """
    """
    entry_point = self.__entry_point_cache.get((layer,
                                                self.pythonify_rpc_name(rpc)))
    if entry_point is not None and callable(entry_point):
      return entry_point(*args, **kwargs)
    else:
      raise RuntimeError('Mistyped or not implemented API function call: %s' %
                         rpc)


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
              self.server_api.prefix)

  def __str__ (self):
    return str(self.server_api.app)

  def __create_server (self):
    host = CONFIG.get_rest_api_host()
    port = CONFIG.get_rest_api_port()
    self.__werkzeug_server = make_server(
      host=host if host else self.DEFAULT_HOST,
      port=port if port else self.DEFAULT_PORT,
      app=Flask(__name__))
    self.server_api = Api(app=self.__werkzeug_server.app,
                          prefix='/' + CONFIG.get_rest_api_prefix())

  def start (self):
    if not self.started:
      self._thread.start()
      self.started = True

  def stop (self):
    if self.started:
      self.shutdown()
      self.started = False

  def run (self):
    log.debug("Starting server....")
    try:
      self.__werkzeug_server.serve_forever()
    except Exception as e:
      log.exception("Got exception in REST-API loop: %s" % e)

  def shutdown (self):
    log.debug("Shutdown server...")
    self.__werkzeug_server.shutdown()


class AbstractLayerResourceHandler(Resource):
  """
  """
  LAYER_NAME = None
  GET_RPCS = ['ping', 'version']
  POST_RPCS = ['ping']

  def __init__ (self, layer_api):
    self.layer_api = layer_api

  def get (self, rpc):
    if rpc not in self.GET_RPCS:
      raise RuntimeError("RPC name: %s is not allowed!" % rpc)
    return self._process_rpc(rpc)

  def post (self, rpc):
    if rpc not in self.POST_RPCS:
      raise RuntimeError("RPC name: %s is not allowed!" % rpc)
    return self._process_rpc(rpc)

  def _process_rpc (self, rpc):
    if rpc == 'version':
      return {'name': __project__, 'version': get_escape_version()}
    if rpc == 'ping':
      return ("OK", 200) if self.layer_api.is_up else ("INITIALIZING", 202)
    else:
      return self.layer_api.proceed_API_call(self.LAYER_NAME, rpc=rpc)


class OrchestrationLayerResourceHandler(AbstractLayerResourceHandler):
  """
  """
  LAYER_NAME = 'orchestration'
  GET_RPCS = ['get-config'] + AbstractLayerResourceHandler.GET_RPCS
  POST_RPCS = ['get-config',
               'edit-config'] + AbstractLayerResourceHandler.POST_RPCS

  def __init__ (self, *args, **kwargs):
    super(OrchestrationLayerResourceHandler, self).__init__(*args, **kwargs)


class ServiceLayerResourceHandler(OrchestrationLayerResourceHandler):
  pass


class AdaptationLayerResourceHandler(OrchestrationLayerResourceHandler):
  pass
