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
import logging
import math
import random
import networkx as nx
import copy

from sg_generator import getName

try:
  from escape.nffg_lib.nffg import NFFG, NFFGToolBox
except ImportError:
  import sys, os

  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                               "../../../escape/escape/nffg_lib/")))
  from nffg import NFFG, NFFGToolBox

log = logging.getLogger("StressTest")
# log.setLevel(logging.DEBUG)
# logging.basicConfig(format='%(levelname)s:%(name)s:%(message)s')
rnd = random.Random()


def gen_seq ():
  while True:
    yield int(math.floor(rnd.random() * 999999999))


helpmsg = """StressTest.py options are:
   -h                Print this message help message.
   --loops           All Service Chains will be loops.
   --vnf_sharing=p   Sets the ratio of shared and not shared VNF-s.
   --seed=i  Provides seed for the random generator.
   --multiple_scs           One request will contain at least 2 chains.
   --max_sc_count=i         Determines how many chains should one request
   contain
                            at most.

   --use_saps_once   If set, all SAPs can only be used once as SC origin and 
                     once as SC destination.
 
   --substrate=<<path>>    Substrate Network NFFG to be used for mapping the 
                           requests. Compulsory to give!
"""


def generateRequestForCarrierTopo (all_saps_ending, all_saps_beginning,
                                   avg_shp_len, nf_types,
                                   max_e2e_lat_multiplier=20,
                                   loops=False, use_saps_once=True,
                                   vnf_sharing_probabilty=0.0,
                                   multiSC=False, max_sc_count=2,
                                   chain_maxlen=8, max_cpu=4, max_mem=1600,
                                   max_storage=3, max_bw=7):
  """
  By default generates VNF-disjoint SC-s starting/ending only once in each SAP.
  With the 'loops' option, only loop SC-s are generated.
  'vnf_sharing_probabilty' determines the ratio of 
     #(VNF-s used by at least two SC-s)/#(not shared VNF-s).
  """
  sc_count = 1
  # maximal possible bandwidth for chains
  if multiSC:
    sc_count = rnd.randint(2, max_sc_count)
  while len(all_saps_ending) > sc_count and len(all_saps_beginning) > sc_count:
    nffg = NFFG(id="E2e_req_test_nffg")
    nffg.mode = NFFG.MODE_ADD
    # newly added NF-s of one request
    current_nfs = []
    for scid in xrange(0, sc_count):
      # find two SAP-s for chain ends.
      nfs_this_sc = []
      sapid = all_saps_beginning.pop() if use_saps_once else \
        rnd.choice(all_saps_beginning)
      if sapid not in nffg:
        sap1 = nffg.add_sap(id=sapid)
      else:
        sap1 = nffg.network.node[sapid]
      sap2 = None
      if loops:
        sap2 = sap1
      else:
        tmpid = all_saps_ending.pop() if use_saps_once else \
          rnd.choice(all_saps_ending)
        while True:
          if tmpid != sap1.id:
            if tmpid not in nffg:
              sap2 = nffg.add_sap(id=tmpid)
            else:
              sap2 = nffg.network.node[tmpid]
            break
          else:
            tmpid = all_saps_ending.pop() if use_saps_once else \
              rnd.choice(all_saps_ending)
      sg_path = []
      if len(sap1.ports) > 0:
        for sap1port in sap1.ports:
          break
      else:
        sap1port = sap1.add_port(id=getName("port"))
      last_req_port = sap1port
      # generate some VNF-s connecting the two SAP-s
      vnf_cnt = next(gen_seq()) % chain_maxlen + 1
      for vnf in xrange(0, vnf_cnt):
        # in the first case p is used to determine which previous chain should 
        # be used to share the VNF, in the latter case it is used to determine
        # whether we should share now.
        p = rnd.random()
        if multiSC and \
              p < vnf_sharing_probabilty and len(current_nfs) > 0:
          # this influences the the given VNF sharing probability...
          if reduce(lambda a, b: a and b, [v in nfs_this_sc for
                                           v in current_nfs]):
            log.warn("All shareable VNF-s are already added to this chain! "
                     "Skipping VNF sharing...")
            continue
          else:
            nf = rnd.choice(current_nfs)
            while nf in nfs_this_sc:
              nf = rnd.choice(current_nfs)
              # the VNF is already in the subchain, we just need to add the
              # links
              # vnf_added = True
        else:
          nf = nffg.add_nf(id="-".join(("SC", str(scid), "VNF", str(vnf))),
                           func_type=rnd.choice(nf_types),
                           cpu=rnd.random() * max_cpu,
                           mem=rnd.random() * max_mem,
                           storage=rnd.random() * max_storage)

        nfs_this_sc.append(nf)
        newport = nf.add_port(id=getName("port"))
        sglink = nffg.add_sglink(last_req_port, newport, id=getName("link"))
        sg_path.append(sglink.id)
        last_req_port = nf.add_port(id=getName("port"))

      if len(sap2.ports) > 0:
        for sap2port in sap2.ports:
          break
      else:
        sap2port = sap2.add_port(id=getName("port"))
      sglink = nffg.add_sglink(last_req_port, sap2port, id=getName("link"))
      sg_path.append(sglink.id)

      # WARNING: this is completly a wild guess! Failing due to this doesn't 
      # necessarily mean algorithm failure
      # Bandwidth maximal random value should be min(SAP1acces_bw,
      # SAP2access_bw)
      # MAYBE: each SAP can only be once in the reqgraph? - this is the case
      # now.
      minlat = avg_shp_len * 1.1
      maxlat = avg_shp_len * 20.0
      nffg.add_req(sap1port, sap2port, delay=rnd.uniform(minlat, maxlat),
                   bandwidth=rnd.random() * max_bw,
                   sg_path=sg_path, id=getName("req"))
      log.info(
        "Service Chain on NF-s added: %s" % [nf.id for nf in nfs_this_sc])
      # this prevents loops in the chains and makes new and old NF-s equally 
      # preferable in total for NF sharing
      new_nfs = [vnf for vnf in nfs_this_sc if vnf not in current_nfs]
      for tmp in xrange(0, scid + 1):
        current_nfs.extend(new_nfs)
      if not multiSC:
        return nffg
    if multiSC:
      return nffg
  return None


