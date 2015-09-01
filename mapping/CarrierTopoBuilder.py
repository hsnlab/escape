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

def addRedundantPairedConnection(nffg, an0, an1, bn0, bn1, linkres):
  """
  Connects A-s to B-s and B-s to A-s with undirected links with linkres.
  """
  nffg.add_undirected_link(an0.add_port(), bn0.add_port(), **linkres)
  nffg.add_undirected_link(an0.add_port(), bn1.add_port(), **linkres)
  nffg.add_undirected_link(an1.add_port(), bn0.add_port(), **linkres)
  nffg.add_undirected_link(an1.add_port(), bn1.add_port(), **linkres)


def addRetailOrBusinessPart(nffg, an0, an1, popn, BNAS_PE, 
                            Cpb, access_bw, part="Retail"):
  """
  Retail and Business part inside one PoP is structurally the same.
  """
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
    for j in range(0, Cpb):
      nameid = part+"-SAP-"+str(j)+"-switch-"+str(i)+popn
      sap = nffg.add_sap(id=nameid, name=nameid)
      access_link = {'bandwidth': access_bw, 'delay': 0.5}
      nffg.add_undirected_link(bnas_pe.add_port(), sap.add_port(), **access_link)


def addCassis(nffg, fi0, fi1, cluster_id, chassis_id, popn, 
              SE, SE_cores, SE_mem, SE_storage, CL_bw, CH_links):
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
    server_res = {'cpu': SE_cores, 'mem': SE_mem, 'storage': SE_storage, 
                  'delay': 0.5, 'bandwidth': 100000, 'infra_type': NFFG.TYPE_INFRA_EE}
    server = nffg.add_infra(id="Server-"+str(s)+"-Chassis-"+str(chassis_id)+\
                            "-Cluster-"+str(cluster_id)+popn,
                            **server_res)
    # TODO: add supported types
    
    # connect servers to Fabric Extenders with 10Gbps links
    server_link = {'bandwidth': 10000, 'delay': 0.2}
    nffg.add_undirected_link(server.add_port(), fe0.add_port(), **server_link)
    nffg.add_undirected_link(server.add_port(), fe1.add_port(), **server_link)


def addCloudNFVPart(nffg, an0, an1, popn, CL, CH, SE, SAN_bw, SAN_storage,
                    SE_cores, SE_mem, SE_storage, CL_bw, CH_links):
  dnres = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
           'bandwidth': 100000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  dn0 = nffg.add_infra(id="DistributionNode"+popn+"CloudNFV-0", 
                       **dnres)
  dn1 = nffg.add_infra(id="DistributionNode"+popn+"CloudNFV-1",
                       **dnres)
  addRedundantPairedConnection(nffg, an0, an1, dn0, dn1, aggr_link)
  
  # add Server Clusters
  for i in range(0, CL):
    fi_res = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
              'bandwidth': 100000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
    fabric_interconnect0 = nffg.add_infra(id="FabricInterconnect-0-Cluster-"+\
                                          str(i)+popn, **fi_res)
    fabric_interconnect1 = nffg.add_infra(id="FabricInterconnect-1-Cluster-"+\
                                          str(i)+popn, **fi_res)
    addRedundantPairedConnection(nffg, an0, an1, fabric_interconnect0, 
                                 fabric_interconnect1, aggr_link)
    
    # SAN is an Infra with big storage (internal bw should be big: e.g. 1Tbps)
    san_res = {'cpu': 0, 'mem': 0, 'storage': SAN_storage, 'delay': 0.1,
              'bandwidth': 1000000, 'infra_type': NFFG.TYPE_INFRA_EE}
    san = nffg.add_infra(id="SAN-Cluster-"+str(i)+popn, **san_res)
    # TODO: add supported types
    # connect SAN to Fabric Interconnects
    nffg.add_undirected_link(san.add_port(), fabric_interconnect0.add_port(), 
                             bandwidth=SAN_bw, delay=0.1)
    nffg.add_undirected_link(san.add_port(), fabric_interconnect1.add_port(), 
                             bandwidth=SAN_bw, delay=0.1)
    # add Chassis
    for j in range(0, CH):
      addCassis(nffg, fabric_interconnect0, fabric_interconnect1, i, j, popn, 
                SE, SE_cores, SE_mem, SE_storage, CL_bw, CH_links)


def addPoP(nffg, backbonenode0, backbonenode1, 
           BNAS, RCpb, RCT, 
           PE, BCpb, BCT,
           CL, CH, SE, SAN_bw, SAN_storage, 
           SE_cores, SE_mem, SE_storage, CL_bw, CH_links):
  """
  Create one PoP which consists of three domain:
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
  SE_cores: number of cores per server (~8-16)
  SE_mem: memory per server (~32000MB - 64000MB)
  SE_storage: (~300GB - 1500GB)
  CL_bw: cluster bandwidth to servers per Chassis (~40Gbps - 160Gbps)
  CH_links: number of uplinks per Chassis (~4-16)
    NOTE: Link bw from Fabric Extender to Fabric Interc. equals 
    CL_bw/CH_links (~10Gbps).
  """
  global popcnt
  popn = "-PoP-"+str(popcnt)
  # add Aggregation Nodes (1Tbps switching capacity)
  anres = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
           'bandwidth': 1000000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  an0 = nffg.add_infra(id="AggregationNode"+popn+"0", **anres)
  an1 = nffg.add_infra(id="AggregationNode"+popn+"1", **anres)
  
  # add uplinks to the Backbone
  nffg.add_undirected_link(an0.add_port(), backbonenode0.add_port(), 
                           bandwidth=1000000, delay=0.1)
  nffg.add_undirected_link(an1.add_port(), backbonenode1.add_port(), 
                           bandwidth=1000000, delay=0.1)

  addRetailOrBusinessPart(nffg, an0, an1, popn, BNAS, RCpb, RCT)
  addRetailOrBusinessPart(nffg, an0, an1, popn, PE, BCpb, BCT, part="Business")

  if CL > 0:
      addCloudNFVPart(nffg, an0, an1, popn, CL, CH, SE, SAN_bw, SAN_storage,
                      SE_cores, SE_mem, SE_storage, CL_bw, CH_links)

  popcnt += 1
  return
    
def getCarrierTopo():
  """
  Construct the core network and add PoPs with their parameters.
  """
  nffg = NFFG(id="CarrierTopo")
  backbone_res =  {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.5,
                   'bandwidth': 10000000, 'infra_type': NFFG.TYPE_INFRA_SDN_SW}
  bn0 = nffg.add_infra(id="BackboneNode0", **backbone_res)
  bn1 = nffg.add_infra(id="BackboneNode1", **backbone_res)
  nffg.add_undirected_link(bn0.add_port(), bn1.add_port(), bandwidth=1000000, 
                           delay=10)
  #                      BNAS,RCpb,  RCT, PE,BCpb, BCT, CL,SE,SE_cores,SAN_bw, 
  addPoP(nffg, bn0, bn1, 2,   10000, 0.2, 2, 4000, 0.2, 2, 8, 8,       160000,  
       # SAN_sto,  SE_cores,SE_mem,SE_sto,CL_bw, CH_links
         100000,   8,       32000, 150,   40000, 4)
  return nffg

if __name__ == '__main__':
  topo = getCarrierTopo()
  print topo.dump()
