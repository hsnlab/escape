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
# dictionary of newly added VNF-s keyed by the number of 'test_lvl' when it 
# was added.
running_nfs = {} 
test_lvl = 1

helpmsg = """StressTest.py options are:
   -h                Print this message help message.
   -o                The output file where the result shall be printed.
   --loops           All Service Chains will be loops.
   --fullremap       Ignores all VNF mappings in the substrate network.
   --vnf_sharing=p   Sets the ratio of shared and not shared VNF-s.
   --request_seed=i  Provides seed for the random generator.

   --bw_factor=f     Controls the importance between bandwidth, infra resources
   --res_factor=f    and distance in latency during the mapping process. The
   --lat_factor=f    factors are advised to be summed to 3, if any is given the
                     others shall be given too!

   --multiple_scs    One request will contain at least 2 chains with vnf sharing
                     probability defined by "--vnf_sharing" option.
   --max_sc_count=i  Determines how many chains should one request contain at 
                     most.
"""

def generateRequestForCarrierTopo(seed, loops=False, 
                                  vnf_sharing_probabilty=0.0,
                                  multiSC=False, max_sc_count=2):
  """
  By default generates VNF-disjoint SC-s starting/ending only once in each SAP.
  With the 'loops' option, only loop SC-s are generated.
  'vnf_sharing_probabilty' determines the ratio of 
     #(VNF-s used by at least two SC-s)/#(not shared VNF-s).
  """
  chain_maxlen = 10
  sc_count=1
  if multiSC:
    sc_count = random.randint(2,max_sc_count)
  while len(all_saps_ending) > sc_count and len(all_saps_beginning) > sc_count:
    nffg = NFFG(id="Benchmark-Req-"+str(test_lvl))
    # newly added NF-s of one request
    current_nfs = []
    for scid in xrange(0,sc_count):
      # find two SAP-s for chain ends.
      nfs_this_sc = []
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
      # generate some VNF-s connecting the two SAP-s
      vnf_cnt = next(gen_seq()) % chain_maxlen + 1
      for vnf in xrange(0, vnf_cnt):
        # in the first case p is used to determine which previous chain should 
        # be used to share the VNF, in the latter case it is used to determine
        # whether we should share now.
        vnf_added = False
        p = random.random()
        if random.random() < vnf_sharing_probabilty and len(running_nfs) > 0 \
           and not multiSC:
          sumlen = sum([n*len(running_nfs[n]) for n in running_nfs])
          i = 1
          ratio = float(len(running_nfs[i])) / sumlen
          while ratio < p:
            i += 1
            ratio += float(i*len(running_nfs[i])) / sumlen
          nf = random.choice(running_nfs[i])
          if reduce(lambda a,b: a and b, [v in nffg.nfs for v in running_nfs[i]]):
            # failing to add a VNF due to this criteria infuences the provided 
            # vnf_sharing_probabilty, but it is estimated to be insignificant, 
            # otherwise the generation can run into infinite loop!
            log.warn("All the VNF-s of the subchain selected for VNF sharing are"
                     " already in the current chain under construction! Skipping"
                     " VNF sharing...")
          else:
            while nf in nffg.nfs:
              nf = random.choice(running_nfs[i])
            nffg.add_node(nf)
            vnf_added = True
        elif multiSC and \
             p < vnf_sharing_probabilty and len(current_nfs) > 0:
          # this influences the the given VNF sharing probability...
          if reduce(lambda a,b: a and b, [v in nfs_this_sc for 
                                          v in current_nfs]):
            log.warn("All shareable VNF-s are already added to this chain! "
                     "Skipping VNF sharing...")
          else:
            nf = random.choice(current_nfs)
            while nf in nfs_this_sc:
              nf = random.choice(current_nfs)
            # the VNF is already in the subchain, we just need to add the links
            vnf_added = True
        else:
          nf = nffg.add_nf(id="-".join(("Test",str(test_lvl),"SC",str(scid),
                                        "VNF",str(vnf))),
                           func_type=random.choice(['A','B','C']), 
                           cpu=random.randint(1,6),
                           mem=random.random()*1000,
                           storage=random.random()*3,
                           delay=1 + random.random()*10,
                           bandwidth=random.random())
          vnf_added = True
        if vnf_added:
          # add olny the newly added VNF-s, not the shared ones.
          nfs_this_sc.append(nf)
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
      # MAYBE: each SAP can only be once in the reqgraph? - this is the case now.
      if multiSC:
        minlat = 5.0 * (len(nfs_this_sc) + 2)
        maxlat = 13.0 * (len(nfs_this_sc) + 2)
      else:
        nfcnt = len([i for i in nffg.nfs])
        minlat = 5.0 * (nfcnt + 2)
        maxlat = 13.0 * (nfcnt + 2)
      nffg.add_req(sap1port, sap2port, delay=random.uniform(minlat,maxlat), 
                   bandwidth=random.random()*0.2, sg_path = sg_path)
      # this prevents loops in the chains and makes new and old NF-s equally 
      # preferable in total for NF sharing
      new_nfs = [vnf for vnf in nfs_this_sc if vnf not in current_nfs]
      for tmp in xrange(0, scid+1):
        current_nfs.extend(new_nfs)
      if not multiSC:
        return nffg
    if multiSC:
      return nffg
  return None

