# Copyright (c) 2015 Balazs Nemeth
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
Script for conveying a parameter search in the algorithm parameter space 
with different Service Request sequences. An input file shall be given to
the script where the result is written.
"""

import os, sys, copy, getopt

def oneLineInParameterSpace(factor1, factor2, factor3, outfile, other=[]):
  basecmd = "python StressTest.py"
  for additionalpar in other:
    basecmd += " " + additionalpar
  for par1 in (0.1*i for i in range(0,11)):
    par2 = par1
    par3 = 3.0 - par1 - par2
    comm = " ".join((basecmd,factor1+str(par1), 
                     factor2+str(par2), factor3+str(par3)))
  
    with open(outfile, "a") as f:
      f.write("\n Command under execution:\n %s"%comm)
    comm += " >> " + outfile
    os.system(comm)


if __name__ == '__main__':
  outfile = sys.argv[1]
  with open(outfile, "w") as f:
    pass
  oneLineInParameterSpace("--res_factor=", "--bw_factor=", "--lat_factor=", 
                          outfile)
  oneLineInParameterSpace("--res_factor=", "--lat_factor=", "--bw_factor=", 
                          outfile)
  oneLineInParameterSpace("--lat_factor=", "--bw_factor=", "--res_factor=", 
                          outfile)

  oneLineInParameterSpace("--res_factor=", "--bw_factor=", "--lat_factor=", 
                          outfile, ["--vnf_sharing=0.3"])
  oneLineInParameterSpace("--res_factor=", "--lat_factor=", "--bw_factor=", 
                          outfile, ["--vnf_sharing=0.3"])
  oneLineInParameterSpace("--lat_factor=", "--bw_factor=", "--res_factor=", 
                          outfile, ["--vnf_sharing=0.3"])

  oneLineInParameterSpace("--res_factor=", "--bw_factor=", "--lat_factor=", 
                          outfile, ["--loops"])
  oneLineInParameterSpace("--res_factor=", "--lat_factor=", "--bw_factor=", 
                          outfile, ["--loops"])
  oneLineInParameterSpace("--lat_factor=", "--bw_factor=", "--res_factor=", 
                          outfile, ["--loops"])
  

