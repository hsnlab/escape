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
Core functions and classes of Algorithm1.
"""

import sys
import copy

import networkx as nx

import GraphPreprocessor
import UnifyExceptionTypes as uet
import Alg1_Helper as helper

try:
  from escape.util.nffg import NFFG, generate_dynamic_fallback_nffg
except ImportError:
  import os

  sys.path.append(os.path.abspath(os.path.dirname(__file__) + "../pox/ext/"))


class CoreAlgorithm(object):
  def __init__ (self, net0, req0, chains0):
    self.log = helper.log.getChild(self.__class__.__name__)

    self.log.info("Initializing algorithm variables")
    # only needed to get SAP`s name by its ID and for reset()
    self.req0 = copy.deepcopy(req0)

    # needed for reset()
    self.net0 = copy.deepcopy(net0)

    self.original_chains = chains0
    self._preproc(net0, req0, chains0)

    # must be sorted in alphabetic order of keys: cpu, mem, storage
    self.resource_priorities = [0.3333, 0.3333, 0.3333]

    # which should count more in the objective function
    self.bw_factor = 1
    self.res_factor = 1
    self.lat_factor = 1

    ''' The new preference parameters are f(x) == 0 if x<c and f(1) == e,
    exponential in between.
    The bandwidth parameter refers to the average link utilization
    on the paths to the nodes (and also collocated request links).
    If  the even the agv is high it is much worse!'''
    self.pref_params = dict(cpu=dict(c=0.4, e=2.5), mem=dict(c=0.4, e=2.5),
                            storage=dict(c=0.4, e=2.5),
                            bandwidth=dict(c=0.1, e=10.0))

    # The networkx graphs from the NFFG should be enough for the core
    # unwrap them, to save one indirection after the preprocessor has
    # finished.
    self.net = self.net.network
    self.req = self.req.network

  def _preproc (self, net0, req0, chains0):
    self.log.info("Preprocessing:")

    self.manager = helper.MappingManager(net0, req0, chains0)

    self.preprocessor = GraphPreprocessor.GraphPreprocessorClass(net0, req0,
                                                                 chains0,
                                                                 self.manager)
    self.net = self.preprocessor.processNetwork()
    self.req, self.chains_with_subgraphs = self.preprocessor.processRequest(
      self.net)

  def _checkBandwidthUtilOnHost (self, i, bw_req):
    """
    Checks if a host can satisfy the bandwidth requirement, returns its
    utilization if yes, or 0 if it is a SAP, -1 if it can`t satisfy.
    """
    if self.net.node[i].type != 'SAP':
      # if first element is a NodeInfra, then traffic also needs
      # to be steered out from the previously mapped VNF.
      if self.net.node[i].availres['bandwidth'] < bw_req:
        self.log.debug(
          "Host %s has only %f Mbps capacity but %f is required." % (
            i, self.net.node[i].availres['bandwidth'], bw_req))
        return -1, None
      else:
        util_of_host = float(self.net.node[i].resources['bandwidth'] - (
          self.net.node[i].availres['bandwidth'] - bw_req)) / \
                       self.net.node[i].resources['bandwidth']
        return 0, util_of_host
    else:
      return 1, 0

  def _calculateAvgLinkUtil (self, path_to_map, linkids, bw_req, vnf_id=None):
    """Checks if the path can satisfy the bandwidth requirement.
    Returns the average link utilization on the path if
    that path is feasible with bw_req, -1 otherwise.
    If vnf_id is None, then the path`s end is already mapped."""
    sum_w = 0
    internal_bw_req = 0
    sap_count_on_path = 0
    if vnf_id is not None:
      if self.req.node[vnf_id].resources['bandwidth'] is not None:
        internal_bw_req = self.req.node[vnf_id].resources['bandwidth']
        avail_bw = self.net.node[path_to_map[-1]].availres[
                     'bandwidth'] - internal_bw_req
        if avail_bw < 0:
          # Do not include VNF-internal bw req into link util calc.
          return -1

    if len(path_to_map) > 1:
      for i, j, k in zip(path_to_map[:-1], path_to_map[1:], linkids):
        if self.net[i][j][k].availbandwidth < bw_req:
          self.log.debug(
            "Link %s, %s has only %f Mbps capacity, but %f is required." % (
              i, j, self.net[i][j][k].availbandwidth, bw_req))
          return -1
        else:
          sum_w += float(self.net[i][j][k].bandwidth - (
            self.net[i][j][k].availbandwidth - bw_req)) / self.net[i][j][
                     k].bandwidth
        # either only steers the traffic through a host or at the
        # beginning of the path, steers out from the VNF
        is_it_sap, util = self._checkBandwidthUtilOnHost(i, bw_req)
        if is_it_sap >= 0:
          sap_count_on_path += is_it_sap
          sum_w += util
        else:
          return -1

      # The last node of the path should also be considered:
      #  - it is a SAP or
      #  - the traffic is steered into the to-be-mapped VNF
      is_it_sap, util = self._checkBandwidthUtilOnHost(path_to_map[-1], bw_req)
      if is_it_sap >= 0:
        sap_count_on_path += is_it_sap
        sum_w += util
      else:
        return -1
      sum_w /= (len(path_to_map) - 1) + (len(path_to_map) - sap_count_on_path)

    elif len(path_to_map) == 0:
      self.log.warn(
        "Tried to calculate average link utilization on 0 length path!")
      return -1

    else:
      # required when trying to collocate two ends of a link.
      act_bw = self.net.node[path_to_map[0]].availres['bandwidth']
      max_bw = self.net.node[path_to_map[0]].resources['bandwidth']
      # sum of the two bw reqs are subtracted from guaranteed bw between
      # all (static and dynamic) ports of the host (BiS-BiS)
      sum_w = float(max_bw - (act_bw - bw_req - internal_bw_req)) / max_bw
      if act_bw < bw_req + internal_bw_req:
        self.log.info(
          "Node %s don`t have %f Mbps capacity for mapping a link." % (
            path_to_map[0], bw_req))
        return -1
        # path has only one element, so sum_w is already average.

    # Utilization of host-internal bandwidths are also included.
    return sum_w

  def _sumLatencyOnPath (self, path_to_map, linkids):
    """Summarizes all latency (link, and forwarding) on the path.
    prev_vnf_id is the already mapped and vnf_id is the to-be-placed
    VNF in the greedy process.
    Latency requirement satisfaction should be checked outside of this
    function, should be done by the helper functions of MappingManager.
    """
    sum_lat = 0
    try:

      if len(path_to_map) > 1:
        # routing the traffic from the previously used host to its
        # outbound port takes time too.(host`s lat is between all ports)
        if self.net.node[path_to_map[0]].type != 'SAP':
          sum_lat += self.net.node[path_to_map[0]].resources['delay']

        for i, j, k in zip(path_to_map[:-1], path_to_map[1:], linkids):
          sum_lat += self.net[i][j][k].delay
          if self.net.node[j].type != 'SAP':
            sum_lat += self.net.node[j].resources['delay']

      elif len(path_to_map) == 1:
        # In this case, collocation is about to happen
        # if there is VNF internal requirement, that should be forwarded
        # to the lower orchestration layer.
        # But forwarding from the previous VNF to the collocated one
        # takes latency between a pair of dynamic ports
        sum_lat = self.net.node[path_to_map[0]].resources['delay']

      else:
        self.log.warn("Tried to check latency sum on 0 length path!")
        return -1

    except KeyError as e:
      raise uet.BadInputException(" node/edge data: %s data not found." % e)
    return sum_lat

  def _preferenceValueOfUtilization (self, x, attr):
    c = self.pref_params[attr]['c']
    e = self.pref_params[attr]['e']
    if x < c:
      return 0.0
    else:
      return (e + 1) ** float((x - c) / (1 - c)) - 1

  def _objectiveFunction (self, cid, node_id, prev_vnf_id, vnf_id, reqlinkid,
       path_to_map, linkids):
    """Calculates a function to determine which node is better to map to,
    returns -1, if not feasible"""
    requested = self.req.node[vnf_id].resources
    available = self.net.node[node_id].availres
    maxres = self.net.node[node_id].resources
    bw_req = self.req[prev_vnf_id][vnf_id][reqlinkid].bandwidth
    sum_res = 0

    if len(path_to_map) == 0:
      raise uet.InternalAlgorithmException(
        "No path given to host %s for preference value calculation!" % node_id)

    if available['mem'] >= requested['mem'] and available['cpu'] >= requested[
      'cpu'] and available['storage'] >= requested['storage']:
      avg_link_util = self._calculateAvgLinkUtil(path_to_map, linkids, bw_req,
                                                 vnf_id)
      if avg_link_util == -1:
        return -1, sys.float_info.max
      sum_latency = self._sumLatencyOnPath(path_to_map, linkids)
      local_latreq = self.manager.getLocalAllowedLatency(cid, prev_vnf_id,
                                                         vnf_id, reqlinkid)
      if sum_latency == -1 or sum_latency > local_latreq or not \
           self.manager.isVNFMappingDistanceGood(
        prev_vnf_id, vnf_id, path_to_map[0], path_to_map[-1]):
        return -1, sys.float_info.max

      '''Here we know that node_id have enough resource and the path
      leading there satisfies the bandwidth req of the potentially
      mapped edge of req graph. And the latency requirements as well'''
      max_rescomponent_value = 0
      for attr, res_w in zip(['cpu', 'mem', 'storage'],
                             self.resource_priorities):
        sum_res += res_w * self._preferenceValueOfUtilization(
          float(maxres[attr] - (available[attr] - requested[attr])) / maxres[
            attr], attr)
        max_rescomponent_value += self.pref_params[attr]['e'] * res_w

      # Scale them to the same interval
      scaled_res_comp = 10 * float(sum_res) / max_rescomponent_value
      scaled_bw_comp = 10 * float(
        self._preferenceValueOfUtilization(avg_link_util, 'bandwidth')) / \
                       self.pref_params['bandwidth']['e']
      scaled_lat_comp = 10 * float(sum_latency) / local_latreq

      self.log.debug("avglinkutil pref value: %f, sum res: %f, sumlat: %f" % (
        self.bw_factor * scaled_bw_comp, self.res_factor * scaled_res_comp,
        self.lat_factor * scaled_lat_comp))

      return self.bw_factor * scaled_bw_comp + self.res_factor * \
             scaled_res_comp + self.lat_factor * scaled_lat_comp, sum_latency
    else:
      return -1, sys.float_info.max

  def _updateGraphResources (self, bw_req, path, linkids, vnf=None, node=None):
    """Subtracts the required resources by the (vnf, node) mapping
    and path with bw_req from the available resources of the
    substrate network. vnf and node variables should be given, if those are
    just mapped now. (not when we want to map only a path between two already
    mapped VNFs)
    NOTE1: the ending of `path` is `node`.
    NOTE2: feasibility is already checked by _objectiveFunction()"""
    if vnf is not None and node is not None:
      if self.net.node[node].type != 'INFRA':
        raise uet.InternalAlgorithmException(
          "updateGraphResources should only be called on Infra nodes!")
      newres = helper.subtractNodeRes(self.net.node[node].availres,
                                      self.req.node[vnf].resources)
      if newres is None:
        raise uet.InternalAlgorithmException(
          "During network resource update, Infra node %s`s resources "
          "shouldn`t got below zero!" % self.net.node[node].id)
      else:
        self.net.node[node].availres = newres

    if len(path) == 0:
      self.log.warn("Updating resources with 0 length path!")
    elif len(path) > 0:
      # collocation or 1st element of path needs to be updated.
      if self.net.node[path[0]].type != 'SAP':
        self.net.node[path[0]].availres['bandwidth'] -= bw_req
        new_bw = self.net.node[path[0]].availres['bandwidth']
        if new_bw <= 0:
          self.net.node[
            path[0]].weight = sys.float_info.max  # maybe use float("inf")?
        else:
          self.net.node[path[0]].weight = 1.0 / new_bw
      if len(path) > 1:
        for i, j, k in zip(path[:-1], path[1:], linkids):
          self.net[i][j][k].availbandwidth -= bw_req
          new_bw = self.net[i][j][k].availbandwidth
          if new_bw <= 0:
            self.net[i][j][k].weight = sys.float_info.max
          else:
            self.net[i][j][k].weight = 1.0 / new_bw
          # update node bandwidth resources on the path
          if self.net.node[j].type != 'SAP':
            self.net.node[j].availres['bandwidth'] -= bw_req
            new_bw_innode = self.net.node[j].availres['bandwidth']
            if new_bw_innode <= 0:
              self.net.node[j].weight = sys.float_info.max
            else:
              self.net.node[j].weight = 1.0 / new_bw_innode
    self.log.debug("Available network resources are updated.")

  def _mapOneVNF (self, cid, subgraph, start, prev_vnf_id, vnf_id, reqlinkid):
    """Starting from the node (start), where the previous vnf of the chain
    was mapped, maps vnf_id to an appropriate node."""
    best_node = (-1, sys.float_info.max, -1)

    '''Edge data must be used from the substrate network!
    NOTE(loops): shortest path from i to i is [i] (This path is the
    collocation, and 1 long paths are handled right by the
    _objectiveFunction()/_calculateAvgLinkUtil()/_sumLat() functions)'''
    # TODO: Write an utility func, which gives path based on lat AND bw
    paths, linkids = helper.shortestPathsBasedOnEdgeWeight(subgraph, start)
    for map_target in paths:
      if self.net.node[map_target].type == 'INFRA' and self.net.node[
        map_target].supported is not None:
        if self.req.node[vnf_id].functional_type in self.net.node[
          map_target].supported:

          place_crit = self.req.node[vnf_id].placement_criteria
          if len(place_crit) > 0 and map_target not in place_crit:
            continue
          else:
            value, used_lat = self._objectiveFunction(cid, map_target,
                                                      prev_vnf_id, vnf_id,
                                                      reqlinkid,
                                                      paths[map_target],
                                                      linkids[map_target])
            if -1 < value < best_node[1]:
              best_node = (map_target, value, used_lat)
              self.log.debug("Calculated value: %f for VNF %s and path: %s" % (
                value, vnf_id, paths[map_target]))

    if best_node[0] > -1:
      self.log.debug(
        "Mapped VNF %s to node %s in network." % (vnf_id, best_node[0]))
      self.manager.vnf_mapping.append((vnf_id, best_node[0]))
      self.log.debug("Request Link %s, %s, %s mapped to path: %s" % (
        prev_vnf_id, vnf_id, reqlinkid, paths[best_node[0]]))
      self.manager.link_mapping.add_edge(prev_vnf_id, vnf_id, key=reqlinkid,
                                         mapped_to=paths[best_node[0]],
                                         path_link_ids=linkids[best_node[0]])
      self._updateGraphResources(
        self.req[prev_vnf_id][vnf_id][reqlinkid]['bandwidth'],
        paths[best_node[0]], linkids[best_node[0]], vnf_id, best_node[0])
      self.manager.updateChainLatencyInfo(cid, best_node[2], best_node[0])
      return best_node[0]
    else:
      self.log.error("Couldn`t map VNF %s anywhere!" % vnf_id)
      raise uet.MappingException("Couldn`t map VNF %s anywhere!" % vnf_id)

  def _mapOneRequestLink (self, cid, g, vnf1, vnf2, reqlinkid):
    """
    Maps a request link, when both ends are already mapped.
    Uses the weighted shortest path.
    TODO: Replace dijkstra with something more sophisticated.
    """
    n1 = self.manager.getIdOfChainEnd_fromNetwork(vnf1)
    n2 = self.manager.getIdOfChainEnd_fromNetwork(vnf2)
    if n1 <= 0 or n2 <= 0:
      self.log.error("Not both end of request link are mapped: %s, %s, %s" % (
        vnf1, vnf2, reqlinkid))
      raise uet.InternalAlgorithmException(
        "Not both end of request link are mapped: %s, %s" % (vnf1, vnf2))
    bw_req = self.req[vnf1][vnf2][reqlinkid].bandwidth

    try:
      path, linkids = helper.shortestPathsBasedOnEdgeWeight(g, n1, target=n2)
      path = path[n2]
      linkids = linkids[n2]
    except (nx.NetworkXNoPath, KeyError) as e:
      raise uet.MappingException(
        "No path found between substrate nodes: %s and %s for mapping a "
        "request link between %s and %s" % (n1, n2, vnf1, vnf2))

    if self._calculateAvgLinkUtil(path, linkids, bw_req) == -1:
      self.log.error(
        "Last link of chain or best-effort link %s, %s couldn`t be mapped!" % (
          vnf1, vnf2))
      raise uet.MappingException(
        "Last link of chain or best-effort link %s, %s, %s couldn`t be mapped "
        "due to link capacity" % (vnf1, vnf2, reqlinkid))
    elif self.manager.getLocalAllowedLatency(cid, vnf1, vnf2,
                                             reqlinkid) < \
         self._sumLatencyOnPath(
         path, linkids):
      raise uet.MappingException(
        "Last link %s, %s, %s of chain couldn`t be mapped due to latency "
        "requirement." % (vnf1, vnf2, reqlinkid))
    self.log.debug(
      "Last link of chain or best-effort link %s, %s " % (vnf1, vnf2))
    self.log.debug(" was mapped to path: %s" % path)
    self._updateGraphResources(bw_req, path, linkids)
    self.manager.link_mapping.add_edge(vnf1, vnf2, key=reqlinkid,
                                       mapped_to=path, path_link_ids=linkids)

  def _addSAPandLinkToFromIt (self, netportid, bis_id, nffg, nodenf, reqportid,
       fc, toSAP=True):
    """
    Checks if there is a SAP for this portid in the currently
    under-construction NFFG. Adds the link to/from this SAP.
    """
    sapname_and_id = "%s-%s" % (bis_id, netportid)
    if sapname_and_id not in nffg.network:
      sap = nffg.add_sap(name=sapname_and_id, id=sapname_and_id)
    else:
      sap = nffg.network.node[sapname_and_id]
      # The VNFs port should be called the same as before,
      # SAP port id is not important.
    if toSAP:
      nffg.add_sglink(nodenf.ports[reqportid], sap.add_port(), flowclass=fc)
    else:
      nffg.add_sglink(sap.add_port(), nodenf.ports[reqportid], flowclass=fc)

  def _addFlowrulesToNFFGDerivatedFromReqLinks (self, v1, v2, reqlid, nffg):
    """
    Adds the flow rules of the path of the request link (v1,v2,reqlid)
    to the ports of the Infras.
    The required Port objects are stored in 'infra_ports' field of
    manager.link_mapping edges. Flowrules must be installed to the 'nffg's
    Ports, NOT self.net!! (Port id-s can be taken from self.net as well)
    Flowrule format is:
      match: in_port=<<Infraport id>>;flowclass=<<Flowclass of SGLink if
                     there is one>>;TAG=<<Neighboring VNF ids and linkid>>
      action: output=<<outbound port id>>;TAG=<<Neighboring VNF ids and
      linkid>>/UNTAG
    WARNING: If multiple SGHops starting from a SAP are mapped to paths whose 
    first infrastructure link is common, starting from the same SAP, the first
    Infra node can only identify which packet belongs to which SGHop based on 
    the FLOWCLASS field, which is considered optional.
    """
    helperlink = self.manager.link_mapping[v1][v2][reqlid]
    path = helperlink['mapped_to']
    linkids = helperlink['path_link_ids']
    flowsrc = helperlink['infra_ports'][0]
    flowdst = helperlink['infra_ports'][1]
    reqlink = self.req[v1][v2][reqlid]
    # The action and match are the same format
    tag = "TAG=%s-%s-%s" % (v1, v2, reqlid)
    if len(path) == 1:
      # collocation happened, none of helperlink`s port refs should be None
      # TAG the traffic and UNTAG it in the destination port
      match_str = "in_port="
      action_str = "output="
      if flowdst is None or flowsrc is None:
        raise uet.InternalAlgorithmException(
          "No InfraPort found for a dynamic link of collocated VNFs")
      match_str += flowsrc.id
      if reqlink.flowclass is not None:
        match_str += ";flowclass=%s" % reqlink.flowclass
      self.log.debug("Collocated flowrule %s => %s added to Port %s of %s" % (
        match_str, action_str, flowsrc.id, path[0]))
      flowsrc.add_flowrule(match_str, action_str)
    else:
      # set the flowrules for the transit Infra nodes
      for i, j, k, lidij, lidjk in zip(path[:-2], path[1:-1], path[2:],
                                       linkids[:-1], linkids[1:]):
        match_str = "in_port="
        action_str = "output="
        match_str += self.net[i][j][lidij].dst.id
        if reqlink.flowclass is not None:
          match_str += ";flowclass=%s" % reqlink.flowclass
        action_str += self.net[j][k][lidjk].src.id
        # Transit SAPs would mess it up pretty much, but it is not allowed.
        if self.net.node[i].type == 'SAP':
          action_str += ";" + tag
        else:
          match_str += ";" + tag
        if self.net.node[k].type == 'SAP':
          # remove TAG in the last port where flowrules are stored 
          # if the next node is a SAP
          # NOTE: If i and k are SAPs but j isn`t, then in j`s port TAG and 
          # UNTAG action will be present at the same time.
          action_str += ";UNTAG"
        self.log.debug("Transit flowrule %s => %s added to Port %s of %s" % (
          match_str, action_str, self.net[i][j][lidij].dst.id, j))
        nffg.network[i][j][lidij].dst.add_flowrule(match_str, action_str)

      # set flowrule for the first element if that is not a SAP
      if nffg.network.node[path[0]].type != 'SAP':
        match_str = "in_port="
        action_str = "output="
        if flowsrc is None:
          raise uet.InternalAlgorithmException(
            "No InfraPort found for a dynamic link which starts a path")
        match_str += flowsrc.id
        if reqlink.flowclass is not None:
          match_str += ";flowclass=%s" % reqlink.flowclass
        action_str += nffg.network[path[0]][path[1]][linkids[0]].src.id
        action_str += ";" + tag
        self.log.debug("Starting flowrule %s => %s added to Port %s of %s" % (
          match_str, action_str, flowsrc.id, path[0]))
        flowsrc.add_flowrule(match_str, action_str)

      # set flowrule for the last element if that is not a SAP
      if nffg.network.node[path[-1]].type != 'SAP':
        match_str = "in_port="
        action_str = "output="
        match_str += self.net[path[-2]][path[-1]][linkids[-1]].dst.id
        if reqlink.flowclass is not None:
          match_str += ";flowclass=%s" % reqlink.flowclass
        match_str += ";" + tag
        if flowdst is None:
          raise uet.InternalAlgorithmException(
            "No InfraPort found for a dynamic link which finishes a path")
        action_str += flowdst.id + ";UNTAG"
        self.log.debug("Finishing flowrule %s => %s added to Port %s of %s" % (
          match_str, action_str,
          self.net[path[-2]][path[-1]][linkids[-1]].dst.id, path[-1]))
        nffg.network[path[-2]][path[-1]][linkids[-1]].dst.add_flowrule(
          match_str, action_str)

  def _retrieveOrAddVNF (self, nffg, vnfid):
    if vnfid not in nffg.network:
      nodenf = copy.deepcopy(self.req.node[vnfid])
      nffg.add_node(nodenf)
    else:
      nodenf = nffg.network.node[vnfid]
    return nodenf

  def returnMappedNFFGofOneBiSBiS (self, bis_id):
    """
    Extracts the NFFG object of one BiS-BiS from the mapping found by the
    orchestrator. The returned NFFG should be the input for the lower level
    (inner) orchestration of the BiS-BiS.
    Should be called after the algorithm returned from start().
    NOT READY, SEE TODO
    """
    nffg = NFFG(id="%s-req" % bis_id)
    for vnf, host in self.manager.vnf_mapping:
      if bis_id == host:
        nodenf = self._retrieveOrAddVNF(nffg, vnf)
        for i, j, k, d in self.req.out_edges_iter([vnf], data=True, keys=True):
          # i is always vnf
          path = self.manager.link_mapping[vnf][j][k]['mapped_to']
          linkids = self.manager.link_mapping[vnf][j][k]['path_link_ids']
          if len(path) > 1:
            # add a SAP with the name of the id of this BiS-BiS
            # concatenated the outbound port identifier.
            self._addSAPandLinkToFromIt(
              self.net[path[0]][path[1]][linkids[0]].src.id, bis_id, nffg,
              nodenf, d.src.id, d.flowclass)
          elif len(path) == 1:
            # A collocation happened between vnf and j
            nodenf_next = self._retrieveOrAddVNF(nffg, j)
            nffg.add_sglink(nodenf.ports[d.src.id], nodenf_next.ports[d.dst.id],
                            flowclass=d.flowclass)
          else:
            raise uet.InternalAlgorithmException(
              "No mapping given for a link, after the algorithm has finished "
              "running!")
        # current vnf is already added to nffg
        for i, j, k, d in self.req.in_edges_iter([vnf], data=True, keys=True):
          # j is always vnf, link is i-->vnf directed
          path = self.manager.link_mapping[i][vnf][k]['mapped_to']
          linkids = self.manager.link_mapping[i][vnf][k]['path_link_ids']
          # collocation is handled by the out_edges_iter()
          if len(path) > 1:
            self._addSAPandLinkToFromIt(
              self.net[path[-2]][path[-1]][linkids[-1]].dst.id, bis_id, nffg,
              nodenf, d.dst.id, d.flowclass, toSAP=False)
            # TODO: construct EdgeReqs too, decide how E2E requirements
            # should be
            # divided between sub NFFG-s
            # TODO: Transit INFRA nodes are not handled yet, only those which
            #  has
            # a VNF with incoming or outgoing requestlinks.
    return nffg

  def constructOutputNFFG (self):
    # use the unchanged input from the lower layer (deepcopied in the
    # constructor, modify it now)
    nffg = self.net0
    for vnf, host in self.manager.vnf_mapping:
      # duplicate the object, so the original one is not modified.
      if self.req.node[vnf].type == 'NF':
        mappednodenf = self._retrieveOrAddVNF(nffg, vnf)

        for i, j, k, d in self.req.out_edges_iter([vnf], data=True, keys=True):
          # i is always vnf
          out_infra_port = nffg.network.node[host].add_port()
          # use the (copies of the) ports between the SGLinks to
          # connect the VNF to the Infra node.
          self.log.debug("Port %s added to Infra %s from NF %s" % (
            out_infra_port.id, host, vnf))
          nffg.add_undirected_link(out_infra_port, mappednodenf.ports[d.src.id],
                                   dynamic=True)
          helperlink = self.manager.link_mapping[i][j][k]
          if 'infra_ports' in helperlink:
            helperlink['infra_ports'][0] = out_infra_port
          else:
            helperlink['infra_ports'] = [out_infra_port, None]

        for i, j, k, d in self.req.in_edges_iter([vnf], data=True, keys=True):
          # j is always vnf
          in_infra_port = nffg.network.node[host].add_port()
          self.log.debug("Port %s added to Infra %s to NF %s" % (
            in_infra_port.id, host, vnf))
          nffg.add_undirected_link(in_infra_port, mappednodenf.ports[d.dst.id],
                                   dynamic=True)
          helperlink = self.manager.link_mapping[i][vnf][k]
          if 'infra_ports' in helperlink:
            helperlink['infra_ports'][1] = in_infra_port
          else:
            helperlink['infra_ports'] = [None, in_infra_port]
            # Here a None instead of a port object means that the
            # SGLink`s beginning or ending is a SAP.

    for vnf in self.req.nodes_iter():
      for i, j, k, d in self.req.out_edges_iter([vnf], data=True, keys=True):
        # i is always vnf
        self._addFlowrulesToNFFGDerivatedFromReqLinks(vnf, j, k, nffg)

    # all VNFs are added to the NFFG, so now, req ids are valid in this
    # NFFG instance. Ports for the SG link ends are created here.
    # Add all the SGHops to the NFFG keeping the SGHops` identifiers, so the
    # installed flowrules and TAG-s will be still valid
    for i, j, d in self.req.edges_iter(data=True):
      if self.req.node[i].type == 'SAP':
        # if i is a SAP we have to find what is its ID in the network
        # d.id is the link`s key
        sapstartid = self.manager.getIdOfChainEnd_fromNetwork(i)
        if self.req.node[j].type == 'SAP':
          sapendid = self.manager.getIdOfChainEnd_fromNetwork(j)
          nffg.add_sglink(nffg.network.node[sapstartid].add_port(),
                          nffg.network.node[sapendid].add_port(), id=d.id,
                          flowclass=d.flowclass)
        else:
          nffg.add_sglink(nffg.network.node[sapstartid].add_port(),
                          nffg.network.node[j].add_port(), id=d.id,
                          flowclass=d.flowclass)
      elif self.req.node[j].type == 'SAP':
        sapendid = self.manager.getIdOfChainEnd_fromNetwork(j)
        nffg.add_sglink(nffg.network.node[i].add_port(),
                        nffg.network.node[sapendid].add_port(), id=d.id,
                        flowclass=d.flowclass)
      else:
        nffg.add_sglink(nffg.network.node[i].add_port(),
                        nffg.network.node[j].add_port(), id=d.id,
                        flowclass=d.flowclass)
    return nffg

  def start (self):
    for c, sub in self.chains_with_subgraphs:
      last_used_node = self.manager.getIdOfChainEnd_fromNetwork(c['chain'][0])

      # Mapping must be started with subchains derived from e2e chains,
      # with lower latency requirement. It is realiyed by the preprocessor,
      # because it adds the subchains in the appropriate order.
      for curr_vnf, next_vnf, linkid in zip(c['chain'][:-1], c['chain'][1:],
                                            c['link_ids']):

        # Last element of chain is already mapped or SAP, if not
        # mapped do it now!
        if self.req.node[
          next_vnf].type != 'SAP' and self.manager.getIdOfChainEnd_fromNetwork(
          next_vnf) == -1:
          last_used_node = self._mapOneVNF(c['id'], sub, last_used_node,
                                           curr_vnf, next_vnf, linkid)
        else:
          '''We are on the end of the (sub)chain, and all chain
          elements are mapped except the last link.
          Execution is here if the IF condition evaluated to false:
            - next_vnf is a SAP OR
            - next_vnf is already mapped'''
          self._mapOneRequestLink(c['id'], sub, c['chain'][-2], c['chain'][-1],
                                  c['link_ids'][-1])
      '''Best-effort links should be mapped here. But I`m not sure it is
      required to deal with, because the upper layer could also specify
      them as service chains. '''

    # construct output NFFG with the mapping of VNFs and links
    return self.constructOutputNFFG()

  def reset (self):
    """Resets the CoreAlgorithm instance to its initial (after preprocessor)
    state. Links weights are also calculated by the preprocessor, so those
    are reset too. self.original_chains is the input chain with maxhop
    added as extra key to chains."""
    self._preproc(copy.deepcopy(self.net0), copy.deepcopy(self.req0),
                  self.original_chains)

  def getNodeCountInNetwork (self):
    count = 0
    for n, d in self.net.nodes_iter(data=True):
      if d['type'] == 'INFRA':
        count += 1
    return count
