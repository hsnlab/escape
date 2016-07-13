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
Unifying package for ESCAPEv2 functions.

'cfg' defines the default configuration settings such as the concrete
RequestHandler and strategy classes, the initial Adapter classes, etc.

`CONFIG` contains the ESCAPEv2 dependent configuration as an
:any:`ESCAPEConfig`.
"""
from escape.util.config import ESCAPEConfig, PROJECT_ROOT

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
__status__ = "prototype"

# Default configuration object which contains static and running
# configuration for Layer APIs, DomainManagers, Adapters and other components
cfg = {
  "service":  # Service Adaptation Sublayer
    {
      "SERVICE-LAYER-ID": "ESCAPE-SERVICE",
      # Mapping configuration
      "MAPPER":
        {
          "module": "escape.service.sas_mapping",
          "class": "ServiceGraphMapper",
          "mapping-config":
            {
              "full_remap": True
            },
          "mapping-enabled": False
        },
      "STRATEGY":
        {
          "module": "escape.service.sas_mapping",
          "class": "DefaultServiceMappingStrategy",
          "THREADED": False  # still experimental
        },
      "PROCESSOR":
        {
          "module": "escape.util.mapping",
          "class": "ProcessorSkipper",
          "enabled": False
        },
      # Interface / Upper layer related configuration
      "REST-API":
        {
          "module": "escape.service.sas_API",
          "class": "ServiceRequestHandler",
          "prefix": "escape",
          "address": "0.0.0.0",
          "port": 8008,
          "unify_interface": False
        }
    },
  "orchestration":  # Resource Orchestration Sublayer
    {
      # Mapping configuration
      "MAPPER":
        {
          "module": "escape.orchest.ros_mapping",
          "class": "ResourceOrchestrationMapper",
          "mapping-config":
            {
              "full_remap": True
            },
          "mapping-enabled": True
        },
      "STRATEGY":
        {
          "module": "escape.orchest.ros_mapping",
          "class": "ESCAPEMappingStrategy",
          "THREADED": False  # still experimental
        },
      "PROCESSOR":
        {
          "module": "escape.util.mapping",
          "class": "ProcessorSkipper",
          "enabled": True
        },
      # Interface / Upper layer related configuration
      "ESCAPE-SERVICE":
        {
          # "virtualizer_type": "SINGLE"
          "virtualizer_type": "GLOBAL"
        },
      "Sl-Or":
        {
          "module": "escape.orchest.ros_API",
          "class": "ROSAgentRequestHandler",
          "prefix": "escape",
          "address": "0.0.0.0",
          "port": 8888,
          "virtualizer_type": "SINGLE",
          # "virtualizer_type": "GLOBAL",
          "unify_interface": True,
          "diff": True
        },
      "Cf-Or":
        {
          "module": "escape.orchest.ros_API",
          "class": "CfOrRequestHandler",
          "prefix": "cfor",
          "address": "0.0.0.0",
          "port": 8889,
          "virtualizer_type": "GLOBAL",
          "unify_interface": True
        }
    },
  "adaptation":  # Controller Adaptation Sublayer
    {
      # Default managers need to start at init
      "MANAGERS": [
        # "REMOTE-ESCAPE",
        # "REMOTE-ESCAPE-ext",
        # "SDN",
        # "OPENSTACK",
        # "UN"
        # "DOCKER"
      ],
      "RESET-DOMAINS-BEFORE-INSTALL": False,
      "CLEAR-DOMAINS-AFTER-SHUTDOWN": False,  # Shutdown strategy config
      # Use re-merge instead of straightforward update when updating DoV
      "USE-REMERGE-UPDATE-STRATEGY": True,
      "ENSURE-UNIQUE-ID": True,  # ID conversion strategy for nodes
      # Specific Domain Managers
      "INTERNAL":
        {
          "module": "escape.adapt.managers",
          "class": "InternalDomainManager",
          "poll": False,
          # Specific Domain Adapters for DomainManager
          "adapters": {
            "CONTROLLER":
              {
                "module": "escape.adapt.adapters",
                "class": "InternalPOXAdapter",
                "name": None,
                "address": "127.0.0.1",
                "port": 6653,
                "keepalive": False
              },
            "TOPOLOGY":
              {
                "module": "escape.adapt.adapters",
                "class": "InternalMininetAdapter",
                "net": None
              },
            "MANAGEMENT":
              {
                "module": "escape.adapt.adapters",
                "class": "VNFStarterAdapter",
                "username": "mininet",
                "password": "mininet",
                "server": "127.0.0.1",
                "port": 830,
                "timeout": 5
              }
          }
        },
      "SDN": {
        "module": "escape.adapt.managers",
        "class": "SDNDomainManager",
        "poll": False,
        "domain_name": "SDN-MICROTIK",
        "adapters": {
          "CONTROLLER":
            {
              "module": "escape.adapt.adapters",
              "class": "SDNDomainPOXAdapter",
              "name": None,
              "address": "0.0.0.0",
              "port": 6633,
              "keepalive": False,
              "binding": {
                "MT1": 0x14c5e0c376e24,
                "MT2": 0x14c5e0c376fc6,
              }
            },
          "TOPOLOGY":
            {
              "module": "escape.adapt.adapters",
              "class": "SDNDomainTopoAdapter",
              "path": "examples/sdn-topo.nffg"  # relative to project root
            }
        }
      },
      "REMOTE-ESCAPE":
        {
          "module": "escape.adapt.managers",
          "class": "RemoteESCAPEDomainManager",
          "poll": False,
          "diff": True,
          "adapters": {
            "REMOTE":
              {
                "module": "escape.adapt.adapters",
                "class": "RemoteESCAPEv2RESTAdapter",
                "url": "http://192.168.50.128:8888",
                "prefix": "escape",
                "unify_interface": True
              }
          }
        },
      "REMOTE-ESCAPE-ext":
        {
          "module": "escape.adapt.managers",
          "class": "UnifyDomainManager",
          "domain_name": "extESCAPE",
          "poll": False,
          "diff": True,
          "adapters": {
            "REMOTE":
              {
                "module": "escape.adapt.adapters",
                "class": "UnifyRESTAdapter",
                "url": "http://192.168.50.129:8888",
                "prefix": "escape",
              }
          }
        },
      "OPENSTACK":
        {
          "module": "escape.adapt.managers",
          "class": "OpenStackDomainManager",
          "poll": False,
          "diff": True,
          "adapters": {
            "REMOTE":
              {
                "module": "escape.adapt.adapters",
                "class": "UnifyRESTAdapter",
                "url": "http://localhost:8081",
                "timeout": 5
              }
          }
        },
      "UN":
        {
          "module": "escape.adapt.managers",
          "class": "UniversalNodeDomainManager",
          "poll": False,
          "diff": True,
          "adapters": {
            "REMOTE":
              {
                "module": "escape.adapt.adapters",
                "class": "UnifyRESTAdapter",
                "url": "http://localhost:8082"
              }
          }
        },
      "DOCKER":
        {
          "module": "escape.adapt.managers",
          "class": "UnifyDomainManager",
          "poll": False,
          "diff": True,
          "adapters": {
            "REMOTE":
              {
                "module": "escape.adapt.adapters",
                "class": "UnifyRESTAdapter",
                "url": "http://192.168.0.121:8888"
              }
          }
        }
    },
  "infrastructure":  # Infrastructure Layer
    {
      "TOPO": "examples/escape-mn-topo.nffg",  # relative to project root
      "NETWORK-OPTS": {  # Additional opts for Mininet
      },
      "Controller": {  # Additional params for InternalControllerProxy
        "ip": "127.0.0.1",
        "port": 6653
      },
      "EE": None,  # Additional params for EE creator func
      "Switch": None,  # Additional params for Switch creator func
      "SAP": None,  # Additional params for SAP creator func
      "Link": None,  # Additional params for Link creator func
      "FALLBACK-TOPO":  # relative to project root
        {
          "module": "escape.infr.topology",
          "class": "FallbackDynamicTopology"
        },
      "SAP-xterms": True,
      "SHUTDOWN-CLEAN": True
    },
  "additional-config-file": "escape.config",  # relative to project root
  "visualization":
    {
      "url": "http://localhost:8081",
      "rpc": "edit-config",
      "instance_id": None
    }
}

ADDITIONAL_DIRS = ("unify_virtualizer",  # Virtualizer lib
                   "mapping",  # Mapping algorithm
                   "mininet"  # Tweaked Mininet for Click-Mininet Infrastructure
                   )

def add_dependencies ():
  """
  Add dependency directories to PYTHONPATH.
  Dependencies are directories besides the escape.py initial script except pox.

  :return: None
  """
  import os
  import sys
  from pox.core import log

  # Skipped folders under project's root
  skipped = ("escape", "examples", "pox", "OpenYuma", "Unify_ncagent", "tools",
             "gui", "hwloc2nffg", "nffg_BME", "include", "share", "lib", "bin",
             "dummy-orchestrator")
  for sub_folder in os.listdir(PROJECT_ROOT):
    abs_sub_folder = os.path.join(PROJECT_ROOT, sub_folder)
    if not os.path.isdir(abs_sub_folder):
      continue
    if not (sub_folder.startswith('.') or sub_folder.upper().startswith(
       'PYTHON')) and sub_folder in ADDITIONAL_DIRS:
      if abs_sub_folder not in sys.path:
        log.debug("Add dependency: %s" % abs_sub_folder)
        sys.path.insert(0, abs_sub_folder)
      else:
        log.debug("Dependency: %s already added." % abs_sub_folder)


# Detect and add dependency directories
add_dependencies()

# Define global configuration and try to load additions from file
CONFIG = ESCAPEConfig(cfg).load_config()
