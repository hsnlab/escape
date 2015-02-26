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

from escape.orchestration.virtualization_management import AbstractVirtualizer


class ControllerAdapter(object):
    """
    Higher-level class for NFFG adaptation between multiple domains
    """
    def __init__(self):
        pass


class DomainVirtualizer(AbstractVirtualizer):
    """
    Specific virtualizer class for global domain virtualization

    Should implement the same interface as AbstractVirtualizer
    """
    def __init__(self):
        AbstractVirtualizer.__init__(self)


class DomainResourceManager(object):
    """
    Handle and store global resources
    """
    def __init__(self):
        pass