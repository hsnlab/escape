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
from escape.orchestration import LAYER_NAME
from escape.orchestration.policy_enforcement import PolicyEnforcementMetaClass
import pox.core as core

log = core.getLogger(LAYER_NAME)


class AbstractVirtualizer(object):
    """
    Abstract class for actual virtualizers

    Follows the Proxy design pattern
    """

    def __init__(self):
        pass


class ESCAPEVirtualizer(AbstractVirtualizer):
    """
    Actual virtualizer class for ESCAPE
    """

    __metaclass__ = PolicyEnforcementMetaClass

    def __init__(self):
        super(ESCAPEVirtualizer, self).__init__()

    def test_func(self):
        """
        Test function for policy checking debug. Should be removed soon.
        """
        print 'Invoke ESCAPEVirtualizer test_func'


class VirtualizerManager(object):
    """
    Store, handle and organize Virtualizer instances
    """

    def __init__(self):
        pass