#!/usr/bin/python -u
#
# Copyright (c) 2016 Balazs Nemeth
#
# This file is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This file is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
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
