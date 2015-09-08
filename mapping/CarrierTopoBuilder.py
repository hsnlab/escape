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
Provides functions to build a large network modeling a carrier topology.
This is the target parameter optimization topology for the mapping algorithm.
The topology is based on WP3 - Service Provider Scenario for Optimization.ppt 
by Telecom Italia (UNIFY SVN repo)
Parameter names are also based on the .ppt file.

"""

import logging
import math
import random

try:
  from escape.util.nffg import NFFG
except ImportError:
  import sys, os, inspect

  sys.path.insert(0, os.path.join(os.path.abspath(os.path.realpath(
    os.path.abspath(
      os.path.split(inspect.getfile(inspect.currentframe()))[0])) + "/.."),
                                  "pox/ext/escape/util/"))
  from nffg import NFFG

# Aggregation links (100Gbps) Connecting Distribution nodes to Aggregation Nodes
aggr_link = {'bandwidth': 100000, 'delay': 0.2}
popcnt = 0

log = logging.getLogger("TopoConstruct")
logging.basicConfig(level=logging.DEBUG,
                      format='%(levelname)s:%(name)s:%(message)s')

def addRedundantPairedConnection(nffg, an0, an1, bn0, bn1, linkres):
  """
  Connects A-s to B-s and B-s to A-s with undirected links with linkres.
  """
  nffg.add_undirected_link(an0.add_port(), bn0.add_port(), **linkres)
  nffg.add_undirected_link(an0.add_port(), bn1.add_port(), **linkres)
  nffg.add_undirected_link(an1.add_port(), bn0.add_port(), **linkres)
  nffg.add_undirected_link(an1.add_port(), bn1.add_port(), **linkres)


def index_gen():
  while True:
    yield int(math.floor(random.random() * 100000))

def gen_params(l):
  while True:
    yield l[next(index_gen()) % len(l)]

def addRetailOrBusinessPart(nffg, an0, an1, popn, BNAS_PE, 
                            Cpb, access_bw, part="Retail"):
  """
  Retail and Business part inside one PoP is structurally the same.
  """
  log.debug("Adding %s part for %s..."%(part, popn))
  # add Distribution Nodes (100Gbps switching capacity)
  dnres = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
           'bandwidth': 100000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  dn0 = None
  dn1 = None
  if BNAS_PE > 0:
    dn0 = nffg.add_infra(id="DistributionNode"+popn+part+"-0", 
                                **dnres)
    dn1 = nffg.add_infra(id="DistributionNode"+popn+part+"-1",
                                **dnres)
    addRedundantPairedConnection(nffg, an0, an1, dn0, dn1, aggr_link)

  # add BNAS or PE (10Gbps switching capacity) 
  # and connecting SAPs towards Retail Clients (links with BCT bandwidth)
  for i in range(0, BNAS_PE):
    log.debug("Adding switch %s for %s part..."%(i, part))
    bnas_pe_res = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
               'bandwidth': 10000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
    bnas_pe = nffg.add_infra(id=part+"-switch-"+str(i)+popn, 
                             **bnas_pe_res)
    distr_link = {'bandwidth': 10000, 'delay': 0.2}
    
    #add Distribution Links towards Distribution Nodes
    nffg.add_undirected_link(dn0.add_port(), bnas_pe.add_port(), 
                             **distr_link)
    nffg.add_undirected_link(dn0.add_port(), bnas_pe.add_port(), 
                             **distr_link)
    
    # add clients to current BNAS or PE
    log.debug("Connecting %s SAPs to switch %s of %s part."%(Cpb, i, part))
    for j in range(0, Cpb):
      nameid = part+"-SAP-"+str(j)+"-switch-"+str(i)+popn
      sap = nffg.add_sap(id=nameid, name=nameid)
      access_link = {'bandwidth': access_bw, 'delay': 0.5}
      nffg.add_undirected_link(bnas_pe.add_port(), sap.add_port(), **access_link)


def addCassis(nffg, fi0, fi1, cluster_id, chassis_id, popn, 
              SE, NF_types, SE_cores, SE_mem, SE_storage, CL_bw, CH_links):
  log.debug("Adding Chassis no.%s with %s Servers for Cluster no.%s of %s."%
            (chassis_id,SE,cluster_id,popn))
  fabricext_res = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
                   'bandwidth': 100000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  fe0 = nffg.add_infra(id="FabricExt-0-Chassis-"+str(chassis_id)+"-Cluster-"\
                       +str(cluster_id)+popn)
  fe1 = nffg.add_infra(id="FabricExt-1-Chassis-"+str(chassis_id)+"-Cluster-"\
                       +str(cluster_id)+popn)
  # add links connecting the Fabric Interconnects and Fabric Extenders
  for i in range(0, CH_links/2):
      nffg.add_undirected_link(fi0.add_port(), fe0.add_port(), 
                               bandwidth=float(CL_bw)/CH_links, delay=0.2)
      nffg.add_undirected_link(fi1.add_port(), fe1.add_port(), 
                               bandwidth=float(CL_bw)/CH_links, delay=0.2)

  # add servers and connect them to Fabric Extenders
  for s in range(0, SE):
    server_res = {'cpu': next(gen_params(SE_cores)), 
                  'mem': next(gen_params(SE_mem)), 
                  'storage': next(gen_params(SE_storage)), 
                  'delay': 0.5, 'bandwidth': 100000, 
                  'infra_type': NFFG.TYPE_INFRA_EE}
    server = nffg.add_infra(id="Server-"+str(s)+"-Chassis-"+str(chassis_id)+\
                            "-Cluster-"+str(cluster_id)+popn,
                            **server_res)
    # add supported types
    server.add_supported_type(random.sample(NF_types, 
                                     (next(index_gen()) % len(NF_types)) + 1))
    # connect servers to Fabric Extenders with 10Gbps links
    server_link = {'bandwidth': 10000, 'delay': 0.2}
    nffg.add_undirected_link(server.add_port(), fe0.add_port(), **server_link)
    nffg.add_undirected_link(server.add_port(), fe1.add_port(), **server_link)


def addCloudNFVPart(nffg, an0, an1, popn, CL, CH, SE, SAN_bw, SAN_storage,
                    NF_types, SE_cores, SE_mem, SE_storage, CL_bw, CH_links):
  log.debug("Adding Cloud/NFV part for %s."%popn)
  dnres = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
           'bandwidth': 100000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  dn0 = nffg.add_infra(id="DistributionNode"+popn+"CloudNFV-0", 
                       **dnres)
  dn1 = nffg.add_infra(id="DistributionNode"+popn+"CloudNFV-1",
                       **dnres)
  addRedundantPairedConnection(nffg, an0, an1, dn0, dn1, aggr_link)
  
  # add Server Clusters
  for i in range(0, CL):
    log.debug("Adding Cluster no.%s to Could/NFV part of %s"%(i, popn))
    fi_res = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
              'bandwidth': 100000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
    fabric_interconnect0 = nffg.add_infra(id="FabricInterconnect-0-Cluster-"+\
                                          str(i)+popn, **fi_res)
    fabric_interconnect1 = nffg.add_infra(id="FabricInterconnect-1-Cluster-"+\
                                          str(i)+popn, **fi_res)
    addRedundantPairedConnection(nffg, an0, an1, fabric_interconnect0, 
                                 fabric_interconnect1, aggr_link)

    # NOTE: SAN can't host any VNFs now!!
    # SAN is an Infra with big storage (internal bw should be big: e.g. 1Tbps)
    san_res = {'cpu': 0, 'mem': 0, 'storage': SAN_storage, 'delay': 0.1,
              'bandwidth': 1000000, 'infra_type': NFFG.TYPE_INFRA_EE}
    san = nffg.add_infra(id="SAN-Cluster-"+str(i)+popn, **san_res)
    # connect SAN to Fabric Interconnects
    nffg.add_undirected_link(san.add_port(), fabric_interconnect0.add_port(), 
                             bandwidth=SAN_bw, delay=0.1)
    nffg.add_undirected_link(san.add_port(), fabric_interconnect1.add_port(), 
                             bandwidth=SAN_bw, delay=0.1)
    # add Chassis
    for j in range(0, CH):
      addCassis(nffg, fabric_interconnect0, fabric_interconnect1, i, j, popn, 
                SE, NF_types, SE_cores, SE_mem, SE_storage, CL_bw, CH_links)


def addPoP(nffg, backbonenode0, backbonenode1, 
           BNAS, RCpb, RCT, 
           PE, BCpb, BCT,
           CL, CH, SE, SAN_bw, SAN_storage, NF_types,
           SE_cores, SE_mem, SE_storage, CL_bw, CH_links):
  """
  Create one PoP which consists of three domains:
    - Cloud/NFV services
    - Retail Edge
    - Business Edge
  Backbone nodes where the Aggregation Nodes should be connected.
  BNAS: number of BNAS nodes (~2-10)
  RCpb: number of Retail Clients per BNAS box (~40k)
  RCT: traffic per Retail Clients (0.1-0.2 Mbps)
  PE: number of PE nodes per PoP (~2-8)
  BCpb: number of business clients oer PE box (~4k)
  BCT: traffic per Business Clients (0.1-0.2 Mbps)
  CL: number of clusters in Cloud/NFV part (?)
  CH: number of Chassis per cluster (~8-40)
  SE: number of Servers per chassis (~8)
  SAN_bw: Cluster bandwith to SAN (160Gbps - 1.6Tbps)
  SAN_storage: storage of one SAN (?)
  NF_types: list of supported NF types on the servers
  SE_cores: list of numbers of cores per server (~8-16)
  SE_mem: list of memory capacities per server (~32000MB - 64000MB)
  SE_storage: list of storage capacities per server (~300GB - 1500GB)
  CL_bw: cluster bandwidth to servers per Chassis (~40Gbps - 160Gbps)
  CH_links: number of uplinks per Chassis (~4-16)
    NOTE: Link bw from Fabric Extender to Fabric Interc. equals 
    CL_bw/CH_links (~10Gbps).
  """
  global popcnt
  popn = "-PoP-"+str(popcnt)

  log.debug("Adding PoP %s..."%popcnt)
  # add Aggregation Nodes (1Tbps switching capacity)
  anres = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
           'bandwidth': 1000000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  an0 = nffg.add_infra(id="AggregationNode-0"+popn, **anres)
  an1 = nffg.add_infra(id="AggregationNode-1"+popn, **anres)
  
  # add uplinks to the Backbone
  nffg.add_undirected_link(an0.add_port(), backbonenode0.add_port(), 
                           bandwidth=1000000, delay=0.1)
  nffg.add_undirected_link(an1.add_port(), backbonenode1.add_port(), 
                           bandwidth=1000000, delay=0.1)

  addRetailOrBusinessPart(nffg, an0, an1, popn, BNAS, RCpb, RCT)
  addRetailOrBusinessPart(nffg, an0, an1, popn, PE, BCpb, BCT, part="Business")

  if CL > 0:
      addCloudNFVPart(nffg, an0, an1, popn, CL, CH, SE, SAN_bw, SAN_storage,
                      NF_types, SE_cores, SE_mem, SE_storage, CL_bw, CH_links)

  popcnt += 1
  return
    
def getCarrierTopo(params):
  """
  Construct the core network and add PoPs with their parameters.
  params is a list of dictionaries with PoP data:
    'Retail': (BNAS, RCpb, RCT)
    'Business': (PE, BCpb, BCT)
    'CloudNFV': (CL,CH,SE,SAN_bw,SAN_sto,NF_types,SE_cores,SE_mem,SE_sto,
                 CL_bw, CH_links)
  """
  # This initializes the random generator always to the same value, so the
  # returned index sequence, and thus the network parameters will be generated 
  # always the same (we want a fixed network environment)
  # The generated identifiers are still different between genereations, but 
  # those does not influence the mapping process
  random.seed(0)
  
  nffg = NFFG(id="CarrierTopo")
  backbone_res =  {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
                   'bandwidth': 10000000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  bn0 = nffg.add_infra(id="BackboneNode0", **backbone_res)
  bn1 = nffg.add_infra(id="BackboneNode1", **backbone_res)
  bn2 = nffg.add_infra(id="BackboneNode2", **backbone_res)
  bn3 = nffg.add_infra(id="BackboneNode3", **backbone_res)

  nffg.add_undirected_link(bn0.add_port(), bn1.add_port(), bandwidth=1000000, 
                           delay=10)
  nffg.add_undirected_link(bn1.add_port(), bn2.add_port(), bandwidth=1000000, 
                           delay=10)
  nffg.add_undirected_link(bn2.add_port(), bn3.add_port(), bandwidth=1000000, 
                           delay=10)
  nffg.add_undirected_link(bn3.add_port(), bn0.add_port(), bandwidth=1000000, 
                           delay=10)
  i = 0
  backbones = (bn0, bn1, bn2, bn3)
  bnlen = len(backbones)
  for popdata in params:
    tmp = []
    tmp.extend(popdata['Retail'])
    tmp.extend(popdata['Business'])
    tmp.extend(popdata['CloudNFV'])
    addPoP(nffg, backbones[i%bnlen], backbones[(i+1)%bnlen], *tmp)
    i += 1
  """
  #                      BNAS,RCpb,  RCT, PE,BCpb, BCT, CL,CH,SE, SAN_bw, 
  addPoP(nffg, bn2, bn3, 2,   10000, 0.2, 2, 4000, 0.2, 2, 8, 8,  160000,  
       # SAN_sto,NF_types,  SE_cores,  SE_mem,        SE_sto,  CL_bw, CH_links
         100000, ['A','B'], [8,12,16], [32000,64000], [150],   40000, 4)  
  #                      BNAS, RCpb,  RCT, PE,BCpb, BCT, CL,CH, SE, SAN_bw, 
  addPoP(nffg, bn1, bn2, 10,   40000, 0.2, 8, 4000, 0.2, 4, 40, 8,  160000,  
       # SAN_sto,NF_types,             SE_cores,  SE_mem,        SE_sto,    
         100000, ['A','B','C','D','E'],[8,12,16], [32000,64000], [150,200],  
       # CL_bw, CH_links
         80000, 8)
  """
  log.debug("Carrier topology construction finished!")
  return nffg

if __name__ == '__main__':
  topoparams = []
  # params of one PoP
  # 'Retail': (BNAS, RCpb, RCT)
  # 'Business': (PE, BCpb, BCT)
  # 'CloudNFV': (CL,CH,SE,SAN_bw,SAN_sto,NF_types,SE_cores,SE_mem,SE_sto,
  #              CL_bw, CH_links)
  topoparams.append({'Retail': (2, 10000, 0.2), 'Business': (2, 8000, 0.2), 
                     'CloudNFV': (2, 8, 8,  160000, 100000, ['A','B','C'], 
                                  [4,8,16],  [32000], [100,150],   40000, 4)})
  topoparams.append({'Retail': (2, 10000, 0.2), 'Business': (4, 4000, 0.2),
                     'CloudNFV': (2, 8, 8,  160000, 100000, ['A','B'], 
                                  [8,12,16], [32000,64000], [150], 40000, 4)})
  # topoparams.append({'Retail': (2, 20000, 0.2), 'Business': (8, 4000, 0.2),
  #                    'CloudNFV': (2, 40, 8,  160000, 100000, ['B', 'C'], 
  #                                 [4,8,12,16], [32000,64000], [200], 40000, 4)})
  topo = getCarrierTopo(topoparams)
  print topo.dump()
