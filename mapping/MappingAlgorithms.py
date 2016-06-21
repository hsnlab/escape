#!/usr/bin/python -u
#
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
Interface for the Mapping Algorithms provided for ESCAPE.
Receives the service request and the resource information in the internal
(NetworkX based) NFFG model, and gives it to the algorithm covering its 
invocation details.
NOTE: Currently only SAP-to-SAP EdgeReqs, or link-local (which are parallel 
with an SGLink) EdgeReqs are supported. After generating the service chains
from the EdgeReqs, all SG links must be in one of the subchains. 
TODO: map best-effort links (not part of any subchain).
"""

import traceback

from pprint import pformat

try:
  from escape.nffg_lib.nffg import NFFG, NFFGToolBox
except ImportError:
  import sys, os
  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                  "../escape/escape/nffg_lib/")))
  from nffg import NFFG, NFFGToolBox
from Alg1_Core import CoreAlgorithm
import UnifyExceptionTypes as uet
import Alg1_Helper as helper

# object for the algorithm instance
alg = None

def _purgeNFFGFromInfinityValues(nffg):
  """
  Before running the algorithm None values for resources were replaced by 
  Infinity value to ensure seamless mapping, in case of missing parameters.
  These values should be set back to None to cooperate with surrounding layers.
  (zero values do not cause errors, and they can't be placed back unabiguously)
  """
  purge = False
  for respar in ('cpu', 'mem', 'storage', 'bandwidth'):
    for n in nffg.infras:
      if hasattr(n.resources, respar):
        if n.resources[respar] == float("inf"):
          n.resources[respar] = None
          purge = True
  if purge:
    helper.log.info("Purging node resource data of output NFFG from Infinity "
                    "values was required.")
  purge = False
  for i, j, d in nffg.network.edges_iter(data=True):
    if d.type == 'STATIC':
      if hasattr(d, 'bandwidth'):
        if d.bandwidth == float("inf"):
          d.bandwidth = None
          purge = True
  if purge:
    helper.log.info("Purging link resource of output NFFG from Infinity values"
                    " was required.")

def MAP (request, network, full_remap=False,
         enable_shortest_path_cache=False,
         bw_factor=1, res_factor=1, lat_factor=1,
         shortest_paths=None, return_dist=False,
         bt_limit=6, bt_branching_factor=3):
  """
  The parameters are NFFG classes.
  Calculates service chain requirements from EdgeReq classes.
  enable_shortest_path_cache: whether we should store the calculated shortest 
  paths in a file for later usage.
  full_remap: whether the resources of the VNF-s contained in the resource
  NFFG be subtracted and deleted or just deleted from the resource NFFG 
  before mapping.
  """
  sg_hops_given = True
  try:
    # if there is at least ONE SGHop in the graph, we don't do SGHop retrieval.
    next(request.sg_hops)
  except StopIteration:
    # retrieve the SGHops from the TAG values of the flow rules, in case they
    # are cannot be found in the request graph and can only be deduced from the 
    # flows
    helper.log.warn("No SGHops were given in the Service Graph, retrieving them"
                    " based on the flowrules...")
    sg_hops_given = False
    sg_hop_info = NFFGToolBox.retrieve_all_SGHops(request)
    helper.log.log(5, "Retrieved SG hops:\n" + pformat(sg_hop_info))
    if len(sg_hop_info) == 0:
      raise uet.BadInputException("If SGHops are not given, flowrules should be"
                                  " in the NFFG",
                                  "No SGHop could be retrieved based on the "
                                  "flowrules of the NFFG.")
    for k, v in sg_hop_info.iteritems():
      # VNF ports are given to the function
      request.add_sglink(v[0], v[1], flowclass=v[2], bandwidth=v[3], delay=v[4],
                         id=k[2])

  chainlist = []
  cid = 1
  edgereqlist = []
  # a delay value which is assumed to be infinity in terms of connection RTT 
  # or latency requirement (set it to 100s = 100 000ms)
  overall_highest_delay = 100000
  for req in request.reqs:
    edgereqlist.append(req)
    request.del_edge(req.src, req.dst, req.id)

  if len(edgereqlist) != 0 and not sg_hops_given:
    helper.log.warn("EdgeReqs were given, but the SGHops (which the EdgeReqs "
                    "refer to by id) are retrieved based on the flowrules of "
                    "infrastructure. This can cause error later if the "
                    "flowrules was malformed...")

  # construct chains from EdgeReqs
  for req in edgereqlist:

    if len(req.sg_path) == 1:
      # then add it as linklocal req instead of E2E req
      helper.log.info("Interpreting one SGHop long EdgeReq (id: %s) as link "
                      "requirement on SGHop: %s."%(req.id, req.sg_path[0]))
      reqlink = None
      for sg_link in request.sg_hops:
        if sg_link.id == req.sg_path[0]:
          reqlink = sg_link
          break
      if reqlink is None:
        helper.log.warn("EdgeSGLink object not found for EdgeSGLink ID %s! "
                        "(maybe ID-s stored in EdgeReq.sg_path are not the "
                        "same type as EdgeSGLink ID-s?)")
      if req.delay is not None:
        setattr(reqlink, 'delay', req.delay)
      if req.bandwidth is not None:
        setattr(reqlink, 'bandwidth', req.bandwidth)
    elif len(req.sg_path) == 0:
      raise uet.BadInputException(
         "If EdgeReq is given, it should specify which SGHop path does it "
         "apply to", "Empty SGHop path was given to %s EdgeReq!" % req.id)
    else:
      try:
        chain = {'id': cid, 'link_ids': req.sg_path,
                 'bandwidth': req.bandwidth if req.bandwidth is not None else 0,
                 'delay': req.delay if req.delay is not None \
                 else overall_highest_delay}
      except AttributeError:
        raise uet.BadInputException(
           "EdgeReq attributes are: sg_path, bandwidth, delay",
           "Missing attribute of EdgeReq")
      # reconstruct NF path from EdgeSGLink path
      nf_chain = []
      for reqlinkid in req.sg_path:

        # find EdgeSGLink object of 'reqlinkid'
        reqlink = None
        for sg_link in request.sg_hops:
          if sg_link.id == reqlinkid:
            reqlink = sg_link
            break
        else:
          raise uet.BadInputException(
             "Elements of EdgeReq.sg_path should be EdgeSGLink.id-s.",
             "SG link %s couldn't be found in input request NFFG" % reqlinkid)
        # add the source node id of the EdgeSGLink to NF path
        nf_chain.append(reqlink.src.node.id)
        # add the destination node id of the last EdgeSGLink to NF path
        if reqlinkid == req.sg_path[-1]:
          if reqlink.dst.node.id != req.dst.node.id:
            raise uet.BadInputException(
               "EdgeReq.sg_path should select a path between its two ends",
               "Last NF (%s) of EdgeReq.sg_path and destination of EdgeReq ("
               "%s) are not the same!" % (reqlink.dst.node.id, req.dst.node.id))
          nf_chain.append(reqlink.dst.node.id)
        # validate EdgeReq ends.
        if reqlinkid == req.sg_path[0] and \
              reqlink.src.node.id != req.src.node.id:
          raise uet.BadInputException(
             "EdgeReq.sg_path should select a path between its two ends",
             "First NF (%s) of EdgeReq.sg_path and source of EdgeReq (%s) are "
             "not the same!" % (reqlink.src.node.id, req.src.node.id))
        chain['chain'] = nf_chain
      cid += 1
      chainlist.append(chain)

  # if some resource value is not set (is None) then be permissive and set it
  # to a comportable value.
  for respar in ('cpu', 'mem', 'storage', 'delay', 'bandwidth'):
    for n in network.infras:
      if n.resources[respar] is None:
        if respar == 'delay':
          helper.log.warn("Resource parameter %s is not given in %s, "
                          "substituting with 0!"%(respar, n.id))
          n.resources[respar] = 0
        else:
          helper.log.warn("Resource parameter %s is not given in %s, "
                          "substituting with infinity!"%(respar, n.id))
          n.resources[respar] = float("inf")
  # If link res is None or doesn't exist, replace it with a neutral value.
  for i, j, d in network.network.edges_iter(data=True):
    if d.type == 'STATIC':
      if getattr(d, 'delay', None) is None:
        if d.src.node.type != 'SAP' and d.dst.node.type != 'SAP':
          helper.log.warn("Resource parameter delay is not given in link %s "
                          "substituting with zero!"%d.id)
        setattr(d, 'delay', 0)
      if getattr(d, 'bandwidth', None) is None:
        if d.src.node.type != 'SAP' and d.dst.node.type != 'SAP':
          helper.log.warn("Resource parameter bandwidth is not given in link %s "
                          "substituting with infinity!"%d.id)
        setattr(d, 'bandwidth', float("inf"))

  # create the class of the algorithm
  alg = CoreAlgorithm(network, request, chainlist, full_remap,
                      enable_shortest_path_cache, overall_highest_delay,
                      bw_factor=bw_factor, res_factor=res_factor,
                      lat_factor=lat_factor, shortest_paths=shortest_paths)
  alg.setBacktrackParameters(bt_limit, bt_branching_factor)
  mappedNFFG = alg.start()

  # replace Infinity values
  _purgeNFFGFromInfinityValues(mappedNFFG)
  # print mappedNFFG.dump()
  # The printed format is vnfs: (vnf_id, node_id) and links: MultiDiGraph, edge
  # data is the paths (with link ID-s) where the request links are mapped.
  helper.log.info("The VNF mappings are (vnf_id, node_id): \n%s" % pformat(
     alg.manager.vnf_mapping))
  helper.log.debug("The link mappings are: \n%s" % pformat(
     alg.manager.link_mapping.edges(data=True, keys=True)))

  if return_dist:
    return mappedNFFG, alg.preprocessor.shortest_paths
  else:
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
  # flowclass default: None, meaning: match all traffic
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
  nffg.add_undirected_link(infra1.add_port(2), nf1.add_port(3), dynamic=True)
  nffg.add_undirected_link(infra2.add_port(0), nf2.add_port(4), dynamic=True)
  nffg.add_undirected_link(infra2.add_port(1), nf3.add_port(2), dynamic=True)
  nffg.add_undirected_link(infra1.add_port(3), infra2.add_port(2),
                           bandwidth=31241242)

  return nffg


def _onlySAPsRequest ():
  nffg = NFFG(id="BME-req-001")
  sap1 = nffg.add_sap(name="SAP1", id="sap1")
  sap2 = nffg.add_sap(name="SAP2", id="sap2")

  nffg.add_sglink(sap1.add_port(0), sap2.add_port(0))
  # nffg.add_sglink(sap1.add_port(1), sap2.add_port(1))

  nffg.add_req(sap1.ports[0], sap2.ports[0], bandwidth=1000, delay=24)
  nffg.add_req(sap1.ports[0], sap2.ports[0], bandwidth=1000, delay=24)

  return nffg


def _constructExampleNetwork ():
  nffg = NFFG(id="BME-net-001")
  uniformnoderes = {'cpu': 5, 'mem': 5, 'storage': 5, 'delay': 0.9,
                    'bandwidth': 5500}
  infra0 = nffg.add_infra(id="node0", name="INFRA0", **uniformnoderes)
  uniformnoderes['cpu'] = None
  infra1 = nffg.add_infra(id="node1", name="INFRA1", **uniformnoderes)
  uniformnoderes['mem'] = None
  infra2 = nffg.add_infra(id="node2", name="INFRA2", **uniformnoderes)
  uniformnoderes['storage'] = None
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
  unilinkres['bandwidth'] = None
  nffg.add_undirected_link(infra0.add_port(1), infra2.add_port(0), **unilinkres)
  nffg.add_undirected_link(infra1.add_port(2), infra2.add_port(1), **unilinkres)
  unilinkres['delay'] = 0.2
  unilinkres['bandwidth'] = 5000
  nffg.add_undirected_link(switch.add_port(0), infra0.add_port(3), **unilinkres)
  unilinkres['delay'] = None
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


def _testNetworkForBacktrack ():
  nffg = NFFG(id="backtracktest", name="backtrack")
  sap1 = nffg.add_sap(name="SAP1", id="sap1")
  sap2 = nffg.add_sap(name="SAP2", id="sap2")

  uniformnoderes = {'cpu': 5, 'mem': 5, 'storage': 5, 'delay': 0.4,
                    'bandwidth': 5500}
  infra0 = nffg.add_infra(id="node0", name="INFRA0", **uniformnoderes)
  uniformnoderes2 = {'cpu': 9, 'mem': 9, 'storage': 9, 'delay': 0.4,
                     'bandwidth': 5500}
  infra1 = nffg.add_infra(id="node1", name="INFRA1", **uniformnoderes2)
  swres = {'cpu': 0, 'mem': 0, 'storage': 0, 'delay': 0.0,
           'bandwidth': 10000}
  sw = nffg.add_infra(id="sw", name="sw1", **swres)

  infra0.add_supported_type(['A'])
  infra1.add_supported_type(['A'])

  unilinkres = {'delay': 0.0, 'bandwidth': 2000}
  nffg.add_undirected_link(sap1.add_port(0), infra0.add_port(0),
                           **unilinkres)
  nffg.add_undirected_link(sap2.add_port(0), infra1.add_port(0),
                           **unilinkres)
  rightlink = {'delay': 10.0, 'bandwidth': 2000}
  leftlink = {'delay': 0.01, 'bandwidth': 5000}
  nffg.add_link(infra0.add_port(1), sw.add_port(0), id="n0sw", **rightlink)
  nffg.add_link(sw.add_port(1), infra1.add_port(1), id="swn1", **rightlink)
  nffg.add_link(sw.ports[0], infra0.ports[1], id="swn0", **leftlink)
  nffg.add_link(infra1.ports[1], sw.ports[1], id="n1sw", **leftlink)

  return nffg


def _testRequestForBacktrack ():
  nffg = NFFG(id="backtracktest-req", name="btreq")
  sap1 = nffg.add_sap(name="SAP1", id="sap1req")
  sap2 = nffg.add_sap(name="SAP2", id="sap2req")

  a = nffg.add_nf(id="a", name="NetFunc0", func_type='A', cpu=3, mem=3,
                  storage=3)
  b = nffg.add_nf(id="b", name="NetFunc1", func_type='A', cpu=3, mem=3,
                  storage=3)
  c = nffg.add_nf(id="c", name="NetFunc2", func_type='A', cpu=3, mem=3,
                  storage=3)

  nffg.add_sglink(sap1.add_port(0), a.add_port(0), id="sa")
  nffg.add_sglink(a.add_port(1), b.add_port(0), id="ab")
  nffg.add_sglink(b.add_port(1), c.add_port(0), id="bc")
  nffg.add_sglink(c.add_port(1), sap2.add_port(0), id="cs")

  nffg.add_req(a.ports[0], b.ports[1], delay=1.0, sg_path=["ab"])
  nffg.add_req(b.ports[0], c.ports[1], delay=1.0, sg_path=["bc"])
  nffg.add_req(c.ports[0], sap2.ports[0], delay=1.0, sg_path=["cs"])
  nffg.add_req(sap1.ports[0], sap2.ports[0], delay=50, bandwidth=10,
               sg_path=["sa", "ab", "bc", "cs"])

  return nffg


if __name__ == '__main__':
  try:
    # req = _constructExampleRequest()
    # net = _constructExampleNetwork()

    # req = _example_request_for_fallback()
    # print req.dump()
    # req = _onlySAPsRequest()
    # print net.dump()
    # req = _testRequestForBacktrack()
    # net = _testNetworkForBacktrack()
    with open('../examples/escape-mn-req.nffg', "r") as f:
      req = NFFG.parse(f.read())
    with open('../examples/escape-mn-topo.nffg', "r") as g:
      net = NFFG.parse(g.read())
      net.duplicate_static_links()
    mapped = MAP(req, net, full_remap=False)
    print mapped.dump()
  except uet.UnifyException as ue:
    print ue, ue.msg
    print traceback.format_exc()
