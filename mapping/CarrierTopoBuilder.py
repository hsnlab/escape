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
import string

import networkx as nx

try:
  from escape.nffg_lib.nffg import NFFG
except ImportError:
  import sys, os
  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                  "../escape/escape/nffg_lib/")))
  from nffg import NFFG

# Aggregation links (100Gbps) Connecting Distribution nodes to Aggregation Nodes
aggr_link = {'bandwidth': 1000, 'delay': 0.2}

log = logging.getLogger("TopoConstruct")
logging.basicConfig(level=logging.WARN,
                      format='%(levelname)s:%(name)s:%(message)s')

max_portids = {}
def add_port(obj, increment_port_ids=False):
  # WARNING! this function is not thread safe!!
  global max_portids
  if not increment_port_ids:
    port = obj.add_port()
  else:
    if obj in max_portids:
      max_portids[obj] += 1
      port = obj.add_port(id=max_portids[obj])
    else:
      max_portids[obj] = 1
      port = obj.add_port(id=1)
  return port

def getGenForName(prefix):
   number = 0
   while True:
     yield prefix+str(number)
     number += 1
 
prefixes = {}
def getName(prefix):
  # WARNING! this function is not thread safe!!
  global prefixes
  while True:
    if prefix in prefixes:
      return prefixes[prefix].next()
    else:
      prefixes[prefix] = getGenForName(prefix)
      return prefixes[prefix].next()

def addRedundantPairedConnection(nffg, an0, an1, bn0, bn1, p, linkres):
  """
  Connects A-s to B-s and B-s to A-s with undirected links with linkres.
  """
  nffg.add_undirected_link(add_port(an0, p), add_port(bn0, p), **linkres)
  nffg.add_undirected_link(add_port(an0, p), add_port(bn1, p), **linkres)
  nffg.add_undirected_link(add_port(an1, p), add_port(bn0, p), **linkres)
  nffg.add_undirected_link(add_port(an1, p), add_port(bn1, p), **linkres)


def index_gen():
  while True:
    yield int(math.floor(random.random() * 100000))

def gen_params(l):
  while True:
    yield l[next(index_gen()) % len(l)]

def addRetailOrBusinessPart(nffg, an0, an1, p, popn, BNAS_PE, 
                            Cpb, access_bw, part="R"):
  """
  Retail and Business part inside one PoP is structurally the same.
  """
  log.debug("Adding %s part for %s..."%(part, popn))
  # add Distribution Nodes (100Gbps switching capacity)
  dnres = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
           'bandwidth': 1000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  dn0 = None
  dn1 = None
  if BNAS_PE > 0:
    dn0 = nffg.add_infra(id=getName("dn"), 
                                **dnres)
    dn1 = nffg.add_infra(id=getName("dn"),
                                **dnres)
    addRedundantPairedConnection(nffg, an0, an1, dn0, dn1, p, aggr_link)

  # add BNAS or PE (10Gbps switching capacity) 
  # and connecting SAPs towards Retail Clients (links with BCT bandwidth)
  for i in range(0, BNAS_PE):
    log.debug("Adding switch %s for %s part..."%(i, part))
    bnas_pe_res = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
               'bandwidth': 100, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
    if part == "R":
      bnas_pe = nffg.add_infra(id=getName("bnas"), 
                               **bnas_pe_res)
    elif part == "B":
      bnas_pe = nffg.add_infra(id=getName("pe"), 
                               **bnas_pe_res)
    else:
      raise Exception("Invalid part identifier given for CarrierTopoBuilder"
                      ".addRetailOrBusinessPart")
    distr_link = {'bandwidth': 100, 'delay': 0.2}
    
    #add Distribution Links towards Distribution Nodes
    nffg.add_undirected_link(add_port(dn0, p), add_port(bnas_pe, p), 
                             **distr_link)
    nffg.add_undirected_link(add_port(dn1, p), add_port(bnas_pe, p), 
                             **distr_link)
    
    # add clients to current BNAS or PE
    log.debug("Connecting %s SAPs to switch %s of %s part."%(Cpb, i, part))
    for j in range(0, Cpb):
      nameid = getName("sap")
      sap = nffg.add_sap(id=nameid, name=nameid)
      access_link = {'bandwidth': access_bw, 'delay': 0.5}
      nffg.add_undirected_link(add_port(bnas_pe, p), add_port(sap, p), 
                               **access_link)


