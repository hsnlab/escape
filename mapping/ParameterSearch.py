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
   -h              Print this help message.
   -o file         The base name for the output files. One output file is 
                   generated for every seed.
   --threads=i     Determines how many cores should be used at most at the same
                   time.
   --seeds=a,b,..  The sequence of seeds which should be used for the SC 
                   sequence generation. The length of the list determines how 
                   many should be executed.
   --param_number=i    Defines which parameter space point from a specific set 
                       shall be tested with all test sequences. If param_number
                       is given, --threads is ignored.
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
                            outfile, ["--vnf_sharing=0.2",
                                      "--multiple_scs",
                                      "--max_sc_count=3",
                                      "--request_seed="+s])
    oneLineInParameterSpace("--res_factor=", "--lat_factor=", "--bw_factor=", 
                            outfile, ["--vnf_sharing=0.2",
                                      "--multiple_scs",
                                      "--max_sc_count=3",
                                      "--request_seed="+s])
    oneLineInParameterSpace("--lat_factor=", "--bw_factor=", "--res_factor=", 
                            outfile, ["--vnf_sharing=0.2",
                                      "--multiple_scs",
                                      "--max_sc_count=3",
                                      "--request_seed="+s])
    semaphore.release()

def runAllTestSequences(par1, par2, par3, seeds, outfile):
  for s in seeds:
    basecmd = "python StressTest.py --request_seed="+str(s)
    comm = " ".join((basecmd,"--res_factor="+str(par1), 
                     "--bw_factor="+str(par2), "--lat_factor="+str(par3)))
    for seqtype in ["", " --vnf_sharing=0.2",
                    " --vnf_sharing=0.2 --multiple_scs --max_sc_count=3"]:
      typed_comm = comm + seqtype
      with open(outfile, "a") as f:
        f.write("\n Command under execution:\n %s"%typed_comm)
      typed_comm += " -o " + outfile
      os.system(typed_comm)

if __name__ == '__main__':
  try: 
    opts, args = getopt.getopt(sys.argv[1:],"ho:", ["threads=", "seeds=", 
                                                    "param_number="])
    baseoutfile = "paramsearch"
    threads = 1
    seedlist = [0,1]
    param_number = None
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
      elif opt == "--param_number":
        param_number = int(arg)
  except Exception as e:
    print traceback.format_exc()
    print helpmsg
    sys.exit()
  if param_number is not None:
    step = 0.375
    i = 0.0
    j = 0.0
    cnt = 0
    while i <= 3.0:
      while j <= 3.0 - i:
        if cnt == param_number:
          k = 3.0-i-j
          print i,j,k
          runAllTestSequences(i, j, k, seedlist, 
          "-".join((baseoutfile,str(i),str(j),str(k)))+".out")
          sys.exit()
        else:
          j += step
          cnt += 1
      i += step
      j = 0.0
  else:
    global semaphore
    launched_threads = 0
    semaphore = threading.Semaphore(threads)
    for s in seedlist:
      launched_threads += 1
      seq = TestSequence("Thread-"+str(launched_threads), 
                         baseoutfile, s)
      seq.start()
