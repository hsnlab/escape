# Copyright 2015 Sahel Sahhaf <sahel.sahhaf@intec.ugent.be>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Test different interfaces of the NFIB
"""

from escape.orchest.nfib_mgmt import NFIBManager
from escape.util.nffg import *


def testNFIB ():
  NFIB = NFIBManager()

  # start clean - all the existing info is removed from the DB
  NFIB.removeGraphDB()

  # add new high-level NF to the DB, all the information related to the NF
  # should be given as a dict

  NFIB.addNode({'label': 'NF', 'node_id': 'forwarder', 'type': 'NA'})
  NFIB.addNode({'label': 'NF', 'node_id': 'compressor', 'type': 'NA'})
  NFIB.addNode({'label': 'NF', 'node_id': 'decompressor', 'type': 'NA'})

  print "high-level  NFs were added to the DB"

  # generate a  decomposition for a high-level forwarder NF (in form of
  # networkx)
  G1 = networkx.DiGraph()
  G1.add_path(['SAP1', 'simpleForwarder', 'SAP2'])

  # create node properties
  for n in G1.nodes():
    properties = {}
    properties['node_id'] = n

    if 'SAP' in n:
      properties['label'] = 'SAP'
      properties['type'] = 'NA'
    else:
      properties['label'] = 'NF'
      properties['type'] = 'click'
      properties['cpu'] = 10
      properties['mem'] = 100
      properties['storage'] = 100
    G1.node[n]['properties'] = properties

  # create edge properties
  properties = {}
  properties['BW'] = 100
  properties['src_port'] = 1
  properties['dst_port'] = 1
  G1.edge['SAP1']['simpleForwarder']['properties'] = properties

  properties1 = {}
  properties1['BW'] = 100
  properties1['src_port'] = 2
  properties1['dst_port'] = 2
  G1.edge['simpleForwarder']['SAP2']['properties'] = properties1

  # generate a decomposition for a high-level compressor NF (in form of
  # networkx)
  G2 = networkx.DiGraph()
  G2.add_path(['SAP3', 'headerCompressor', 'SAP4'])

  # create node properties
  for n in G2.nodes():
    properties = {}
    properties['node_id'] = n
    if 'SAP' in n:
      properties['label'] = 'SAP'
      properties['type'] = 'NA'
    else:
      properties['label'] = 'NF'
      properties['type'] = 'click'
      properties['cpu'] = 20
      properties['mem'] = 200
      properties['storage'] = 200
    G2.node[n]['properties'] = properties

  # create edge properties 
  properties3 = {}
  properties3['BW'] = 200
  properties3['src_port'] = 1
  properties3['dst_port'] = 1
  G2.edge['SAP3']['headerCompressor']['properties'] = properties3

  properties4 = {}
  properties4['BW'] = 200
  properties4['src_port'] = 2
  properties4['dst_port'] = 2
  G2.edge['headerCompressor']['SAP4']['properties'] = properties4

  # generate a decomposition for a high-level decompressor NF (in form of
  # networkx)
  G3 = networkx.DiGraph()
  G3.add_path(['SAP5', 'headerDecompressor', 'SAP6'])

  # create node properties
  for n in G3.nodes():
    properties = {}
    properties['node_id'] = n
    if 'SAP' in n:
      properties['label'] = 'SAP'
      properties['type'] = 'NA'
    else:
      properties['label'] = 'NF'
      properties['type'] = 'click'
      properties['cpu'] = 30
      properties['mem'] = 300
      properties['storage'] = 300
    G3.node[n]['properties'] = properties

  # create edge properties
  properties5 = {}
  properties5['BW'] = 300
  properties5['src_port'] = 1
  properties5['dst_port'] = 1
  G3.edge['SAP5']['headerDecompressor']['properties'] = properties5

  properties6 = {}
  properties6['BW'] = 300
  properties6['src_port'] = 2
  properties6['dst_port'] = 2
  G3.edge['headerDecompressor']['SAP6']['properties'] = properties6

  # required elementary NFs should be added first to the DB
  NFIB.addClickNF({'label': 'NF', 'node_id': 'Queue', 'type:': 'click'})
  NFIB.addClickNF({'label': 'NF', 'node_id': 'Classifier', 'type': 'click'})
  NFIB.addClickNF({'label': 'NF', 'node_id': 'Counter', 'type': 'click'})
  NFIB.addClickNF({'label': 'NF', 'node_id': 'RFC2507Comp', 'type': 'click'})
  NFIB.addClickNF({'label': 'NF', 'node_id': 'RFC2507Decomp', 'type': 'click'})

  # the NF decompositions are added to the DB
  NFIB.addDecomp('forwarder', 'G1', G1)
  NFIB.addDecomp('compressor', 'G2', G2)
  NFIB.addDecomp('decompressor', 'G3', G3)

  print "NF decompositions were added to the DB"

  # create an NFFG with high-level NFs
  nffg = NFFG(id="iMinds-001")
  infra = nffg.add_infra(id="node0", name="INFRA0")
  sap0 = nffg.add_sap(id="SG_SAP1")
  sap1 = nffg.add_sap(id="SG_SAP2")
  nf1 = nffg.add_nf(id="compressor")
  nf2 = nffg.add_nf(id="forwarder")
  nf3 = nffg.add_nf(id="decompressor")
  nffg.add_link(sap0.add_port(1), infra.add_port(0), id="infra_in")
  nffg.add_link(sap1.add_port(1), infra.add_port(1), id="infra_out")
  nffg.add_link(infra.add_port(2), nf1.add_port(1), id="nf1_in", dynamic=True)
  nffg.add_link(nf1.add_port(2), infra.add_port(3), id="nf1_out", dynamic=True)
  nffg.add_link(infra.add_port(4), nf2.add_port(1), id="nf2_in", dynamic=True)
  nffg.add_link(nf2.add_port(2), infra.add_port(5), id="nf2_out", dynamic=True)
  nffg.add_link(infra.add_port(6), nf3.add_port(1), id="nf3_in", dynamic=True)
  nffg.add_link(nf3.add_port(2), infra.add_port(7), id="nf3_out", dynamic=True)

  nffg.add_sglink(sap0.ports[1], nf1.ports[1], id="hop1")
  nffg.add_sglink(nf1.ports[2], nf2.ports[1], id="hop2")
  nffg.add_sglink(nf2.ports[2], nf3.ports[1], id="hop3")
  nffg.add_sglink(nf3.ports[2], sap1.ports[1], id="hop4")
  nffg.add_sglink(sap1.ports[1], sap0.ports[1], id="hop_back")

  nffg.add_req(sap0.ports[1], sap1.ports[1], id="req", delay=10, bandwidth=100)

  # retrieve all possible decompositions for the generated nffg (a dict of nffg)
  decomps = NFIB.getDecomps(nffg)
  print "All possible decompositions were retrieved form the DB"

  for n in decomps['D0'].nfs:
    print NFIB.getNF(n.id)


testNFIB()