def addCassis(nffg, fi0, fi1, p, cluster_id, chassis_id, popn, 
              SE, NF_types, SE_cores, SE_mem, SE_storage, CL_bw, CH_links):
  log.debug("Adding Chassis no.%s with %s Servers for Cluster no.%s of %s."%
            (chassis_id,SE,cluster_id,popn))
  fabricext_res = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
                   'bandwidth': 1000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  fe0 = nffg.add_infra(id=getName("fe"), **fabricext_res)
  fe1 = nffg.add_infra(id=getName("fe"), **fabricext_res)
  # add links connecting the Fabric Interconnects and Fabric Extenders
  for i in range(0, CH_links/2):
      nffg.add_undirected_link(add_port(fi0, p), add_port(fe0, p), 
                               bandwidth=float(CL_bw)/CH_links, delay=0.2)
      nffg.add_undirected_link(add_port(fi1, p), add_port(fe1, p), 
                               bandwidth=float(CL_bw)/CH_links, delay=0.2)

  # add servers and connect them to Fabric Extenders
  for s in range(0, SE):
    server_res = {'cpu': next(gen_params(SE_cores)), 
                  'mem': next(gen_params(SE_mem)), 
                  'storage': next(gen_params(SE_storage)), 
                  'delay': 0.5, 'bandwidth': 1000, 
                  'infra_type': NFFG.TYPE_INFRA_EE}
    server = nffg.add_infra(id=getName("host"),
                            **server_res)
    # add supported types
    server.add_supported_type(random.sample(NF_types, 
                                     (next(index_gen()) % len(NF_types)) + 1))
    # connect servers to Fabric Extenders with 10Gbps links
    server_link = {'bandwidth': 100, 'delay': 0.2}
    nffg.add_undirected_link(add_port(server, p), add_port(fe0, p), **server_link)
    nffg.add_undirected_link(add_port(server, p), add_port(fe1, p), **server_link)


def addCloudNFVPart(nffg, an0, an1, p, popn, CL, CH, SE, SAN_bw, SAN_storage,
                    NF_types, SE_cores, SE_mem, SE_storage, CL_bw, CH_links):
  log.debug("Adding Cloud/NFV part for %s."%popn)
  dnres = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
           'bandwidth': 1000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  dn0 = nffg.add_infra(id=getName("dn"), 
                       **dnres)
  dn1 = nffg.add_infra(id=getName("dn"),
                       **dnres)
  addRedundantPairedConnection(nffg, an0, an1, dn0, dn1, p, aggr_link)
  
  # add Server Clusters
  for i in range(0, CL):
    log.debug("Adding Cluster no.%s to Could/NFV part of %s"%(i, popn))
    fi_res = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
              'bandwidth': 1000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
    fabric_interconnect0 = nffg.add_infra(id=getName("fi"), **fi_res)
    fabric_interconnect1 = nffg.add_infra(id=getName("fi"), **fi_res)
    addRedundantPairedConnection(nffg, an0, an1, fabric_interconnect0, 
                                 fabric_interconnect1, p, aggr_link)

    # NOTE: SAN can't host any VNFs now!!
    # SAN is an Infra with big storage (internal bw should be big: e.g. 1Tbps)
    san_res = {'cpu': 0, 'mem': 0, 'storage': SAN_storage, 'delay': 0.1,
              'bandwidth': 1000, 'infra_type': NFFG.TYPE_INFRA_EE}
    san = nffg.add_infra(id=getName("san"), **san_res)
    # connect SAN to Fabric Interconnects
    nffg.add_undirected_link(add_port(san, p), add_port(fabric_interconnect0, p), 
                             bandwidth=SAN_bw, delay=0.1)
    nffg.add_undirected_link(add_port(san, p), add_port(fabric_interconnect1, p), 
                             bandwidth=SAN_bw, delay=0.1)
    # add Chassis
    for j in range(0, CH):
      addCassis(nffg, fabric_interconnect0, fabric_interconnect1, p, i, j, popn,
                SE, NF_types, SE_cores, SE_mem, SE_storage, CL_bw, CH_links)


