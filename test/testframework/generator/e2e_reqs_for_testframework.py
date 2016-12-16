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
Generates request graphs for ESCAPE Test Framework's mapping focused tests.
"""

import os
import sys
# Needed to run the Algorithm scripts in the parent folder.
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import getopt
import logging
import math
import random
import traceback
import string

import CarrierTopoBuilder
import MappingAlgorithms
import UnifyExceptionTypes as uet

from collections import OrderedDict

try:
  from escape.nffg_lib.nffg import NFFG, NFFGToolBox
except ImportError:
  import sys, os
  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                  "../escape/escape/nffg_lib/")))
  from nffg import NFFG, NFFGToolBox

log = logging.getLogger("StressTest")
log.setLevel(logging.DEBUG)
logging.basicConfig(format='%(levelname)s:%(name)s:%(message)s')
rnd = random.Random()

def gen_seq():
  while True:
    yield int(math.floor(rnd.random() * 999999999))


helpmsg = """StressTest.py options are:
   -h                Print this message help message.
   --loops           All Service Chains will be loops.
   --vnf_sharing=p   Sets the ratio of shared and not shared VNF-s.
   --request_seed=i  Provides seed for the random generator.
   --multiple_scs           One request will contain at least 2 chains with vnf sharing
                            probability defined by "--vnf_sharing_same_sg" option.
   --vnf_sharing_same_sg=p  The conditional probablilty of sharing a VNF with the
                            current Service Graph, if we need to share a VNF 
                            determined by "--vnf_sharing"
   --max_sc_count=i         Determines how many chains should one request contain
                            at most.

   --batch_length=f  The number of time units to wait for Service Graphs, that 
                     should be batched and mapped together by the algorithm. The
                     expected arrival time difference is 1.0 between SG-s.
   --shareable_sg_count=i   The number of last 'i' Service Graphs which could
                            be used for sharing VNFs. Default value is unlimited.
   --sliding_share   If not set, the set of shareable SG-s is emptied after 
                     successfull batched mapping.
   --use_saps_once   If set, all SAPs can only be used once as SC origin and 
                     once as SC destination.
 
   --substrate=<<path>>    Substrate Network NFFG to be used for mapping the 
                           requests.
