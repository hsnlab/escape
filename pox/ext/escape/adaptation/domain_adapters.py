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


class AbstractAdapter(object):
    """
    Abstract class for different domain adapters

    Follow the Adapter design pattern
    """
    def __init__(self):
        pass


class MininetDomainAdapter(AbstractAdapter):
    """
    Adapter class to handle communication with Mininet
    """
    def __init__(self):
        AbstractAdapter.__init__(self)


class POXControllerAdapter(AbstractAdapter):
    """
    Adapter class to handle communication with POX OpenFlow controller
    """
    def __init__(self):
        AbstractAdapter.__init__(self)


class OpenStckDomainAdapter(AbstractAdapter):
    """
    Adapter class to handle communication with OpenStack
    """
    def __init__(self):
        AbstractAdapter.__init__(self)