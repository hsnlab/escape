# Copyright 2015 Janos Czentye <czentye@tmit.bme.hu>
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
Contains manager and handling functions for global ESCAPE configuration.
"""
import collections
import importlib
import json
import os
import pprint
from distutils.util import strtobool

from escape.adapt import LAYER_NAME as ADAPT
from escape.infr import LAYER_NAME as INFR
from escape.orchest import LAYER_NAME as ORCHEST
from escape.service import LAYER_NAME as SERVICE
from escape.util.misc import Singleton, VERBOSE, unicode_to_str
from pox.core import log, core

# Store the project root where escape.py is started in
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__) + "/../../../")


class ConfigurationError(RuntimeError):
  """
  Error class for signaling errors related to configuration load, parse etc.
  """
  pass


class ESCAPEConfig(object):
  """
  Wrapper class for configuration to hide specialties with respect to storing,
  loading, parsing and getting special data.

  Contains functions for config handling and manipulation.

  Should be instantiated once!
  """
  # Singleton
  __metaclass__ = Singleton
  """Singleton"""
  # Predefined layer names
  LAYERS = (SERVICE, ORCHEST, ADAPT, INFR)
  """Predefined layer names"""
  # Default additional config name
  DEFAULT_CONFIG_FILE = "escape.config"  # relative to project root
  """Path of the default config file"""

  def __init__ (self, default=None):
    """
    Init configuration from given data or an empty dict.

    :param default: default configuration
    :type default: dict
    :return: None
    """
    # Store copy of project root directory
    self.project_root = str(PROJECT_ROOT)
    self.__initiated = False
    if default:
      self.__configuration = default
    else:
      self.__initialize_from_file(path=self.DEFAULT_CONFIG_FILE)

  @property
  def in_initiated (self):
    """
    Return True if config is initiated.

    :return: initiated or not
    :rtype: bool
    """
    return self.__initiated

  def add_cfg (self, cfg):
    """
    Override configuration.

    :param cfg: new configuration
    :type cfg: dict
    :return: None
    """
    if isinstance(cfg, dict) and cfg:
      self.__configuration = cfg

  def __initialize_from_file (self, path):
    """
    Initialize the config from a file given by ``path``.
    
    :param path: config file path
    :type path: str
    :return: None
    """
    # Load file
    path = os.path.join(PROJECT_ROOT, path)
    log.info("Load default config from file: %s" % path)
    try:
      with open(path) as f:
        self.__configuration = json.load(f, object_hook=unicode_to_str)
    except IOError:
      log.warning('Default config file: %s is not found!' % path)
      self.__configuration = dict.fromkeys(self.LAYERS, {})

  def load_config (self, config=None):
    """
    Load static configuration from file if it exist or leave the default intact.

    .. note::
      The CONFIG is updated per data under the Layer entries. This means that
      the minimal amount of data have to given is the hole sequence or
      collection under the appropriate key. E.g. the hole data under the
      'STRATEGY' key in 'orchestration' layer.

    :param config: config file name relative to pox.py (optional)
    :type config: str
    :return: self
    :rtype: :class:`ESCAPEConfig`
    """
    if self.__initiated:
      return self
    if config:
      # Config is set directly
      log.info("Load explicitly given config file: %s" % config)
    elif hasattr(core, "CONFIG_FILE_NAME"):
      # Config is set through POX's core object by a topmost module (unify)
      config = getattr(core, "CONFIG_FILE_NAME")
      log.info("Load explicitly given config file: %s" % config)
    else:
      # No config file has been given
      log.debug("No additional configuration has been given!")
    try:
      if config:
        # Load file
        with open(os.path.abspath(config), 'r') as f:
          cfg = json.load(f, object_hook=unicode_to_str)
        # Iterate over layer config
        changed = False
        for layer in cfg:
          if layer in self.__configuration:
            if self.__parse_part(self.__configuration[layer], cfg[layer]):
              changed = True
        if changed:
          log.info("Running configuration has been updated from file!")
    except IOError:
      log.error("Additional configuration file not found: %s" % config)
    except ValueError as e:
      log.error("An error occurred when load configuration: %s" % e)
    # Register config into pox.core to be reachable for other future
    # components -not used currently
    self.__initiated = True
    core.register("CONFIG", self)
    log.log(VERBOSE, "Running config:\n" + pprint.pformat(self.__configuration))
    return self

  def __parse_part (self, inner_part, loaded_part):
    """
    Inner function to parse and check a part of configuration and update the
    stored one according the detected changes.
    Uses recursion.

    :param inner_part: part of inner representation of config (CONFIG)
    :type inner_part: dict
    :param loaded_part: part of loaded configuration (escape.config)
    :type loaded_part: collections.Mapping
    :return: original config is changed or not.
    :rtype: bool
    """
    changed = False
    # If parsed part is not None or empty dict/tuple/list
    if loaded_part:
      # Iterating over the structure
      for key, value in loaded_part.iteritems():
        # If the loaded value is a dict
        if isinstance(value, collections.Mapping):
          # If we need to check deeper
          if key in inner_part:
            # Recursion
            changed = self.__parse_part(inner_part[key], value)
          # If no entry in CONFIG just copying
          else:
            # Add the new value(dict) to the inner part
            inner_part[key] = value
            # Config updated
            changed = True
        # If the loaded value is a str/tuple/list
        else:
          # If there is a default value for this key
          if key in inner_part:
            # If it is not the same
            if isinstance(value, (tuple, list)):
              if set(inner_part[key]) != set(value):
                # Config overrided
                inner_part[key] = value
                changed = True
            else:
              if inner_part[key] != value:
                # Config overrided
                inner_part[key] = value
                changed = True
          else:
            # Config updated
            inner_part[key] = value
            changed = True
    return changed

  def dump (self):
    """
    Return with the entire configuration in JSON.

    :return: config
    :rtype: str
    """
    import json

    print json.dumps(self.__configuration, indent=4)

  def is_layer_loaded (self, layer):
    """
    Return the value given UNIFY's layer is loaded or not.

    :param layer: layer name
    :type layer: str
    :return: layer condition
    :rtype: bool
    """
    return self.__configuration[layer].get('LOADED', False)

  def set_layer_loaded (self, layer):
    """
    Set the given layer LOADED value.

    :param layer: layer name
    :type layer: str
    :return: None
    """
    if not self.__initiated:
      self.load_config()
    self.__configuration[layer]['LOADED'] = True

  def __getitem__ (self, item):
    """
    Can be used the config as a dictionary: CONFIG[...]

    :param item: layer key
    :type item: str
    :return: layer config
    :rtype: dict
    """
    if not isinstance(item, basestring):
      raise TypeError("Unsupported operand type: Layer name must be str")
    elif item not in self.LAYERS:
      raise KeyError("No layer is defined with the name: %s" % item)
    else:
      return self.__configuration[item]

  def __setitem__ (self, key, value):
    """
    Disable explicit layer config modification.

    :raise: :any:`exceptions.RuntimeError`
    """
    raise RuntimeError("Explicit layer config modification is not supported!")

  def __delitem__ (self, key):
    """
    Disable explicit layer config deletion.

    :raise: :any:`exceptions.RuntimeError`
    """
    raise RuntimeError("Explicit layer config deletion is not supported!")

  def get_project_root_dir (self):
    """
    Return the absolute path of project dir.

    :return: path of project dir
    :rtype: str
    """
    return self.project_root

  ##############################################################################
  # Mapping related getters
  ##############################################################################

  def get_mapping_enabled (self, layer):
    """
    Return the mapping process is enabled for the ``layer`` or not.

    :param layer: layer name
    :type layer: str
    :return: enabled value (default: True)
    :rtype: bool
    """
    try:
      return self.__configuration[layer]['MAPPER']['mapping-enabled']
    except KeyError:
      return True

  def get_mapping_config (self, layer):
    """
    Return the mapping config for the ``layer`` or not.

    :param layer: layer name
    :type layer: str
    :return: config parameters for main mapper function (default: empty dict)
    :rtype: dict
    """
    try:
      return self.__configuration[layer]['MAPPER']['mapping-config']
    except (KeyError, AttributeError):
      return {}

  def get_strategy (self, layer):
    """
    Return with the Strategy class of the given layer.

    :param layer: layer name
    :type layer: str
    :return: Strategy class
    :rtype: :any:`AbstractMappingStrategy`
    """
    try:
      return getattr(importlib.import_module(
        self.__configuration[layer]['STRATEGY']['module']),
        self.__configuration[layer]['STRATEGY']['class'], None)
    except (KeyError, AttributeError, TypeError):
      return None

  def get_mapper (self, layer):
    """
    Return with the Mapper class of the given layer.

    :param layer: layer name
    :type layer: str
    :return: Mapper class
    :rtype: :any:`AbstractMapper`
    """
    try:
      return getattr(importlib.import_module(
        self.__configuration[layer]['MAPPER']['module']),
        self.__configuration[layer]['MAPPER']['class'], None)
    except (KeyError, AttributeError, TypeError):
      return None

  def get_mapping_processor (self, layer):
    """
    Return with Validator class of the given layer.

    :param layer: layer name
    :type layer: str
    :return: Validator class
    :rtype: :any:`AbstractMappingDataProcessor`
    """
    try:
      return getattr(importlib.import_module(
        self.__configuration[layer]['PROCESSOR']['module']),
        self.__configuration[layer]['PROCESSOR']['class'], None)
    except (KeyError, AttributeError, TypeError):
      return None

  def get_processor_enabled (self, layer):
    """
    Return the mapping process is enabled for the ``layer`` or not.

    :param layer: layer name
    :type layer: str
    :return: enabled value (default: True)
    :rtype: bool
    """
    try:
      return self.__configuration[layer]['PROCESSOR']['enabled']
    except KeyError:
      return False

  def get_threaded (self, layer):
    """
    Return with the value if the mapping strategy is needed to run in
    separated thread or not. If value is not defined: return False.

    :param layer: layer name
    :type layer: str
    :return: threading value
    :rtype: bool
    """
    try:
      return self.__configuration[layer]['STRATEGY']['THREADED']
    except KeyError:
      return False

  def get_api_virtualizer (self, layer_name, api_name):
    """
    Return the type of the assigned Virtualizer.

    :param layer_name: main layer of the API
    :type layer_name: str
    :param api_name: name of the REST-API in the global config.
    :type api_name: str
    :return: type of the Virtualizer as in :any:`VirtualizerManager`
    :rtype: str
    """
    try:
      return self.__configuration[layer_name][api_name]["virtualizer_type"]
    except (KeyError, AttributeError, TypeError):
      return None

  ##############################################################################
  # SERVICE layer getters
  ##############################################################################

  def get_service_layer_id (self):
    """
    Return with the identifications value of the Service Layer.

    :return: service id
    :rtype: str
    """
    try:
      return self.__configuration[SERVICE]["SERVICE-LAYER-ID"]
    except KeyError:
      return None

  def get_sas_api_class (self):
    """
    Return with the request handler class of Service Layer REST API.

    :return: REST API class
    :rtype: :any:`AbstractRequestHandler`
    """
    try:
      return getattr(importlib.import_module(
        self.__configuration[SERVICE]["REST-API"]['module']),
        self.__configuration[SERVICE]["REST-API"]['class'], None)
    except KeyError:
      return None

  def get_sas_agent_params (self):
    """
    Return the Cf-Or API params for agent request handler.

    :return: params
    :rtype: dict
    """
    try:
      params = self.__configuration[SERVICE]["REST-API"].copy()
      del params['module']
      del params['class']
      return params
    except KeyError:
      return {}

  def get_sas_request_delay (self):
    """
    Return the default delay value for service request parsing from file.

    :return: delay
    :rtype: int
    """
    try:
      return int(
        self.__configuration[SERVICE]["SCHEDULED_SERVICE_REQUEST_DELAY"])
    except (KeyError, ValueError):
      return 0

  ##############################################################################
  # ORCHESTRATION layer getters
  ##############################################################################

  def get_ros_agent_class (self):
    """
    Return with the request handler class of Agent REST API.

    :return: agent class
    :rtype: :any:`AbstractRequestHandler`
    """
    try:
      return getattr(importlib.import_module(
        self.__configuration[ORCHEST]["Sl-Or"]['module']),
        self.__configuration[ORCHEST]["Sl-Or"]['class'], None)
    except KeyError:
      return None

  def get_ros_agent_params (self):
    """
    Return the REST API params for agent request handler.

    :return: params
    :rtype: dict
    """
    try:
      params = self.__configuration[ORCHEST]["Sl-Or"].copy()
      del params['module']
      del params['class']
      return params
    except KeyError:
      return {}

  def get_cfor_api_class (self):
    """
    Return with the request handler class of Cf-Or REST API.

    :return: REST API class
    :rtype: :any:`AbstractRequestHandler`
    """
    try:
      return getattr(importlib.import_module(
        self.__configuration[ORCHEST]["Cf-Or"]['module']),
        self.__configuration[ORCHEST]["Cf-Or"]['class'], None)
    except KeyError:
      return None

  def get_cfor_agent_params (self):
    """
    Return the Cf-Or API params for agent request handler.

    :return: params
    :rtype: dict
    """
    try:
      params = self.__configuration[ORCHEST]["Cf-Or"].copy()
      del params['module']
      del params['class']
      return params
    except KeyError:
      return {}

  ##############################################################################
  # ADAPTATION layer getters
  ##############################################################################

  def get_component (self, component, parent=None):
    """
    Return with the class of the adaptation component.

    :param component: component name
    :type component: str
    :param parent: define the parent of the actual component's configuration
    :type parent: dict
    :return: component class
    """
    try:
      comp = self.__configuration[ADAPT][component] if parent is None \
        else parent[component]
      return getattr(importlib.import_module(comp['module']), comp['class'])
    except KeyError:
      return None

  def get_component_params (self, component, parent=None):
    """
    Return with the initial parameters of the given component defined in CONFIG.
    The param's name must be identical with the attribute name of the component
    constructor.

    :param component: component name
    :type component: str
    :param parent: define the parent of the actual component's configuration
    :type parent: dict
    :return: initial params
    :rtype: dict
    """
    try:
      params = self.__configuration[ADAPT][component] \
        if parent is None else parent[component]
    except KeyError:
      return {}
    try:
      # FIXME - what if there are not module and class???
      params = params.copy()
      del params['module']
      del params['class']
    except KeyError:
      pass
    return params

  def get_managers (self):
    """
    Return the default DomainManagers for initialization on start.

    :return: list of :any:`AbstractDomainManager`
    :rtype: list
    """
    try:
      return self.__configuration[ADAPT]['MANAGERS']
    except KeyError:
      return ()

  def get_internal_manager (self):
    """
    Return with the Manager class which is detected as the Manager of the
    locally emulated Mininet-based network.

    Based on the IS_INTERNAL_MANAGER attribute of the defined DomainManager
    classes in the global config.

    :return: local manager name(s)
    :rtype: dict
    """
    internal_mgrs = []
    for item in self.__configuration[ADAPT].itervalues():
      if isinstance(item, dict) and 'module' in item and 'class' in item:
        try:
          mgr_class = getattr(importlib.import_module(item['module']),
                              item['class'])
          if mgr_class.IS_INTERNAL_MANAGER:
            internal_mgrs.append(
              item['domain_name'] if "domain_name" in item else
              mgr_class.DEFAULT_DOMAIN_NAME)
        except (KeyError, AttributeError, TypeError):
          return None
    return internal_mgrs if internal_mgrs else None

  def get_external_managers (self):
    """
    Return with Manager classes which is detected as external managers.

    Based on the IS_EXTERNAL_MANAGER attribute of the defined DomainManager
    classes in the global config.

    :return: external manager name(s)
    :rtype: dict
    """
    external_mgrs = []
    for item in self.__configuration[ADAPT].itervalues():
      if isinstance(item, dict) and 'module' in item and 'class' in item:
        try:
          mgr_class = getattr(importlib.import_module(item['module']),
                              item['class'])
          if mgr_class.IS_EXTERNAL_MANAGER:
            external_mgrs.append(
              item['domain_name'] if "domain_name" in item else
              mgr_class.DEFAULT_DOMAIN_NAME)
        except (KeyError, AttributeError, TypeError):
          return None
    return external_mgrs if external_mgrs else None

  def clear_domains_after_shutdown (self):
    """
    Return with the shutdown strategy to reset domain or not.

    :return: clear domain after shutdown or not (default: True)
    :rtype: bool
    """
    try:
      return self.__configuration[ADAPT]['CLEAR-DOMAINS-AFTER-SHUTDOWN']
    except KeyError:
      return True

  def reset_domains_before_install (self):
    """
    Return with the pre-deploy strategy to reset domain or not.

    :return: reset domain before install or not (default: False)
    :rtype: bool
    """
    try:
      return self.__configuration[ADAPT]['RESET-DOMAINS-BEFORE-INSTALL']
    except KeyError:
      return False

  def use_remerge_update_strategy (self):
    """
    Return True if the re-merge update strategy is enabled in DoV updating
    instead of using the straightforward step-by-step updating.

    :return: re-merge strategy is enabled or not (default: True)
    :rtype: bool
    """
    try:
      return self.__configuration[ADAPT]['USE-REMERGE-UPDATE-STRATEGY']
    except KeyError:
      return True

  def use_status_based_update (self):
    """
    Return True if the status based update strategy is enabled.
    This approach update DoV as a first step and use element status to update
    the domain.

    :return: status update strategy is enabled or not (default: False)
    :rtype: bool
    """
    try:
      return self.__configuration[ADAPT]['USE-STATUS-BASED-UPDATE']
    except KeyError:
      return False

  def ensure_unique_id (self):
    """
    Return with the ID generations strategy for nodes.
    If it is set, id of nodes will be generated with the domain name as a
    prefix to ensure unique id globally.

    :return: id generation strategy (default: False)
    :rtype: bool
    """
    try:
      return self.__configuration[ADAPT]['ENSURE-UNIQUE-ID']
    except KeyError:
      return False

  def get_sdn_topology (self):
    """
    Return the path of the SDN topology config file.

    :return:  path of topology config file
    :rtype: str
    """
    try:
      # Project root dir relative to this module which is/must be under root
      # util/escape/ext/pox/root
      return os.path.abspath(
        os.path.join(self.get_project_root_dir(),
                     self.__configuration[ADAPT]["SDN"]["TOPOLOGY"]["path"]))
    except KeyError:
      return None

  ##############################################################################
  # INFRASTRUCTURE layer getters
  ##############################################################################

  def get_mn_network_opts (self):
    """
    Return the optional Mininet parameters for initiation.

    :return: optional constructor params (default: empty dict)
    :rtype: dict
    """
    try:
      mn_opts = self.__configuration[INFR]['NETWORK-OPTS']
      return mn_opts if mn_opts is not None else {}
    except KeyError:
      return {}

  def get_mininet_topology (self):
    """
    Return the Mininet topology class.

    :return:  topo class
    """
    try:
      # Project root dir relative to this module which is/must be under pox/ext
      return os.path.abspath(os.path.join(self.get_project_root_dir(),
                                          self.__configuration[INFR]["TOPO"]))
    except KeyError:
      return None

  def get_fallback_topology (self):
    """
    Return the fallback topology class.

    :return: fallback topo class
    :rtype: :any::`AbstractTopology`
    """
    try:
      return getattr(importlib.import_module(
        self.__configuration[INFR]["FALLBACK-TOPO"]['module']),
        self.__configuration[INFR]["FALLBACK-TOPO"]['class'], None)
    except KeyError:
      return None

  def get_clean_after_shutdown (self):
    """
    Return with the value if a cleaning process need to be done or not.

    :return: cleanup (default: False)
    :rtype: bool
    """
    try:
      return strtobool(str(self.__configuration[INFR]['SHUTDOWN-CLEAN']))
    except KeyError:
      return False

  def get_SAP_xterms (self):
    """
    Return the value if need to initiate xtemrs assigned to SAPs.

    :return: xterms
    :rtype: bool
    """
    try:
      return self.__configuration[INFR]["SAP-xterms"]
    except (KeyError, AttributeError, TypeError):
      return True

  def get_manage_neo4j_service (self):
    """
    Return the value if neo4j needs to be managed by ESCAPE.

    :return: manage_neo4j_service
    :rtype: bool
    """
    try:
      return self.__configuration[ORCHEST]["manage-neo4j-service"]
    except (KeyError, AttributeError, TypeError):
      return False

  def get_Controller_params (self):
    """
    Return the additional parameter which are forwarded to the constructor of
    the specific :any:`InternalControllerProxy` class during Mininet building.

    :return: additional parameters as a dict (default: empty dict)
    :rtype: dict
    """
    try:
      cfg = self.__configuration[INFR]["Controller"]
      return cfg if cfg is not None else {}
    except (KeyError, AttributeError, TypeError):
      return {}

  def get_EE_params (self):
    """
    Return the additional parameter which are forwarded to the constructor of
    the :class:`mininet.node.EE` class during Mininet building.

    :return: additional parameters as a dict (default: empty dict)
    :rtype: dict
    """
    try:
      cfg = self.__configuration[INFR]["EE"]
      return cfg if cfg is not None else {}
    except (KeyError, AttributeError, TypeError):
      return {}

  def get_Switch_params (self):
    """
    Return the additional parameter which are forwarded to the constructor of
    the specific :class:`mininet.node.Switch` class during Mininet building.

    :return: additional parameters as a dict (default: empty dict)
    :rtype: dict
    """
    try:
      cfg = self.__configuration[INFR]["Switch"]
      return cfg if cfg is not None else {}
    except (KeyError, AttributeError, TypeError):
      return {}

  def get_SAP_params (self):
    """
    Return the additional parameter which are forwarded to the constructor of
    the :class:`mininet.node.Host` class during Mininet building.

    :return: additional parameters as a dict (default: empty dict)
    :rtype: dict
    """
    try:
      cfg = self.__configuration[INFR]["SAP"]
      return cfg if cfg is not None else {}
    except (KeyError, AttributeError, TypeError):
      return {}

  def get_Link_params (self):
    """
    Return the additional parameter which are forwarded to the constructor of
    the :class:`mininet.node.Link` class during Mininet building.

    :return: additional parameters as a dict (default: empty dict)
    :rtype: dict
    """
    try:
      cfg = self.__configuration[INFR]["Link"]
      return cfg if cfg is not None else {}
    except (KeyError, AttributeError, TypeError):
      return {}

  ##############################################################################
  # Visualizations layer getters
  ##############################################################################

  def get_visualization_url (self):
    """
    Return the url of the remote Visualization server.

    :return: url
    :rtype: str
    """
    try:
      return self.__configuration["visualization"]["url"]
    except KeyError:
      return None

  def get_visualization_rpc (self):
    """
    Return the url of the remote Visualization server.

    :return: url
    :rtype: str
    """
    try:
      return self.__configuration["visualization"]["rpc"]
    except KeyError:
      return None

  def get_visualization_instance_id (self):
    """
    Return the instance id of the current ESCAPEv2.

    :return: url
    :rtype: str
    """
    try:
      return self.__configuration["visualization"]["instance_id"]
    except KeyError:
      return None