"""

def _shareVNFFromEarlierSG(nffg, running_nfs, nfs_this_sc, p):
  sumlen = sum([l*i for l,i in zip([len(running_nfs[n]) for n in running_nfs], 
                                   xrange(1,len(running_nfs)+1))])
  i = 0
  ratio = float(len(running_nfs.values()[i])) / sumlen
  while ratio < p:
    i += 1
    ratio += float((i+1)*len(running_nfs.values()[i])) / sumlen
  nf = rnd.choice(running_nfs.values()[i])
  if reduce(lambda a,b: a and b, [v in nfs_this_sc for v 
                                  in running_nfs.values()[i]]):
    # failing to add a VNF due to this criteria infuences the provided 
    # vnf_sharing_probabilty, but it is estimated to be insignificant, 
    # otherwise the generation can run into infinite loop!
    log.warn("All the VNF-s of the subchain selected for VNF sharing are"
             " already in the current chain under construction! Skipping"
             " VNF sharing...")
    return False, None
  else:
    while nf in nfs_this_sc:
      nf = rnd.choice(running_nfs.values()[i])
  if nf in nffg.nfs:
    return False, nf
  else:
    nffg.add_node(nf)
    return True, nf


def generateRequestForCarrierTopo(test_lvl, all_saps_beginning, 
                                  all_saps_ending,
                                  running_nfs, loops=False, 
                                  use_saps_once=True,
                                  vnf_sharing_probabilty=0.0,
                                  vnf_sharing_same_sg=0.0,
                                  shareable_sg_count=9999999999999999,
                                  multiSC=False, max_sc_count=2):
  """
  By default generates VNF-disjoint SC-s starting/ending only once in each SAP.
  With the 'loops' option, only loop SC-s are generated.
  'vnf_sharing_probabilty' determines the ratio of 
     #(VNF-s used by at least two SC-s)/#(not shared VNF-s).
  NOTE: some kind of periodicity is included to make the effect of batching 
  visible. But it is (and must be) independent of the batch_length.

  WARNING!! batch_length meaining is changed if --poisson is set!

  Generate exponential arrival time for VNF-s to make Batching more reasonable.
  inter arrival time is Exp(1) so if we are batching for 4 time units, the 
  expected SG count is 4, because the sum of 4 Exp(1) is Exp(4).
  BUT we wait for 1 SG at least, but if by that time 4 units has already passed,
  map the SG alone (unbatched).
  """
  chain_maxlen = 8
  sc_count=1
  # maximal possible bandwidth for chains
  max_bw = 7.0
  if multiSC:
    sc_count = rnd.randint(2,max_sc_count)
  while len(all_saps_ending) > sc_count and len(all_saps_beginning) > sc_count:
    nffg = NFFG(id="Benchmark-Req-"+str(test_lvl)+"-Piece")
    # newly added NF-s of one request
    current_nfs = []
    for scid in xrange(0,sc_count):
      # find two SAP-s for chain ends.
      nfs_this_sc = []
      sap1 = nffg.add_sap(id = all_saps_beginning.pop() if use_saps_once else \
                          rnd.choice(all_saps_beginning))
      sap2 = None
      if loops:
        sap2 = sap1
      else:
        tmpid = all_saps_ending.pop() if use_saps_once else \
                rnd.choice(all_saps_ending)
        while True:
          if tmpid != sap1.id:
            sap2 = nffg.add_sap(id = tmpid)
            break
          else:
            tmpid = all_saps_ending.pop() if use_saps_once else \
                    rnd.choice(all_saps_ending)
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
        p = rnd.random()
        if rnd.random() < vnf_sharing_probabilty and len(running_nfs) > 0 \
           and not multiSC:
          vnf_added, nf = _shareVNFFromEarlierSG(nffg, running_nfs, nfs_this_sc,
                                                 p)
        elif multiSC and \
             p < vnf_sharing_probabilty and len(current_nfs) > 0 \
             and len(running_nfs) > 0:
          # this influences the the given VNF sharing probability...
          if reduce(lambda a,b: a and b, [v in nfs_this_sc for 
                                          v in current_nfs]):
            log.warn("All shareable VNF-s are already added to this chain! "
                     "Skipping VNF sharing...")
          elif rnd.random() < vnf_sharing_same_sg:
            nf = rnd.choice(current_nfs)
            while nf in nfs_this_sc:
              nf = rnd.choice(current_nfs)
            # the VNF is already in the subchain, we just need to add the links
            # vnf_added = True
          else:
            # this happens when VNF sharing is needed but not with the actual SG
            vnf_added, nf = _shareVNFFromEarlierSG(nffg, running_nfs, 
                                                   nfs_this_sc, p)
        else:
          nf = nffg.add_nf(id="-".join(("Test",str(test_lvl),"SC",str(scid),
                                        "VNF",str(vnf))),
                           func_type=rnd.choice(nf_types), 
                           cpu=rnd.randint(1, 4),
                           mem=rnd.random()*1600,
                           storage=rnd.random()*3)
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
        # nfcnt = len([i for i in nffg.nfs])
        minlat = 60.0
        maxlat = 220.0
      nffg.add_req(sap1port, sap2port, delay=rnd.uniform(minlat,maxlat), 
                   bandwidth=rnd.random()*max_bw, 
                   sg_path = sg_path)
      log.info("Service Chain on NF-s added: %s"%[nf.id for nf in nfs_this_sc])
      # this prevents loops in the chains and makes new and old NF-s equally 
      # preferable in total for NF sharing
      new_nfs = [vnf for vnf in nfs_this_sc if vnf not in current_nfs]
      for tmp in xrange(0, scid+1):
        current_nfs.extend(new_nfs)
      if not multiSC:
        return nffg, all_saps_beginning, all_saps_ending
    if multiSC:
      return nffg, all_saps_beginning, all_saps_ending
  return None, all_saps_beginning, all_saps_ending

def main(argv):
  try:
    opts, args = getopt.getopt(argv,"h",["loops", "request_seed=",
                               "vnf_sharing=", "multiple_scs",
                               "vnf_sharing_same_sg=", "max_sc_count=",
                               "shareable_sg_count=", "batch_length=",
                               "sliding_share", "use_saps_once",
                               "substrate="])
  except getopt.GetoptError:
    print helpmsg
    sys.exit()
  loops = False
  vnf_sharing = 0.0
  vnf_sharing_same_sg = 0.0
  seed = 3
  multiple_scs = False
  sliding_share = False
  use_saps_once = False
  max_sc_count = 2
  shareable_sg_count = 99999999999999
  batch_length = 1
  substrate = "dfn-gwin.gml"
  for opt, arg in opts:
    if opt == '-h':
      print helpmsg
      sys.exit()
    elif opt == "--loops":
      loops = True
    elif opt == "--request_seed":
      seed = int(arg)
    elif opt == "--vnf_sharing":
      vnf_sharing = float(arg)
    elif opt == "--multiple_scs":
      multiple_scs = True
    elif opt == "--max_sc_count":
      max_sc_count = int(arg)
    elif opt == "--vnf_sharing_same_sg":
      vnf_sharing_same_sg = float(arg)
    elif opt == "--shareable_sg_count":
      shareable_sg_count = int(arg)
    elif opt == "--batch_length":
      batch_length = float(arg)
    elif opt == "--sliding_share":
      sliding_share = True
    elif opt == "--use_saps_once":
      use_saps_once = True
    elif opt == "--substrate":
      topo_name = arg
    
  nf_types = []
  # TODO: this is NOT an NFFG
  with open(substrate, "r") as f:
    substrate_nffg = NFFG.parse(f.read())
    

if __name__ == '__main__':
  main(sys.argv[1:])
