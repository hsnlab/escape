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

import sys, logging
import UnifyExceptionTypes as uet
import networkx as nx

from Alg1_Core import CoreAlgorithm
try:
  from escape.nffg_lib.nffg import NFFG, NFFGToolBox
except ImportError:
  import sys, os
  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                  "../escape/escape/nffg_lib/")))
  from nffg import NFFG, NFFGToolBox

from MIPBaseline import Scenario, ModelCreator, isFeasibleStatus, \
  convert_req_to_request, convert_nffg_to_substrate

import MappingAlgorithms

log = logging.getLogger("MIP-NFFG-conv")
logging.basicConfig(format='%(levelname)s:%(name)s:%(message)s')
log.setLevel(logging.DEBUG)

def get_MIP_solution (reqnffgs, netnffg):
  """
  Executes the MIP mapping for the input requests and network NFFGs.
  Returns the mapped structure and the references to the mapped requests.
  """
  request_seq = []
  for req in reqnffgs:
    request = convert_req_to_request(req)
    request_seq.append(request)

  substrate = convert_nffg_to_substrate(netnffg)

  scen = Scenario(substrate, request_seq)
  mc = ModelCreator(scen)
  mc.init_model_creator()
  if isFeasibleStatus(mc.run_milp()):
    solution = mc.solution
    solution.validate_solution(debug_output=False)
    
    return solution.mapping_of_request
  

def get_edge_id (g, srcid, srcpid, dstpid, dstid):
  """
  Retrieves the edge ID from NFFG of an arbitrary link between two ports.
  (There should only be one link.)
  """
  """Retrieve objects.
  src = nffg.network.node[src]
  dst = nffg.network.node[dst]
  srcp = src.ports[srcpid]
  dstp = dst.ports[dstpid]
  """
  for i,j,k,d in g.edges_iter(data=True, keys=True):
    if i == srcid and j == dstid and d.src.id == srcpid and d.dst.id == dstpid:
      return k

def convert_mip_solution_to_nffg (reqs, net, file_inputs=False, 
                                  full_remap=False):
  if file_inputs:
    request_seq = []
    for reqfile in reqs:
      with open(reqfile, "r") as f:
        req = NFFG.parse(f.read())
        request_seq.append(req)

    with open(net, "r") as g:
      net = NFFG.parse(g.read())
  else:
    request_seq = reqs
      
  # all input NFFG-s are obtained somehow
 

  ######################################################################
  ##### This is taken from the MappingAlgorithms.MAP() function ####
  ######################################################################
  
  request = request_seq[0]
  
  # batch together all nffgs
  for r in request_seq[1:]:
    request = NFFGToolBox.merge_nffgs (request, r)
  
  chainlist = []
  cid = 1
  edgereqlist = []
  for req in request.reqs:
    edgereqlist.append(req)
    request.del_edge(req.src, req.dst, req.id)

  # construct chains from EdgeReqs
  for req in edgereqlist:

    if len(req.sg_path) == 1:
      # then add it as linklocal req instead of E2E req
      log.info("Interpreting one SGHop long EdgeReq (id: %s) as link "
                      "requirement on SGHop: %s."%(req.id, req.sg_path[0]))
      reqlink = None
      for sg_link in request.sg_hops:
        if sg_link.id == req.sg_path[0]:
          reqlink = sg_link
          break
      if reqlink is None:
        log.warn("EdgeSGLink object not found for EdgeSGLink ID %s! "
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
                 'delay': req.delay if req.delay is not None else float("inf")}
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
    for n in net.infras:
      if n.resources[respar] is None:
        if respar == 'delay':
          log.warn("Resource parameter %s is not given in %s, "
                          "substituting with 0!"%(respar, n.id))
          n.resources[respar] = 0
        else:
          log.warn("Resource parameter %s is not given in %s, "
                          "substituting with infinity!"%(respar, n.id))
          n.resources[respar] = float("inf")
  # If link res is None or doesn't exist, replace it with a neutral value.
  for i, j, d in net.network.edges_iter(data=True):
    if d.type == 'STATIC':
      if getattr(d, 'delay', None) is None:
        if d.src.node.type != 'SAP' and d.dst.node.type != 'SAP':
          log.warn("Resource parameter delay is not given in link %s "
                          "substituting with zero!"%d.id)
        setattr(d, 'delay', 0)
      if getattr(d, 'bandwidth', None) is None:
        if d.src.node.type != 'SAP' and d.dst.node.type != 'SAP':
          log.warn("Resource parameter bandwidth is not given in link %s "
                          "substituting with infinity!"%d.id)
        setattr(d, 'bandwidth', float("inf"))

  # create the class of the algorithm
  # unnecessary preprocessing is executed
  ############################################################################
  # HACK: We only want to use the algorithm class to generate an NFFG, we will 
  # fill the mapping struct with the one found by MIP
  alg = CoreAlgorithm(net, request, chainlist, full_remap, False)

  # move 'availres' and 'availbandwidth' values of the network to maxres, 
  # because the MIP solution takes them as availabel resource.
  net = alg.bare_infrastucture_nffg
  for n in net.infras:
    n.resources = n.availres
  for d in net.links:
    # there shouldn't be any Dynamic links by now.
    d.bandwidth = d.availbandwidth
  
  mapping_of_reqs = get_MIP_solution(request_seq, net)

  mappedNFFG = NFFG(id="MILP-mapped")
  for transformed_req in mapping_of_reqs:
    if mapping_of_reqs[transformed_req].is_embedded:
      alg.manager.vnf_mapping = []
      alg.manager.link_mapping = nx.MultiDiGraph()
      for n, vlist in mapping_of_reqs[transformed_req].\
          snode_to_hosted_vnodes.items():
        for v in vlist:
          alg.manager.vnf_mapping.append((v, n))
      trans_link_mapping = mapping_of_reqs[transformed_req].vedge_to_spath
      for trans_sghop in trans_link_mapping:
        vnf1 = trans_sghop[0]
        vnf2 = trans_sghop[3]
        reqlid = get_edge_id(alg.req, vnf1, trans_sghop[1], 
                             trans_sghop[2], vnf2)
        mapped_path = []
        path_link_ids = []
        for trans_link in trans_link_mapping[trans_sghop]:
          n1 = trans_link[0]
          n2 = trans_link[3]
          lid = get_edge_id(alg.net, n1, trans_link[1], trans_link[2], n2)
          mapped_path.append(n1)
          path_link_ids.append(lid)
        if len(trans_link_mapping[trans_sghop]) == 0:
          mapped_path.append(alg.manager.getIdOfChainEnd_fromNetwork(vnf1))
        else:
          mapped_path.append(n2)

        alg.manager.link_mapping.add_edge(vnf1, vnf2, key=reqlid, 
                                          mapped_to=mapped_path, 
                                          path_link_ids=path_link_ids)
    
      oneNFFG = alg.constructOutputNFFG()
      mappedNFFG = NFFGToolBox.merge_nffgs(mappedNFFG, oneNFFG)
    else:
      print "MILP didn't produce a mapping for request %s"%transformed_req
      return None

  # replace Infinity values
  MappingAlgorithms._purgeNFFGFromInfinityValues(mappedNFFG)

  # print mappedNFFG.dump()
  return mappedNFFG

if __name__ == '__main__':
  convert_mip_solution_to_nffg(['untracked/e2e-req-erronous.nffg'], 
                               'untracked/mip_mapped-escape-mn-topo.nffg', 
                               file_inputs=True)
