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
import random, math, traceback, sys, logging

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

def genAndAddSAP(nffg, networkparams):
  popn = next(gen_seq()) % len(networkparams)
  popdata = networkparams[popn]
  part = random.choice(['Retail','Business'])
  sapid = "-".join((part,"SAP",
                    str(next(gen_seq()) % popdata[part][1]), 
                    "switch", str(next(gen_seq()) % popdata[part][0]),
                    "PoP", str(popn)))
  if not sapid in nffg.network:
    return nffg.add_sap(id=sapid)
  else:
    return nffg.network.node[sapid]


def generateRequestForCarrierTopo(networkparams, test_lvl, seed):
  nffg = NFFG(id="Benchmark-Req-"+str(test_lvl))
  chain_maxlen = 10
  random.seed(seed)
  
  # generate some VNF-s connecting the two SAP-s
  for i in xrange(0, test_lvl):
    # find two SAP-s for chain ends.
    sap1 = genAndAddSAP(nffg, networkparams)
    sap2 = genAndAddSAP(nffg, networkparams)
    sg_path = []
    sap1port = sap1.add_port()
    last_req_port = sap1port
    for vnf in xrange(0, next(gen_seq()) % chain_maxlen + 1):
      nf = nffg.add_nf(id="-".join(("Test",str(test_lvl),"SC",str(i),"VNF",
                                    str(vnf))),
                       func_type=random.choice(['A','B','C']), 
                       cpu=random.choice([1,2,3]),
                       mem=random.random()*500,
                       storage=random.random(),
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
    nffg.add_req(sap1port, sap2port, delay=random.uniform(20,100), 
                 bandwidth=random.random()*0.2, sg_path = sg_path)
  return nffg

if __name__ == '__main__':
  topoparams = []
  # params of one PoP
  # 'Retail': (BNAS, RCpb, RCT)
  # 'Business': (PE, BCpb, BCT)
  # 'CloudNFV': (CL,CH,SE,SAN_bw,SAN_sto,NF_types,SE_cores,SE_mem,SE_sto,
  #              CL_bw, CH_links)
  topoparams.append({'Retail': (2, 250, 0.2), 'Business': (2, 100, 0.2), 
                     'CloudNFV': (2, 4, 8,  160000, 100000, ['A','B','C'], 
                                  [4,8,16],  [32000], [100,150],   40000, 4)})
  topoparams.append({'Retail': (2, 250, 0.2), 'Business': (2, 150, 0.2),
                     'CloudNFV': (2, 2, 8,  160000, 100000, ['A','B'], 
                                  [8,12,16], [32000,64000], [150], 40000, 4)})
  # topoparams.append({'Retail': (2, 20000, 0.2), 'Business': (8, 4000, 0.2),
  #                    'CloudNFV': (2, 40, 8,  160000, 100000, ['B', 'C'], 
  #                                 [4,8,12,16], [32000,64000], [200], 40000, 4)})
  network = CarrierTopoBuilder.getCarrierTopo( topoparams )
  test_lvl = 10
  max_test_lvl = sys.maxint
  ever_successful = False
  try:
    while test_lvl < max_test_lvl:
      try:
        log.debug("Trying mapping with test level %s..."%test_lvl)
        request = generateRequestForCarrierTopo(topoparams, test_lvl, 1)
        # print request.dump()
        MappingAlgorithms.MAP(request, network, enable_shortest_path_cache=True)
        ever_successful = True
        test_lvl = int(2 * test_lvl)
        log.debug("Mapping successful!")
      except uet.MappingException as me:
        log.debug("Mapping failed: %s"%me.msg)
        break
  except uet.UnifyException as ue:
    print ue.msg 
    print traceback.format_exc()
  except Exception as e:
    print traceback.format_exc()
  print "First unsuccessful mapping was at %s test level."%test_lvl
  if ever_successful:
    print "Last successful was at %s test level."%int(test_lvl/2.0)
  else:
    print "Mapping failed at starting test level (%s)"%test_lvl