def main(argv):
  try:
    opts, args = getopt.getopt(argv,"ho:",["loops", "fullremap", "bw_factor=",
                               "res_factor=", "lat_factor=", "request_seed=",
                               "vnf_sharing=", "multiple_scs", "max_sc_count="])
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
  outputfile = "paramsearch.out"
  multiple_scs = False
  max_sc_count = 2
  for opt, arg in opts:
    if opt == '-h':
      print helpmsg
      sys.exit()
    elif opt == '-o':
      outputfile = arg
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
    elif opt == "--multiple_scs":
      multiple_scs = True
    elif opt == "--max_sc_count":
      max_sc_count = int(arg)
  params, args = zip(*opts)
  if "--bw_factor" not in params or "--res_factor" not in params or \
     "--lat_factor" not in params:
    print helpmsg
    raise Exception("Not all algorithm params are given!")
  
  network, topoparams = CarrierTopoBuilder.getSmallTopo()
  max_test_lvl = 50000
  ever_successful = False
  global test_lvl
  global all_saps_ending
  global all_saps_beginning
  all_saps_ending = [s.id for s in network.saps]
  all_saps_beginning = [s.id for s in network.saps]
  random.seed(seed)
  random.shuffle(all_saps_beginning)
  random.shuffle(all_saps_ending)
  try:
    while test_lvl < max_test_lvl:
      try:
        log.debug("Trying mapping with test level %s..."%test_lvl)
        shortest_paths = None
        request = generateRequestForCarrierTopo(seed, 
                  loops=loops, vnf_sharing_probabilty=vnf_sharing,
                  multiSC=multiple_scs, max_sc_count=max_sc_count)
        while request is not None:
          if test_lvl > max_test_lvl:
            break
          running_nfs[test_lvl] = [nf for nf in request.nfs 
                                   if nf.id.split("-")[1] == str(test_lvl)]
          network, shortest_paths = MappingAlgorithms.MAP(request, network, 
                    full_remap=fullremap, enable_shortest_path_cache=True,
                    bw_factor=bw_factor, res_factor=res_factor,
                    lat_factor=lat_factor, shortest_paths=shortest_paths, 
                    return_dist=True)
          ever_successful = True
          log.debug("Mapping successful on test level %s!"%test_lvl)
          test_lvl += 1
          # needed to change from generator style due to some bug 
          # with all_saps_ lists. Parameters needs to be modified two places!!
          request = generateRequestForCarrierTopo(seed, 
                  loops=loops, vnf_sharing_probabilty=vnf_sharing,
                  multiSC=multiple_scs, max_sc_count=max_sc_count)
      except uet.MappingException as me:
        log.info("Mapping failed: %s"%me.msg)
        break
      if request is None:
        log.info("Request generation reached its end!")
        break
  except uet.UnifyException as ue:
    log.error(ue.msg)
    log.error(traceback.format_exc())
    with open(outputfile, "a") as f:
      f.write("\n".join(("UnifyException cought during StressTest: ",
                         ue.msg,traceback.format_exc())))
  except Exception as e:
    log.error(traceback.format_exc())
    with open(outputfile, "a") as f:
      f.write("\n".join(("Exception cought during StressTest: ",
                         traceback.format_exc())))
  log.info("First unsuccessful mapping was at %s test level."%test_lvl)
  if ever_successful:
    # print "\nLast successful mapping was at %s test level.\n"%(test_lvl - 1)
    with open(outputfile, "a") as f:
      f.write("\nLast successful mapping was at %s test level.\n"%(test_lvl - 1))
  else:
    with open(outputfile, "a") as f:
      f.write("\nMapping failed at starting test level (%s)\n"%test_lvl)

if __name__ == '__main__':
  main(sys.argv[1:])
