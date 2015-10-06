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
Generates increasingly bigger/more Service Chain requirements for a 
network topology, reports how well the algorithm performed.
"""

import CarrierTopoBuilder
import MappingAlgorithms
import UnifyExceptionTypes as uet
import random, math, traceback, sys, logging, getopt

try:
  from escape.util.nffg import NFFG
except ImportError:
  import sys, os, inspect

  sys.path.insert(0, os.path.join(os.path.abspath(os.path.realpath(
    os.path.abspath(
      os.path.split(inspect.getfile(inspect.currentframe()))[0])) + "/.."),
                                  "pox/ext/escape/util/"))
  from nffg import NFFG

def gen_seq():
  while True:
    yield int(math.floor(random.random() * 999999999))

log = logging.getLogger("StressTest")
logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)s:%(name)s:%(message)s')
all_saps_beginning = []
all_saps_ending = []
running_nfs = {}
test_lvl = 1

helpmsg = """StressTest.py options are:
   -h                Print this message help message.
   --loops           All Service Chains will be loops.
   --fullremap       Ignores all VNF mappings in the substrate network.
   --vnf_sharing=p   Sets the ratio of shared and not shared VNF-s.
   --request_seed=i  Provides seed for the random generator.

   --bw_factor=f     Controls the importance between bandwidth, infra resources
   --res_factor=f    and distance in latency during the mapping process. The
   --lat_factor=f    factors are advised to be summed to 3, if any is given the
                     others are calculated based on this criteria.
"""

def generateRequestForCarrierTopo(networkparams, seed, loops=False, 
                                  vnf_sharing_probabilty=0.0):
  """
  By default generates VNF-disjoint SC-s starting/ending only once in each SAP.
  With the 'loops' option, only loop SC-s are generated.
  'vnf_sharing_probabilty' determines the ratio of 
     #(VNF-s used by at least two SC-s)/#(not shared VNF-s).
  """
  chain_maxlen = 10
  random.seed(seed)
  random.shuffle(all_saps_beginning)
  random.shuffle(all_saps_ending)
  # generate some VNF-s connecting two SAP-s
  while len(all_saps_ending) > 1 and len(all_saps_beginning) > 1:
    nffg = NFFG(id="Benchmark-Req-"+str(test_lvl))
    # find two SAP-s for chain ends.
    sap1 = nffg.add_sap(id = all_saps_beginning.pop())
    sap2 = None
    if loops:
      sap2 = sap1
    else:
      tmpid = all_saps_ending.pop()
      while True:
        if tmpid != sap1.id:
          sap2 = nffg.add_sap(id = tmpid)
          break
        else:
          tmpid = all_saps_ending.pop()
    sg_path = []
    sap1port = sap1.add_port()
    last_req_port = sap1port
    for vnf in xrange(0, next(gen_seq()) % chain_maxlen + 1):
      if random.random() < vnf_sharing_probabilty and len(running_nfs) > 0:
        p = random.random()
        sumlen = sum([n*len(running_nfs[n]) for n in running_nfs])
        i = 1
        ratio = float(len(running_nfs[i])) / sumlen
        while ratio < p:
          i += 1
          ratio += float(i*len(running_nfs[i])) / sumlen
        nf = random.choice(running_nfs[i])
        while nf in nffg.nfs:
          nf = random.choice(running_nfs[i])
        nffg.add_node(nf)
      else:
        nf = nffg.add_nf(id="-".join(("SC",str(test_lvl),"VNF",
                         str(vnf))),
                         func_type=random.choice(['A','B','C']), 
                         cpu=random.randint(1,6),
                         mem=random.random()*1000,
                         storage=random.random()*3,
                         delay=1 + random.random()*10,
                         bandwidth=random.random())
      newport = nf.add_port()
      sglink = nffg.add_sglink(last_req_port, newport)
      sg_path.append(sglink.id)
      last_req_port = nf.add_port()

    sap2port = sap2.add_port()
    sglink = nffg.add_sglink(last_req_port, sap2port)
    sg_path.append(sglink.id)

    # WARNING: this is completly a wild guess! Failing due to this doesn't 
    # necessarily mean algorithm failure
    # Bandwidth maximal random value should be min(SAP1acces_bw, SAP2access_bw)
    # MAYBE: each SAP can only be once in the reqgraph?
    nffg.add_req(sap1port, sap2port, delay=random.uniform(20,100), 
                 bandwidth=random.random()*0.2, sg_path = sg_path)
    yield nffg
  yield None

def main(argv):
  try:
    opts, args = getopt.getopt(argv,"h",["loops", "fullremap", "bw_factor=",
                               "res_factor=", "lat_factor=", "request_seed=",
                               "vnf_sharing="])
  except getopt.GetoptError:
    print helpmsg
    sys.exit()
  loops = False
  fullremap = False
  vnf_sharing = 0.0
  seed = 3
  bw_factor = 1
  res_factor = 1
  lat_factor = 1
  for opt, arg in opts:
    if opt == '-h':
      print helpmsg
      sys.exit()
    elif opt == "--loops":
      loops = True
    elif opt == "--fullremap":
      fullremap = True
    elif opt == "--request_seed":
      seed = int(arg)
    elif opt == "--vnf_sharing":
      vnf_sharing = float(arg)
    elif opt == "--bw_factor":
      bw_factor = float(arg)
    elif opt == "--res_factor":
      res_factor = float(arg)
    elif opt == "--lat_factor":
      lat_factor = float(arg)
  """
  params, args = zip(*opts)
  if "bw_factor" not in params or "res_factor" not in params or \
     "bw_factor" not in params:
    raise Exception("Not all algorithm params are given!")
  """
  
  network, topoparams = CarrierTopoBuilder.getSmallTopo()
  max_test_lvl = 50000
  ever_successful = False
  global test_lvl
  global all_saps_ending
  global all_saps_beginning
  all_saps_ending = [s.id for s in network.saps]
  all_saps_beginning = [s.id for s in network.saps]
  try:
    while test_lvl < max_test_lvl:
      try:
        log.debug("Trying mapping with test level %s..."%test_lvl)
        for request in generateRequestForCarrierTopo(topoparams, seed, 
                       loops=loops, vnf_sharing_probabilty=vnf_sharing):
          # print request.dump()
          if test_lvl > max_test_lvl or request is None:
            break
          running_nfs[test_lvl] = [nf for nf in request.nfs 
                                   if nf.id.split("-")[1] == str(test_lvl)]
          network = MappingAlgorithms.MAP(request, network, 
                    full_remap=fullremap, enable_shortest_path_cache=True,
                    bw_factor=bw_factor, res_factor=res_factor,
                    lat_factor=lat_factor)
          ever_successful = True
          log.debug("Mapping successful on test level %s!"%test_lvl)
          test_lvl += 1
      except uet.MappingException as me:
        log.info("Mapping failed: %s"%me.msg)
        break
      if request is None:
        log.info("Request generation reached its end!")
        break
  except uet.UnifyException as ue:
    print ue.msg 
    print traceback.format_exc()
  except Exception as e:
    print traceback.format_exc()
  log.info("First unsuccessful mapping was at %s test level."%test_lvl)
  if ever_successful:
    print "Last successful mapping was at %s test level."%(test_lvl - 1)
    with open("paramsearch.out", "a") as f:
      f.write("\nLast successful mapping was at %s test level.\n"%(test_lvl - 1))
  else:
    print "Mapping failed at starting test level (%s)"%test_lvl

if __name__ == '__main__':
  main(sys.argv[1:])
