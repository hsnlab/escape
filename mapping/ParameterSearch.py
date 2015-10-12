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

import os, sys, copy, getopt, traceback, threading

helpmsg = """ParameterSearch.py usage:
   -h       Print this help message.
"""

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
    comm += " -o " + outfile
    os.system(comm)


class TestSequence(threading.Thread):

  def __init__(self, threadname, base, s):
    threading.Thread.__init__(self)
    self.outfile = base + "-seed"+str(s)+".out"
    self.threadname = threadname
    self.s = s
  
  def run(self):
    s = str(self.s)
    outfile = self.outfile
    semaphore.acquire()
    with open(outfile, "w") as f:
      f.write(self.threadname+" seed: "+s)
    oneLineInParameterSpace("--res_factor=", "--bw_factor=", "--lat_factor=", 
                            outfile, ["--request_seed="+s])
    oneLineInParameterSpace("--res_factor=", "--lat_factor=", "--bw_factor=", 
                            outfile, ["--request_seed="+s])
    oneLineInParameterSpace("--lat_factor=", "--bw_factor=", "--res_factor=", 
                            outfile, ["--request_seed="+s])

    oneLineInParameterSpace("--res_factor=", "--bw_factor=", "--lat_factor=", 
                            outfile, ["--vnf_sharing=0.3", 
                                        "--request_seed="+s])
    oneLineInParameterSpace("--res_factor=", "--lat_factor=", "--bw_factor=", 
                            outfile, ["--vnf_sharing=0.3",
                                      "--request_seed="+s])
    oneLineInParameterSpace("--lat_factor=", "--bw_factor=", "--res_factor=", 
                            outfile, ["--vnf_sharing=0.3",
                                      "--request_seed="+s])

    oneLineInParameterSpace("--res_factor=", "--bw_factor=", "--lat_factor=", 
                            outfile, ["--loops",
                                      "--request_seed="+s])
    oneLineInParameterSpace("--res_factor=", "--lat_factor=", "--bw_factor=", 
                            outfile, ["--loops",
                                      "--request_seed="+s])
    oneLineInParameterSpace("--lat_factor=", "--bw_factor=", "--res_factor=", 
                            outfile, ["--loops",
                                      "--request_seed="+s])
    semaphore.release()

if __name__ == '__main__':
  try: 
    opts, args = getopt.getopt(sys.argv[1:],"ho:", ["threads=", "seeds="])
    baseoutfile = "paramsearch"
    threads = 1
    seedlist = [0,1]
    for opt, arg in opts:
      if opt == "-h":
        print helpmsg
        sys.exit()
      elif opt == "-o":
        baseoutfile = arg
      elif opt == "--threads":
        threads = int(arg)
      elif opt == "--seeds":
        seedlist = map(int, arg.split(","))
  except Exception as e:
    print traceback.format_exc()
    print helpmsg
    sys.exit()
  global semaphore
  launched_threads = 0
  semaphore = threading.Semaphore(threads)
  for s in seedlist:
    launched_threads += 1
    seq = TestSequence("Thread-"+str(launched_threads), 
                       baseoutfile, s)
    seq.start()