def main (substrate, loops=False, vnf_sharing=0.0,
          seed=0, multiple_scs=False,
          use_saps_once=False, max_sc_count=2,
          chain_maxlen=8,
          max_cpu=4, max_mem=1600, max_storage=3, max_bw=7,
          max_e2e_lat_multiplier=20):
  nf_types = []
  request = None
  rnd.seed(seed)
  with open(substrate, "r") as f:
    substrate_nffg = NFFG.parse(f.read())
    for infra in substrate_nffg.infras:
      nf_types.extend(infra.supported)

    nf_types = list(set(nf_types))

    all_saps_ending = [s.id for s in substrate_nffg.saps]
    all_saps_beginning = [s.id for s in substrate_nffg.saps]

    bare_substrate_nffg = copy.deepcopy(substrate_nffg)
    for n in substrate_nffg.nfs:
      bare_substrate_nffg.del_node(n)
    path_calc_graph = nx.MultiDiGraph()
    for l in bare_substrate_nffg.links:
      path_calc_graph.add_edge(l.src.node.id, l.dst.node.id, l.id,
                               delay=l.delay)

    avg_shp_len = nx.average_shortest_path_length(path_calc_graph,
                                                  weight='delay')

    request = generateRequestForCarrierTopo(all_saps_ending, all_saps_beginning,
                                            avg_shp_len, nf_types, loops=loops,
                                            use_saps_once=use_saps_once,
                                            vnf_sharing_probabilty=vnf_sharing,
                                            multiSC=multiple_scs,
                                            max_sc_count=max_sc_count,
                                            chain_maxlen=chain_maxlen,
                                            max_cpu=max_cpu, max_mem=max_mem,
                                            max_storage=max_storage,
                                            max_bw=max_bw,
                                            max_e2e_lat_multiplier=max_e2e_lat_multiplier)

  return request


if __name__ == '__main__':
  """
  argv = sys.argv[1:]
  
  try:
    opts, args = getopt.getopt(argv,"h",["loops", "seed=",
                               "vnf_sharing=", "multiple_scs",
                               "max_sc_count=", 
                               "use_saps_once",
                               "substrate="])
  except getopt.GetoptError:
    print helpmsg
    sys.exit()
  loops = False
  vnf_sharing = 0.0
  seed = 3
  multiple_scs = False
  use_saps_once = False
  max_sc_count = 2
  substrate = ""
  for opt, arg in opts:
    if opt == '-h':
      print helpmsg
      sys.exit()
    elif opt == "--loops":
      loops = True
    elif opt == "--seed":
      seed = int(arg)
    elif opt == "--vnf_sharing":
      vnf_sharing = float(arg)
    elif opt == "--multiple_scs":
      multiple_scs = True
    elif opt == "--max_sc_count":
      max_sc_count = int(arg)
    elif opt == "--use_saps_once":
      use_saps_once = True
    elif opt == "--substrate":
      topo_name = arg
  """

  nffg = main(substrate="../../case14/topology.nffg", loops=True,
              vnf_sharing=0.5,
              seed=1, multiple_scs=True, chain_maxlen=30,
              use_saps_once=False, max_sc_count=30)

  print nffg.dump()
