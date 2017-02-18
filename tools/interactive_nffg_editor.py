#!/usr/bin/python -u
# Copyright 2017 Balazs Nemeth
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
# limitations under the License.nse
# along with POX. If not, see <http://www.gnu.org/licenses/>.

"""
Reads an input NFFG object into memory and starts an interactive Python
interpreter to edit the NFFG object. 
"""
import sys

try:
  from escape.nffg_lib.nffg import NFFG, NFFGToolBox
except ImportError:
  import os

  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                               "../escape/escape/nffg_lib/")))
  from nffg import NFFG, NFFGToolBox

if __name__ == '__main__':
  argv = sys.argv[1:]
  if "-h" in argv or "--help" in argv:
    print """
Reads an input NFFG object into memory and starts an interactive Python
interpreter to edit the NFFG object. The object can be accessed by 'nffg' name.
"""
  with open(argv[0], "r") as f:
    nffg = NFFG.parse(f.read())
