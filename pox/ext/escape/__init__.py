# Copyright 2015 Janos Czentye
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

`__version__` contains the actual version

`CONFIG` contains the ESCAPEv2 dependent configuration such as the concrete
RequestHandler and strategy classes, the initial Adapter classes, etc.
"""
__version__ = '2.0.0'
CONFIG = {'SMS': {  # Service Management Sublayer
                    'REQUEST-handler': 'ServiceRequestHandler'},  # REST-API
          'SAS': {  # Service Adaptation Sublayer
                    'STRATEGY': 'DefaultServiceMappingStrategy'},
          'ROS': {  # Resource Orchestration Sublayer
                    'STRATEGY': 'ESCAPEMappingStrategy'},
          'CAS': {  # Controller Adaptation Sublayer
                    'POX': 'POXDomainAdapter',  # POX Adapter
                    'MN': 'MininetDomainAdapter',  # Mininet Adapter
                    'OS': 'OpenStackDomainAdapter'}}  # OpenStack Adapter