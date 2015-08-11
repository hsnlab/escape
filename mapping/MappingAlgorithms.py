# Copyright (c) 2014 Balazs Nemeth
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
Interface for the Mapping Algorithms provided for ESCAPE.
Receives the service request and the resource information in the internal
(NetworkX based) NFFG model, and gives it to the algorithm covering its 
invocation details.
NOTE: Currently only SAP-to-SAP EdgeReqs, or link-local (which are parallel 
with an SGLink) EdgeReqs are supported. After generating the service chains
from the EdgeReqs, all SG links must be in one of the subchains. 
TODO: map best-effort links.
"""

from pprint import pformat
import traceback

import networkx as nx

try:
  from escape.util.nffg import NFFG, generate_dynamic_fallback_nffg
except ImportError:
  import sys, os, inspect

  sys.path.insert(0, os.path.join(os.path.abspath(os.path.realpath(
    os.path.abspath(
      os.path.split(inspect.getfile(inspect.currentframe()))[0])) + "/.."),
                                  "pox/ext/escape/util/"))
  from nffg import NFFG, generate_dynamic_fallback_nffg
from Alg1_Core import CoreAlgorithm
import UnifyExceptionTypes as uet
# object for the algorithm instance
alg = None


def MAP (request, network):
  """
  The parameters are NFFG classes.
  Calculates service chain requirements from EdgeReq classes.
  """
  # EdgeReqs don`t specify exactly on which paths the requirement should hold
  # suppose we need it on all paths.
  # IF the EdgeReq link is parallel to an SGLink, the request applies to the
  # link (and possibly other directed paths between the two VNFs)
  chainlist = []
  cid = 1
  edgereqlist = []
  for req in request.reqs:
    edgereqlist.append(req)
    request.del_edge(req.src, req.dst, req.id)

  for req in edgereqlist:
    number_of_simple_paths = 0
    chains_of_one_req = []
    for path in nx.all_simple_paths(request.network, req.src.node.id,
                                    req.dst.node.id):
      chain = {'chain': path, 'link_ids': []}
      is_there_notSGlink_in_path = False
      for i, j in zip(path[:-1], path[1:]):
        for sglink in request.sg_hops:
          if i == sglink.src.node.id and j == sglink.dst.node.id:
            if len(path) == 2:
              # then add it as linklocal req insead of E2E
              if req.delay is not None:
                setattr(request.network[i][j][sglink.id], 'delay', req.delay)
              if req.bandwidth is not None:
                setattr(request.network[i][j][sglink.id], 'bandwidth',
                        req.bandwidth)
            else:
              chain['link_ids'].append(sglink.id)
            break  # warning! the second of the double links in SG
            # will not be taken into any service, which causes the
            # algorithm to throw a bad input exception because not
            # all SG links are in some subchain
        else:
          # This means `path` is not entirely in the service graph,
          # so this should be ignored.
          is_there_notSGlink_in_path = True
          break

      if not is_there_notSGlink_in_path:
        if len(path) != 2:
          if len(path) - 1 != len(chain['link_ids']):
            raise Exception(
              "TEMPORARY Exception: Not all link ID-s found for a service "
              "chain")
          chain['id'] = cid
          cid += 1
          chain['delay'] = req.delay
          chains_of_one_req.append(chain)
          number_of_simple_paths += 1
          # else: In this case the SG link has been added as link
          # requirement to the service graph

    # distribute the bandwidth requirement uniformly...
    for c in chains_of_one_req:
      if req.bandwidth is not None:
        c['bandwidth'] = float(req.bandwidth) / number_of_simple_paths
      else:
        c['bandwidth'] = 0
    chainlist.extend(chains_of_one_req)

  # create the class of the algorithm
  alg = CoreAlgorithm(network, request, chainlist)
  mappedNFFG = alg.start()

  # put the EdgeReqs back to the mappedNFFG for the lower layer
  # (NFFG splitting is omitted for now, lower layer gets the full NFFG)
  # port adding is necessary, because SAPs can be with different ID in the
  # two NFFGs and add_edge() uses the ID of the port`s parent.
  for req in edgereqlist:
    srcnode = req.src.node
    dstnode = req.dst.node
    if req.src.node.type == 'SAP':
      srcnode = mappedNFFG.network.node[
        alg.manager.getIdOfChainEnd_fromNetwork(req.src.node.id)]
    if req.dst.node.type == 'SAP':
      dstnode = mappedNFFG.network.node[
        alg.manager.getIdOfChainEnd_fromNetwork(req.dst.node.id)]
    mappedNFFG.add_req(srcnode.add_port(), dstnode.add_port(), id=req.id,
                       delay=req.delay, bandwidth=req.bandwidth)

  # print mappedNFFG.dump()
  # The printed format is vnfs: (vnf_id, node_id) and links: MultiDiGraph, edge
  # data is the paths (with link ID-s) where the request links are mapped.
  # print "\nThe VNF mappings are (vnf_id, node_id):\n", pformat(
  #   alg.manager.vnf_mapping)
  # print "\n The link mappings are:\n", pformat(
  #   alg.manager.link_mapping.edges(data=True, keys=True))

  # n0_nffg = alg.returnMappedNFFGofOneBiSBiS("node0")
  # n1_nffg = alg.returnMappedNFFGofOneBiSBiS("node1")
  # n2_nffg = alg.returnMappedNFFGofOneBiSBiS("node2")

  return mappedNFFG


def _constructExampleRequest ():
  nffg = NFFG(id="BME-req-001")
  sap0 = nffg.add_sap(name="SAP0", id="sap0")
  sap1 = nffg.add_sap(name="SAP1", id="sap1")

  # add NF requirements.
  # Note: storage is used now for the first time, it comes in with the
  # NodeResource class
  # Note: internal latency is only forwarded to lower layer
  # Note: internal bw is untested yet, even before the NFFG support
  nf0 = nffg.add_nf(id="NF0", name="NetFunc0", func_type='A', cpu=2, mem=2,
                    storage=2, bandwidth=100)
  nf1 = nffg.add_nf(id="NF1", name="NetFunc1", func_type='B', cpu=1.5, mem=1.5,
                    storage=1.5, delay=50)
  nf2 = nffg.add_nf(id="NF2", name="NetFunc2", func_type='C', cpu=3, mem=3,
                    storage=3, bandwidth=500)
  nf3 = nffg.add_nf(id="NF3", name="NetFunc3", func_type='A', cpu=2, mem=2,
                    storage=2, bandwidth=100, delay=50)
  nf4 = nffg.add_nf(id="NF4", name="NetFunc4", func_type='C', cpu=0, mem=0,
                    storage=0, bandwidth=500)

  # directed SG links
  # flowclass defaul: None, meaning: match all traffic
  # some agreement on flowclass format is required.
  nffg.add_sglink(sap0.add_port(0), nf0.add_port(0))
  nffg.add_sglink(nf0.add_port(1), nf1.add_port(0), flowclass="HTTP")
  nffg.add_sglink(nf1.add_port(1), nf2.add_port(0), flowclass="HTTP")
  nffg.add_sglink(nf2.add_port(1), sap1.add_port(1))
  nffg.add_sglink(nf0.add_port(2), nf3.add_port(0), flowclass="non-HTTP")
  nffg.add_sglink(nf3.add_port(1), nf2.add_port(2), flowclass="non-HTTP")
  nffg.add_sglink(nf1.add_port(2), nf4.add_port(0), flowclass="index.com")
  nffg.add_sglink(nf4.add_port(1), nf2.add_port(3), flowclass="index.com")

  # add EdgeReqs
  nffg.add_req(sap0.ports[0], sap1.ports[1], delay=40, bandwidth=1500)
  nffg.add_req(nf1.ports[1], nf2.ports[0], delay=3.5)
  nffg.add_req(nf3.ports[1], nf2.ports[2], bandwidth=500)
  nffg.add_req(sap0.ports[0], nf0.ports[0], delay=3.0)
  # force collocation of NF0 and NF3
  # nffg.add_req(nf0.ports[2], nf3.ports[0], delay=1.0)
  # not SAP-to-SAP requests are not taken into account yet, these are ignored
  nffg.add_req(nf0.ports[1], nf2.ports[0], delay=1.0)

  # test Infra node removal from the request NFFG
  infra1 = nffg.add_infra(id="BiS-BiS1")
  infra2 = nffg.add_infra(id="BiS-BiS2")
  nffg.add_undirected_link(infra1.add_port(0), nf0.add_port(3), dynamic=True)
  nffg.add_undirected_link(infra1.add_port(1), nf0.add_port(4), dynamic=True)
  nffg.add_undirected_link(infra1.add_port(2), nf1.add_port(2), dynamic=True)
  nffg.add_undirected_link(infra2.add_port(0), nf2.add_port(3), dynamic=True)
  nffg.add_undirected_link(infra2.add_port(1), nf3.add_port(2), dynamic=True)
  nffg.add_undirected_link(infra1.add_port(3), infra2.add_port(2),
                           bandwidth=31241242)

  return nffg


def _constructExampleNetwork ():
  nffg = NFFG(id="BME-net-001")
  uniformnoderes = {'cpu': 5, 'mem': 5, 'storage': 5, 'delay': 0.9,
                    'bandwidth': 5500}
  infra0 = nffg.add_infra(id="node0", name="INFRA0", **uniformnoderes)
  infra1 = nffg.add_infra(id="node1", name="INFRA1", **uniformnoderes)
  infra2 = nffg.add_infra(id="node2", name="INFRA2", **uniformnoderes)
  switch = nffg.add_infra(id="sw0", name="FastSwitcher", delay=0.01,
                          bandwidth=10000)
  infra0.add_supported_type('A')
  infra1.add_supported_type(['B', 'C'])
  infra2.add_supported_type(['A', 'B', 'C'])
  sap0 = nffg.add_sap(name="SAP0", id="sap0innet")
  sap1 = nffg.add_sap(name="SAP1", id="sap1innet")

  unilinkres = {'delay': 1.5, 'bandwidth': 2000}
  # Infra links should be undirected, according to the currnet NFFG model
  # Infra link model is full duplex now.
  nffg.add_undirected_link(sap0.add_port(0), infra0.add_port(0), **unilinkres)
  nffg.add_undirected_link(sap1.add_port(0), infra1.add_port(0), **unilinkres)
  nffg.add_undirected_link(infra1.add_port(1), infra0.add_port(2), **unilinkres)
  nffg.add_undirected_link(infra0.add_port(1), infra2.add_port(0), **unilinkres)
  nffg.add_undirected_link(infra1.add_port(2), infra2.add_port(1), **unilinkres)
  unilinkres['delay'] = 0.2
  unilinkres['bandwidth'] = 5000
  nffg.add_undirected_link(switch.add_port(0), infra0.add_port(3), **unilinkres)
  nffg.add_undirected_link(switch.add_port(1), infra1.add_port(3), **unilinkres)
  nffg.add_undirected_link(switch.add_port(2), infra2.add_port(2), **unilinkres)

  # test VNF mapping removal, and resource update in the substrate NFFG
  nf4 = nffg.add_nf(id="NF4inNet", name="NetFunc4", func_type='B', cpu=1, mem=1,
                    storage=1, bandwidth=100, delay=50)
  nffg.add_undirected_link(infra1.add_port(3), nf4.add_port(0), dynamic=True)
  nffg.add_undirected_link(infra1.add_port(4), nf4.add_port(1), dynamic=True)

  return nffg


def _example_request_for_fallback ():
  nffg = NFFG(id="FALLBACK-REQ", name="fallback-req")
  sap1 = nffg.add_sap(name="SAP1", id="sap1")
  sap2 = nffg.add_sap(name="SAP2", id="sap2")

  # add NF requirements.
  nf0 = nffg.add_nf(id="NF0", name="NetFunc0", func_type='B', cpu=2, mem=2,
                    storage=2, bandwidth=100)
  nf1 = nffg.add_nf(id="NF1", name="NetFunc1", func_type='A', cpu=1.5, mem=1.5,
                    storage=1.5, delay=50)
  nf2 = nffg.add_nf(id="NF2", name="NetFunc2", func_type='C', cpu=3, mem=3,
                    storage=3, bandwidth=500)
  nf3 = nffg.add_nf(id="NF3", name="NetFunc3", func_type='A', cpu=2, mem=2,
                    storage=2, bandwidth=100, delay=50)

  # add SG hops
  nffg.add_sglink(sap1.add_port(0), nf0.add_port(0), id="s1n0")
  nffg.add_sglink(nf0.add_port(1), nf1.add_port(0), id="n0n1")
  nffg.add_sglink(nf1.add_port(1), nf2.add_port(0), id="n1n2")
  nffg.add_sglink(nf1.add_port(2), nf3.add_port(0), id="n1n3")
  nffg.add_sglink(nf2.add_port(1), sap2.add_port(0), id="n2s2")
  nffg.add_sglink(nf3.add_port(1), sap2.add_port(1), id="n3s2")

  # add EdgeReqs
  # port number on SAP2 doesn`t count
  nffg.add_req(sap1.ports[0], sap2.ports[1], bandwidth=1000, delay=24)
  nffg.add_req(nf0.ports[1], nf1.ports[0], bandwidth=200)
  nffg.add_req(nf0.ports[1], nf1.ports[0], delay=3)

  # set placement criteria. Should be used to enforce the placement decision of
  # the upper orchestration layer. Placement criteria can contain multiple
  # InfraNode id-s, if the BiS-BiS is decomposed to multiple InfraNodes in this
  # layer.
  # setattr(nf1, 'placement_criteria', ['nc2'])

  return nffg


if __name__ == '__main__':
  try:
    # req = _constructExampleRequest()
    # net = _constructExampleNetwork()

    req = _example_request_for_fallback()
    # this is the dynamic fallback topology taken from nffg.py
    net = generate_dynamic_fallback_nffg()
    mapped = MAP(req, net)
    print mapped.dump()
  except uet.UnifyException as ue:
    print ue, ue.msg
    print traceback.format_exc()