def addPoP(nffg, popcnt, backbonenode0, backbonenode1, p,
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
  popn = "PoP"+str(popcnt)

  log.debug("Adding PoP %s..."%popcnt)
  # add Aggregation Nodes (1Tbps switching capacity)
  anres = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
           'bandwidth': 1000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  an0 = nffg.add_infra(id=getName("an"), **anres)
  an1 = nffg.add_infra(id=getName("an"), **anres)
  
  # add uplinks to the Backbone
  nffg.add_undirected_link(add_port(an0, p), add_port(backbonenode0, p), 
                           bandwidth=1000, delay=0.1)
  nffg.add_undirected_link(add_port(an1, p), add_port(backbonenode1, p), 
                           bandwidth=1000, delay=0.1)

  addRetailOrBusinessPart(nffg, an0, an1, p, popn, BNAS, RCpb, RCT)
  addRetailOrBusinessPart(nffg, an0, an1, p, popn, PE, BCpb, BCT, 
                          part="B")

  if CL > 0:
      addCloudNFVPart(nffg, an0, an1, p, popn, CL, CH, SE, SAN_bw, SAN_storage,
                      NF_types, SE_cores, SE_mem, SE_storage, CL_bw, CH_links)

  return
    
def getCarrierTopo(params, increment_port_ids=False):
  """
  Construct the core network and add PoPs with their parameters.
  params is a list of dictionaries with PoP data:
    'Retail': (BNAS, RCpb, RCT)
    'Business': (PE, BCpb, BCT)
    'CloudNFV': (CL,CH,SE,SAN_bw,SAN_sto,NF_types,SE_cores,SE_mem,SE_sto,
                 CL_bw, CH_links)
  WARNING: using this function with increment_port_ids=True this function is not 
  thread safe, because it uses global variable then!
  """
  # This initializes the random generator always to the same value, so the
  # returned index sequence, and thus the network parameters will be generated 
  # always the same (we want a fixed network environment)
  # The generated identifiers are still different between genereations, but 
  # those does not influence the mapping process
  random.seed(0)
  popcnt = 0
  nffg = NFFG(id="CarrierTopo")
  p = increment_port_ids
  backbone_res =  {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
                   'bandwidth': 1000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  bn0 = nffg.add_infra(id=getName("bn"), **backbone_res)
  bn1 = nffg.add_infra(id=getName("bn"), **backbone_res)
  bn2 = nffg.add_infra(id=getName("bn"), **backbone_res)
  bn3 = nffg.add_infra(id=getName("bn"), **backbone_res)

  nffg.add_undirected_link(add_port(bn0, p), add_port(bn1, p), bandwidth=1000, 
                           delay=10)
  nffg.add_undirected_link(add_port(bn1, p), add_port(bn2, p), bandwidth=1000, 
                           delay=10)
  nffg.add_undirected_link(add_port(bn2, p), add_port(bn3, p), bandwidth=1000, 
                           delay=10)
  nffg.add_undirected_link(add_port(bn3, p), add_port(bn0, p), bandwidth=1000, 
                           delay=10)
  backbones = (bn0, bn1, bn2, bn3)
  bnlen = len(backbones)
  for popdata in params:
    tmp = []
    tmp.extend(popdata['Retail'])
    tmp.extend(popdata['Business'])
    tmp.extend(popdata['CloudNFV'])
    addPoP(nffg, popcnt, backbones[popcnt%bnlen], backbones[(popcnt+1)%bnlen],
           p, *tmp)
    popcnt += 1
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

def getMediumTopo():
  """
  Constructs a medium sized topology for worst case presentation, if the bigger
  would take too long to finish. Its size is around 12 460 nodes
  (~4500 with SAP cutting)
  """
  topoparams = []
  # params of one PoP
  # 'Retail': (BNAS, RCpb, RCT)
  # 'Business': (PE, BCpb, BCT)
  # 'CloudNFV': (CL,CH,SE,SAN_bw,SAN_sto,NF_types,SE_cores,SE_mem,SE_sto,
  #              CL_bw, CH_links)
  topoparams.append({'Retail': (6, 250, 0.2), 'Business': (6, 200, 0.2),
                     'CloudNFV': (4, 40, 8,  160000, 100000, ['A','B','C'],
                                 [4,8,16],  [32000, 64000], [100,150], 40000, 4)})
  topoparams.append({'Retail': (6, 100, 0.2), 'Business': (4, 200, 0.2),
                     'CloudNFV': (4, 20, 8,  160000, 100000, ['A','B'],
                                  [8,12,16], [32000,64000], [150], 40000, 4)})
  topoparams.append({'Retail': (3, 400, 0.2), 'Business': (8, 100, 0.2),
                    'CloudNFV': (4, 30, 8,  160000, 100000, ['B', 'C'],
                                [4,8,12,16], [32000,64000], [200], 40000, 4)})
  topoparams.append({'Retail': (10, 100, 0.2), 'Business': (8, 150, 0.2),
                    'CloudNFV': (4, 40, 8,  160000, 100000, ['B', 'C'],
                                [4,8,12,16], [32000,64000], [200], 40000, 4)})
  return getCarrierTopo(topoparams), topoparams


def getSmallTopo():
  """
  Constructs a small topology which is structurally similar to carrier topology,
  but could be executed fast enough for testing.
  """
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
  # topoparams.append({'Retail': (2, 4000, 0.2), 'Business': (8, 2000, 0.2),
  #                    'CloudNFV': (2, 40, 8,  160000, 100000, ['B', 'C'], 
  # [4,8,12,16], [32000,64000], [200], 40000, 4)})
  return getCarrierTopo(topoparams), topoparams

def getMicroTopo():
  topoparams = []
  topoparams.append({'Retail': (2, 50, 0.2), 'Business': (2, 30, 0.2),
                     'CloudNFV': (2, 2, 4,  160000, 100000, ['A','B'], 
                                  [8,12,16], [32000,64000], [150], 40000, 4)})
  topoparams.append({'Retail': (2, 50, 0.2), 'Business': (2, 30, 0.2),
                     'CloudNFV': (2, 2, 4,  160000, 100000, ['A','B', 'C'], 
                                  [8,12,16], [32000,64000], [150], 40000, 4)})
  return getCarrierTopo(topoparams), topoparams

def getNanoTopo():
  topoparams = []
  topoparams.append({'Retail': (1, 2, 10), 'Business': (1, 2, 10),
                     'CloudNFV': (1, 2, 4,  1000, 100000, ['A', 'B', 'C'], 
                                  [8,12,16], [32000,64000], [150], 4000, 4)})
  """
  topoparams.append({'Retail': (2, 5, 0.2), 'Business': (2, 5, 0.2),
                     'CloudNFV': (1, 2, 4,  160000, 100000, ['A','B', 'C'], 
                                  [8,12,16], [32000,64000], [150], 4000, 4)})
  """
  return getCarrierTopo(topoparams, increment_port_ids=True), topoparams

def getPicoTopo():
  """
  Not carrier style topo. Few nodes with big resources.
  """
  random.seed(0)
  nffg = NFFG(id="SmallExampleTopo")
  switch = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
            'bandwidth': 1000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  sw = nffg.add_infra(id = getName("sw"), **switch)
  infra = {'cpu': 400, 'mem': 320000, 'storage': 1500, 'delay': 1.0,
           'bandwidth': 10000, 'infra_type': NFFG.TYPE_INFRA_EE}
  linkres = {'bandwidth': 1000, 'delay': 0.5}

  inf1 = nffg.add_infra(id = getName("infra"), **infra)
  inf0 = inf1
  inf1.add_supported_type(list(string.ascii_uppercase)[:10])
  for i in range(0,4):
    if i == 3:
      inf2 = inf0
    else:
      inf2 = nffg.add_infra(id = getName("infra"), **infra)
      inf2.add_supported_type(list(string.ascii_uppercase)[:10])
    nameid = getName("sap")
    sap = nffg.add_sap(id = nameid, name = nameid)
    # add links


    nffg.add_undirected_link(sw.add_port(), inf2.add_port(), **linkres)
    nffg.add_undirected_link(inf1.add_port(), inf2.add_port(), **linkres)
    nffg.add_undirected_link(inf2.add_port(), sap.add_port(), **linkres)
    inf1 = inf2 
    
  return nffg

def getSNDlib_dfn_gwin(save_to_file = False):
  """
  Topology taken from SNDlib, dfn-gwin.
  """
  random.seed(0)
  gwin = nx.read_gml("dfn-gwin.gml")
  nffg = NFFG(id="dfn-gwin")
  nf_types = list(string.ascii_uppercase)[:10]
  switch = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
            'bandwidth': 40000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  infrares = {'cpu': 400, 'mem': 320000, 'storage': 1500, 'delay': 1.0,
           'bandwidth': 40000, 'infra_type': NFFG.TYPE_INFRA_EE}
  corelinkres = {'bandwidth': 10000, 'delay': 1.0}
  aggrlinkres = {'bandwidth': 1000, 'delay': 5.0}
  acclinkres = {'bandwidth': 100, 'delay': 1.0}
  gwinnodes = []
  for n in  gwin.nodes_iter():
    gwinnodes.append(n.rstrip('.'))
  # get topology from dfn-gwin
  for n in gwinnodes:
    nffg.add_infra(id=n, **switch)
  for i,j in gwin.edges_iter():
    nffg.add_undirected_link(nffg.network.node[i.rstrip('.')].add_port(), 
                             nffg.network.node[j.rstrip('.')].add_port(), 
                             **corelinkres)

  
  nodeset1 = random.sample(gwinnodes, 3)
  nodeset1.extend(random.sample(gwinnodes, 3))
  # add cloud nodes to 6 random nodes.
  for n in nodeset1:
    infra = nffg.add_infra(id=getName(n+"Host"), **infrares)
    infra.add_supported_type(random.sample(nf_types, 6))
    nffg.add_undirected_link(nffg.network.node[n].add_port(), infra.add_port(), 
                             **corelinkres)
    
  nodeset2 = random.sample(gwinnodes, 3)
  nodeset2.extend(random.sample(gwinnodes, 3))
  # add access switched to 6 random nodes
  for n in nodeset2:
    sw = nffg.add_infra(id=getName(n+"Sw"), **switch)
    nffg.add_undirected_link(nffg.network.node[n].add_port(), sw.add_port(),
                             **aggrlinkres)
    for i in xrange(0,random.randint(3,4)):
      nameid = getName(n+"SAP")
      sap = nffg.add_sap(id=nameid, name=nameid)
      nffg.add_undirected_link(sap.add_port(), sw.add_port(), **acclinkres)
  
  # save it to file
  if save_to_file:
    augmented_gwin = nx.MultiDiGraph()
    augmented_gwin.add_nodes_from(nffg.network.nodes_iter())
    augmented_gwin.add_edges_from(nffg.network.edges_iter())
    nx.write_gml(augmented_gwin, "augmented-dfn-gwin.gml")

  return nffg
  

if __name__ == '__main__':
  topoparams = []
  # params of one PoP
  # 'Retail': (BNAS, RCpb, RCT)
  # 'Business': (PE, BCpb, BCT)
  # 'CloudNFV': (CL,CH,SE,SAN_bw,SAN_sto,NF_types,SE_cores,SE_mem,SE_sto,
  #              CL_bw, CH_links)
  # print getSNDlib_dfn_gwin().dump() NOT WORKING.
  topoparams.append({'Retail': (2, 10000, 0.2), 'Business': (2, 8000, 0.2), 
                     'CloudNFV': (2, 8, 8,  160000, 100000, ['A','B','C'], 
                                  [4,8,16],  [32000], [100,150],   40000, 4)})
  topoparams.append({'Retail': (2, 10000, 0.2), 'Business': (4, 4000, 0.2),
                     'CloudNFV': (2, 8, 8,  160000, 100000, ['A','B'], 
                                  [8,12,16], [32000,64000], [150], 40000, 4)})
  # topoparams.append({'Retail': (2, 20000, 0.2), 'Business': (8, 4000, 0.2),
  #                    'CloudNFV': (2, 40, 8,  160000, 100000, ['B', 'C'], 
  #                                 [4,8,12,16], [32000,64000], [200], 40000, 4)})
  # topo = getCarrierTopo(topoparams)
  # print topo.dump()
