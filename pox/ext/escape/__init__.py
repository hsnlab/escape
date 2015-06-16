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
Unifying package for ESCAPEv2 functions

`CONFIG` contains the ESCAPEv2 dependent configuration such as the concrete
RequestHandler and strategy classes, the initial Adapter classes, etc.
"""

__project__ = "ESCAPEv2"
__authors__ = "Janos Czentye, Balazs Sonkoly, Levente Csikor"
__copyright__ = "Copyright 2015, under Apache License Version 2.0"
__credits__ = "Janos Czentye, Balazs Sonkoly, Levente Csikor, Attila Csoma, " \
              "Felician Nemeth, Andras Gulyas, Wouter Tavernier, and Sahel " \
              "Sahhaf"
__license__ = "Apache License, Version 2.0"
__version__ = "2.0.0"
__maintainer__ = "Janos Czentye"
__email__ = "czentye@tmit.bme.hu"
__status__ = "Prototype"

# Configuration object which contains static and running configuration for
# Layer APIs, DomainManagers, Adapters and other components
CONFIG = {'service': {  # Service Adaptation Sublayer
                        'STRATEGY': 'DefaultServiceMappingStrategy',
                        'REQUEST-handler': 'ServiceRequestHandler',
                        'THREADED': True},
          'orchestration': {  # Resource Orchestration Sublayer
                              'STRATEGY': 'ESCAPEMappingStrategy',
                              'THREADED': True},
          'adaptation': {  # Controller Adaptation Sublayer
                           'INTERNAL': {'class': "InternalDomainManager",
                                        'listener-id': "InternalOFController"},
                           'POX': {'class': "POXDomainAdapter"},
                           'MININET': {'class': "MininetDomainAdapter"},
                           "VNFStarter": {"class": "VNFStarterAdapter",
                                          "agent": {"server": "192.168.12.128",
                                                    "port": 830,
                                                    "username": "mininet",
                                                    "password": "mininet"}},
                           'OPENSTACK': {'class': "OpenStackDomainAdapter"},
                           'DOCKER': {'class': "DockerDomainAdapter"}},
          'infrastructure': {}}


def load_config (config="escape.config"):
  """
  Load static configuration from file if it exist or leave the default intact

  :param config: config file name relative to pox.py (optional)
  :type config: str
  :return: None
  """
  from pox.core import log

  try:
    import json

    f = open(config, 'r')
    cfg = json.load(f)
    # Minimal syntax checking
    changed = []
    if len(cfg) > 0:
      for layer in CONFIG:
        if layer in cfg.keys() and len(cfg[layer]) > 0:
          CONFIG[layer].update(cfg[layer])
          changed.append(layer)
    if changed:
      log.info("Part(s) of running configuration has been loaded: %s", changed)
      return
  except IOError:
    log.debug("Configuration file not found!")
  except ValueError as e:
    log.error("An error occured when load configuration: %s" % e.message)
  log.info("Using default configuration...")


load_config()
