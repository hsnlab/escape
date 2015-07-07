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

# Default configuration object which contains static and running
# configuration for Layer APIs, DomainManagers, Adapters and other components
cfg = {"service": {  # Service Adaptation Sublayer
                     "STRATEGY": {"module": "escape.service.sas_mapping",
                                  "class": "DefaultServiceMappingStrategy",
                                  "THREADED": True}},
       "orchestration": {  # Resource Orchestration Sublayer
                           "STRATEGY": {"module": "escape.orchest.ros_mapping",
                                        "class": "ESCAPEMappingStrategy",
                                        "THREADED": True}},
       "adaptation": {  # Controller Adaptation Sublayer
                        # Default managers need to start at init
                        "DEFAULTS": ("OPENSTACK",), # OpenStack Agent REST API
                        "AGENT": {"module": "escape.adapt.cas_API",
                                  "class": "AgentRequestHandler",
                                  "address": "0.0.0.0", "port": 8888,
                                  "prefix": "virtualizer"},
                        # Specific Domain Adapters for DomainManagers
                        "POX": {"module": "escape.adapt.components",
                                "class": "POXDomainAdapter",
                                "name": "InternalOFController"},
                        "MININET": {"module": "escape.adapt.components",
                                    "class": "MininetDomainAdapter"},
                        "VNFStarter": {"module": "escape.adapt.components",
                                       "class": "VNFStarterAdapter",
                                       "username": "mininet",
                                       "password": "mininet",
                                       "server": "192.168.12.128", "port": 830},
                        "OpenStack-REST": {"module": "escape.adapt.components",
                                           "class": "OpenStackRESTAdapter",
                                           "url": "http://localhost:8080"},
                        # Domain Managers
                        "INTERNAL": {"module": "escape.adapt.components",
                                     "class": "InternalDomainManager",
                                     "poll": True},
                        "OPENSTACK": {"module": "escape.adapt.components",
                                      "class": "OpenStackDomainManager",
                                      "poll": False},
                        "DOCKER": {"module": "escape.adapt.components",
                                   "class": "DockerDomainManager"}},
       "infrastructure": {  # Infrastructure Layer
                            "NETWORK-OPTS": None,  # Additional opts for Mininet
                            "FALLBACK-TOPO": {"module": "escape.infr.topology",
                                              "class": "BackupTopology"},
                            "SHUTDOWN-CLEAN": True},
       "additional-config-file": "escape.config"}


def add_dependencies ():
  """
  Add dependency directories to PYTHONPATH.
  Dependencies are directories besides the escape.py initial script except pox.

  :return: None
  """
  import os
  import sys
  from pox.core import core

  # Project root dir relative to unify.py top module which is/must be under
  # pox/ext
  root = os.path.abspath(os.path.dirname(__file__) + "../../../..")
  for item in os.listdir(root):
    abs_item = os.path.join(root, item)
    if not item.startswith('.') and item != "pox" and os.path.isdir(abs_item):
      sys.path.insert(0, abs_item)
      core.getLogger().debug("Add dependency: %s" % abs_item)

# Detect and add dependency directories
add_dependencies()

from escape.util.misc import ESCAPEConfig
# Define global configuration and try to load additions from file
CONFIG = ESCAPEConfig(cfg).load_config()
