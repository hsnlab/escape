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

import copy
import networkx as nx
import sys
from collections import deque

import Alg1_Helper as helper
import BacktrackHandler as backtrack
import GraphPreprocessor
import UnifyExceptionTypes as uet

try:
  from escape.nffg_lib.nffg import NFFG
except ImportError:
  import sys, os
  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                  "../escape/escape/nffg_lib/")))
  from nffg import NFFG


class CoreAlgorithm(object):
  def __init__ (self, net0, req0, chains0, full_remap, cache_shortest_path, 
                overall_highest_delay,
                bw_factor=1, res_factor=1, lat_factor=1, shortest_paths=None):
    self.log = helper.log.getChild(self.__class__.__name__)
    self.log.setLevel(helper.log.getEffectiveLevel())

    self.log.info("Initializing algorithm variables")
    # only needed to get SAP`s name by its ID and for reset()
    self.req0 = copy.deepcopy(req0)

    # needed for reset()
    self.net0 = copy.deepcopy(net0)
    self.original_chains = chains0
    self.enable_shortest_path_cache = cache_shortest_path
    self.full_remap = full_remap
    
    # parameters contolling the backtrack process
    # how many of the best possible VNF mappings should be remembered
    self.bt_branching_factor = 3
    self.bt_limit = 6

    self._preproc(net0, req0, chains0, shortest_paths, overall_highest_delay)

    # must be sorted in alphabetic order of keys: cpu, mem, storage
    self.resource_priorities = [0.333, 0.333, 0.333]

    # which should count more in the objective function
    self.bw_factor = bw_factor
    self.res_factor = res_factor
    self.lat_factor = lat_factor

    ''' The new preference parameters are f(x) == 0 if x<c and f(1) == e,
    exponential in between.
    The bandwidth parameter refers to the average link utilization
    on the paths to the nodes (and also collocated request links).
    If  the even the agv is high it is much worse!'''
    self.pref_params = dict(cpu=dict(c=0.4, e=2.5), mem=dict(c=0.4, e=2.5),
                            storage=dict(c=0.4, e=2.5),
                            bandwidth=dict(c=0.1, e=10.0))
    """
    Functions to give the prefence values of a given ratio of resource 
    utilization. All fucntions should map every number between [0,1] to [0,1]
    real intervals and should be monotonic!
    """
    self.pref_funcs = dict(cpu=self._pref_noderes, mem=self._pref_noderes, 
                           storage=self._pref_noderes, bandwidth=self._pref_bw)

    # we need to store the original preprocessed NFFG too. with remove VNF-s 
    # and not STATIC links
    self.bare_infrastucture_nffg = self.net
    
    # peak number of VNFs that were mapped to resource at the same time
    self.peak_mapped_vnf_count = 0
    self.sap_count = len([i for i in self.req.saps])

    # The networkx graphs from the NFFG should be enough for the core
    # unwrap them, to save one indirection after the preprocessor has
    # finished.
    self.net = self.net.network
    self.req = self.req.network

  def _preproc (self, net0, req0, chains0, shortest_paths, 
                overall_highest_delay):
    self.log.info("Preprocessing:")
    
    # 100 000ms is considered to be infinite latency
    self.manager = helper.MappingManager(net0, req0, chains0, 
                                         overall_highest_delay)

    self.preprocessor = GraphPreprocessor.GraphPreprocessorClass(net0, req0,
                                                                 chains0,
                                                                 self.manager)
    self.preprocessor.shortest_paths = shortest_paths
    self.net = self.preprocessor.processNetwork(self.full_remap, 
                                                self.enable_shortest_path_cache)
    self.req, chains_with_subgraphs = self.preprocessor.processRequest(
      self.net)
    self.bt_handler = backtrack.BacktrackHandler(chains_with_subgraphs, 
         self.bt_branching_factor, self.bt_limit)

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
        if self.net.node[i].resources['bandwidth'] == float("inf"):
          return 0, 0
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
        # this is only a preliminary check (the bw_req should also be accomadated
        # by the hosting node)
        avail_bw = self.net.node[path_to_map[-1]].availres[
                     'bandwidth'] - internal_bw_req
        if avail_bw < 0:
          return -1

    if len(path_to_map) > 1:
      for i, j, k in zip(path_to_map[:-1], path_to_map[1:], linkids):
        if self.net[i][j][k].availbandwidth < bw_req:
          self.log.debug(
            "Link %s, %s has only %f Mbps capacity, but %f is required." % (
              i, j, self.net[i][j][k].availbandwidth, bw_req))
          return -1
        else:
          if not self.net[i][j][k].bandwidth == float("inf"):
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
      is_it_sap, util = self._checkBandwidthUtilOnHost(path_to_map[-1], 
                                                       bw_req + internal_bw_req)
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
      if max_bw < float("inf"):
        sum_w = float(max_bw - (act_bw - bw_req - internal_bw_req)) / max_bw
      else:
        sum_w = 0.0
      if act_bw < bw_req + internal_bw_req:
        self.log.debug(
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

  # UNUSED NOW
  def _preferenceValueOfUtilization (self, x, attr):
    c = self.pref_params[attr]['c']
    e = self.pref_params[attr]['e']
    if x < c:
      return 0.0
    else:
      return (e + 1) ** float((x - c) / (1 - c)) - 1

  def _pref_noderes(self, x):
    if x < 0.2:
      return 0.0
    else:
      return 1.25 * x - 0.25
    
  def _pref_bw(self, x):
    if x < 0.2:
      return 0.0
    else:
      return -1.5625 * ((x-1) ** 2) + 1
      

  def _objectiveFunction (self, cid, node_id, prev_vnf_id, vnf_id, reqlinkid,
                          path_to_map, linkids, sum_latency):
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
        self.log.debug("Host %s is not a good candidate for hosting %s due to "
                       "bandwidth requirement."%(node_id, vnf_id))
        return -1
      local_latreq = self.manager.getLocalAllowedLatency(cid, prev_vnf_id,
                                                         vnf_id, reqlinkid)
      if sum_latency == -1 or sum_latency > local_latreq or not \
           self.manager.isVNFMappingDistanceGood(\
                prev_vnf_id, vnf_id, path_to_map[0], path_to_map[-1]) or \
           local_latreq == 0 or not self.manager.areChainEndsReachableInLatency(\
                sum_latency, node_id, cid):
        self.log.debug("Host %s is too far measured in latency for hosting %s."%
                       (node_id, vnf_id))
        return -1

      '''Here we know that node_id have enough resource and the path
      leading there satisfies the bandwidth req of the potentially
      mapped edge of req graph. And the latency requirements as well'''
      max_rescomponent_value = 0
      for attr, res_w in zip(['cpu', 'mem', 'storage'],
                             self.resource_priorities):
        if maxres[attr] == float("inf"):
          sum_res += self.pref_funcs[attr](0.0)
        else:
          sum_res += res_w * self.pref_funcs[attr](
            float(maxres[attr] - (available[attr] - requested[attr])) / maxres[
              attr])
        max_rescomponent_value += self.pref_funcs[attr](1.0) * res_w

      # Scale them to the same interval
      scaled_res_comp = 10 * float(sum_res) / max_rescomponent_value
      scaled_bw_comp = 10 * float(
        self.pref_funcs['bandwidth'](avg_link_util)) / \
        self.pref_funcs['bandwidth'](1.0)
      # Except latency component, because it is added outside of the objective 
      # function
      # scaled_lat_comp = 10 * float(sum_latency) / local_latreq

      # TODO: correct logs to new latency calculation!
      self.log.debug("avglinkutil pref value: %f, sum res: %f" % (
        self.bw_factor * scaled_bw_comp, self.res_factor * scaled_res_comp))

      return self.bw_factor * scaled_bw_comp + self.res_factor * scaled_res_comp
    else:
      self.log.debug("Host %s does not have engough node resource for hosting %s."%
                     (node_id, vnf_id))
      return -1

  def _updateGraphResources (self, bw_req, path, linkids, vnf=None, node=None, 
                             redo=False):
    """Subtracts the required resources by the (vnf, node) mapping
    and path with bw_req from the available resources of the
    substrate network. vnf and node variables should be given, if those are
    just mapped now. (not when we want to map only a path between two already
    mapped VNFs)
    redo=True means we are doing a backstep in the mapping and we want to redo 
    the resource reservations.
    TODO: use redo parameter!! and checking not to exceed max!!
    NOTE1: the ending of `path` is `node`.
    NOTE2: feasibility is already checked by _objectiveFunction()"""

    if vnf is not None and node is not None:
      if self.net.node[node].type != 'INFRA':
        raise uet.InternalAlgorithmException(
          "updateGraphResources should only be called on Infra nodes!")
      if redo:
        res_to_substractoradd = copy.deepcopy(self.req.node[vnf].resources)
        for attr in ['cpu', 'mem', 'storage', 'bandwidth']:
        # delay is not subtracted!!
          if res_to_substractoradd[attr] is not None:
            res_to_substractoradd[attr] = -1 * res_to_substractoradd[attr]
      else:
        res_to_substractoradd = self.req.node[vnf].resources
      newres = self.net.node[node].availres.subtractNodeRes(\
                                   res_to_substractoradd,
                                   self.net.node[node].resources)
      self.net.node[node].availres = newres

    if redo:
      bw_req = -1 * bw_req

    if len(path) == 0:
      self.log.warn("Updating resources with 0 length path!")
    elif len(path) > 0:
      # collocation or 1st element of path needs to be updated.
      if self.net.node[path[0]].type != 'SAP':
        self.net.node[path[0]].availres['bandwidth'] -= bw_req
        new_bw = self.net.node[path[0]].availres['bandwidth']
        if new_bw < 0 or new_bw > self.net.node[path[0]].resources['bandwidth']:
          self.log.error("Node bandwidth is incorrect with value %s!"%new_bw)
          raise uet.InternalAlgorithmException("An internal bandwidth value got"
                                       " below zero or exceeded maximal value!")
        elif new_bw == 0:
          self.net.node[
            path[0]].weight = float("inf")
        else:
          self.net.node[path[0]].weight = 1.0 / new_bw
      if len(path) > 1:
        for i, j, k in zip(path[:-1], path[1:], linkids):
          self.net[i][j][k].availbandwidth -= bw_req
          new_bw = self.net[i][j][k].availbandwidth
          if new_bw < 0 or new_bw > self.net[i][j][k].bandwidth:
            self.log.error("Link bandwidth is incorrect with value %s!"%new_bw)
            raise uet.InternalAlgorithmException("The bandwidth resource of "
                      "link %s got below zero, or exceeded maximal value!"%k)
          elif new_bw == 0:
            self.net[i][j][k].weight = float("inf")
          else:
            self.net[i][j][k].weight = 1.0 / new_bw
          # update node bandwidth resources on the path
          if self.net.node[j].type != 'SAP':
            self.net.node[j].availres['bandwidth'] -= bw_req
            new_bw_innode = self.net.node[j].availres['bandwidth']
            if new_bw_innode < 0 or new_bw_innode > \
               self.net.node[j].resources['bandwidth']:
              self.log.error("Node bandwidth is incorrect with value %s!"%
                             new_bw_innode)
              raise uet.InternalAlgorithmException("The bandwidth resource"
              " of node %s got below zero, or exceeded the maximal value!"%j)
            elif new_bw_innode == 0:
              self.net.node[j].weight = float("inf")
            else:
              self.net.node[j].weight = 1.0 / new_bw_innode
    self.log.debug("Available network resources are updated: redo: %s, vnf: "
                   "%s, path: %s"%(redo, vnf, path))

  def _takeOneGreedyStep(self, cid, step_data):
    """
    Calls all required functions to take a greedy step, mapping the actual 
    VNF and link to the selected host and path.
    Feasibility should be already tested for every case.
    And adds the step_data back to the current backtrack level, so it could be 
    undone just like in other cases.
    """
    self.log.debug(
      "Mapped VNF %s to node %s in network. Updating data accordingly..." % 
      (step_data['vnf_id'], step_data['target_infra']))
    self.manager.vnf_mapping.append((step_data['vnf_id'], 
                                     step_data['target_infra']))
    # maintain peak VNF count during the backtracking
    if len(self.manager.vnf_mapping) - self.sap_count > \
       self.peak_mapped_vnf_count:
      self.peak_mapped_vnf_count = len(self.manager.vnf_mapping) - self.sap_count
    self.log.debug("Request Link %s, %s, %s mapped to path: %s" % (
      step_data['prev_vnf_id'], step_data['vnf_id'], step_data['reqlinkid'], 
      step_data['path']))
    self.manager.link_mapping.add_edge(step_data['prev_vnf_id'], 
                 step_data['vnf_id'], key=step_data['reqlinkid'], 
                 mapped_to=step_data['path'], 
                 path_link_ids=step_data['path_link_ids'])
    self._updateGraphResources(step_data['bw_req'],
      step_data['path'], step_data['path_link_ids'], step_data['vnf_id'], 
      step_data['target_infra'])
    self.manager.updateChainLatencyInfo(cid, step_data['used_latency'], 
                                        step_data['target_infra'])
    self.bt_handler.addFreshlyMappedBacktrackRecord(step_data, None)

  def _mapOneVNF (self, cid, subgraph, start, prev_vnf_id, vnf_id, reqlinkid, 
                  bt_record = None):
    """
    Starting from the node (start), where the previous vnf of the chain
    was mapped, maps vnf_id to an appropriate node.
    is_it_forward_step indicates if we have to check for all possible mappings 
    and save it to the backtrack structure, or we have received a backtrack 
    record due to a backstep.
    """
    best_node_que = deque(maxlen = self.bt_branching_factor)
    deque_length = 0
    base_bt_record = {'prev_vnf_id': prev_vnf_id, 'vnf_id': vnf_id, 
                      'reqlinkid': reqlinkid, 'last_used_node': start,
                      'bw_req': self.req[prev_vnf_id][vnf_id]\
                      [reqlinkid].bandwidth}
    '''Edge data must be used from the substrate network!
    NOTE(loops): shortest path from i to i is [i] (This path is the
    collocation, and 1 long paths are handled right by the
    _objectiveFunction()/_calculateAvgLinkUtil()/_sumLat() functions)'''
    paths, linkids = helper.shortestPathsBasedOnEdgeWeight(subgraph, start)
    # TODO: sort 'paths' in ordered dict according to new latency pref value.
    # allow only infras which has some 'supported'
    potential_hosts = filter(lambda h, nodes=self.net.node: 
      nodes[h].type=='INFRA' and nodes[h].supported is not None, 
                             paths.keys())
    # allow only hosts which supports this NF
    potential_hosts = filter(lambda h, v=vnf_id, nodes=self.net.node, 
      vnfs=self.req.node: vnfs[v].functional_type in nodes[h].supported, 
                             potential_hosts)
    # allow only hosts which complies to plac_crit if any
    potential_hosts = filter(lambda h, v=vnf_id, vnfs=self.req.node:
      len(vnfs[v].placement_criteria)==0 or h in vnfs[v].placement_criteria, 
                             potential_hosts)
    potential_hosts_sumlat = []
    for host in potential_hosts:
      potential_hosts_sumlat.append((host, self._sumLatencyOnPath(paths[host], 
                                                                  linkids[host])))
    hosts_with_lat_prefvalues = self.manager.calcDelayPrefValues(\
                            potential_hosts_sumlat, prev_vnf_id, vnf_id, 
                            reqlinkid, cid, subgraph, start)
    # TODO: self.use_old_lat_calc variable to change between lat pref val 
    # calculation methods
    for map_target, sumlat, latprefval in hosts_with_lat_prefvalues:
      value = self._objectiveFunction(cid, map_target,
                                      prev_vnf_id, vnf_id,
                                      reqlinkid,
                                      paths[map_target],
                                      linkids[map_target],
                                      sumlat)
      if value > -1:
        self.log.debug("Calculated latency preference value: %f for VNF %s and "
                       "path: %s" % (latprefval, vnf_id, paths[map_target]))
        value += 10.0*latprefval
        self.log.debug("Calculated value: %f for VNF %s and path: %s" % (
          value, vnf_id, paths[map_target]))
        just_found = copy.deepcopy(base_bt_record)
        just_found.update(zip(('target_infra', 'path', 'path_link_ids', 
                              'used_latency', 'obj_func_value'), 
                          (map_target, paths[map_target], 
                           linkids[map_target], sumlat, value)))
        if deque_length == 0:
          best_node_que.append(just_found)
          deque_length += 1
        else:
          best_node_sofar = best_node_que.pop()
          best_node_que.append(best_node_sofar)
          if best_node_sofar['obj_func_value'] > value:
            best_node_que.append(just_found)
          elif deque_length <= self.bt_branching_factor > 1:
            least_good_que = deque()
            least_good_sofar = best_node_que.popleft()
            deque_length -= 1
            while least_good_sofar['obj_func_value'] > value:
              least_good_que.append(least_good_sofar)
              # too many good nodes can be remove, because we already 
              # know just found is worse than the best node
              least_good_sofar = best_node_que.popleft()
              deque_length -= 1
            best_node_que.appendleft(least_good_sofar)
            best_node_que.appendleft(just_found)
            deque_length += 2
            while deque_length < self.bt_branching_factor:
              try:
                best_node_que.appendleft(least_good_que.popleft())
              except IndexError:
                break
      else:
        # self.log.debug("Host %s is not a good candidate for hosting %s."
        #                %(map_target,vnf_id))
        pass
    try:
      best_node_sofar = best_node_que.pop()
      self.bt_handler.addBacktrackLevel(cid, best_node_que)
      # we don't have to deal with the deque length anymore, because it is 
      # handled by the bactrack structure.
    except IndexError:
      self.log.info("Couldn`t map VNF %s anywhere, trying backtrack..." % 
                    vnf_id)
      raise uet.MappingException("Couldn`t map VNF %s anywhere trying"
                                 "backtrack..." % vnf_id,
                                 backtrack_possible = True)
    self._takeOneGreedyStep(cid, best_node_sofar)

  def _mapOneRequestLink (self, cid, g, vnf1, vnf2, reqlinkid):
    """
    Maps a request link, when both ends are already mapped.
    Uses the weighted shortest path.
    TODO: Replace dijkstra with something more sophisticated.
    """
    n1 = self.manager.getIdOfChainEnd_fromNetwork(vnf1)
    n2 = self.manager.getIdOfChainEnd_fromNetwork(vnf2)
    if n1 == -1 or n2 == -1:
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
        "request link between %s and %s" % (n1, n2, vnf1, vnf2),
        backtrack_possible = True)

    used_lat = self._sumLatencyOnPath(path, linkids)

    if self._calculateAvgLinkUtil(path, linkids, bw_req) == -1:
      self.log.info(
        "Last link of chain or best-effort link %s, %s couldn`t be mapped!" % (
          vnf1, vnf2))
      raise uet.MappingException(
        "Last link of chain or best-effort link %s, %s, %s couldn`t be mapped "
        "due to link capacity" % (vnf1, vnf2, reqlinkid),
        backtrack_possible = True)
    elif self.manager.getLocalAllowedLatency(cid, vnf1, vnf2, reqlinkid) < \
         used_lat:
      raise uet.MappingException(
        "Last link %s, %s, %s of chain couldn`t be mapped due to latency "
        "requirement." % (vnf1, vnf2, reqlinkid),
        backtrack_possible = True)
    self.log.debug(
      "Last link of chain or best-effort link %s, %s was mapped to path: %s" % (
        vnf1, vnf2, path))
    self._updateGraphResources(bw_req, path, linkids)
    self.manager.updateChainLatencyInfo(cid, used_lat, n2)
    link_mapping_rec = {'bw_req': bw_req, 'path': path, 
                        'linkids': linkids, 'used_lat': used_lat,
                        'vnf1': vnf1, 'vnf2': vnf2, 
                        'reqlinkid': reqlinkid}
    self.bt_handler.addFreshlyMappedBacktrackRecord(None, link_mapping_rec)
    self.manager.link_mapping.add_edge(vnf1, vnf2, key=reqlinkid,
                                       mapped_to=path, path_link_ids=linkids)

  def _resolveLinkMappingRecord(self, c, link_bt_record):
    """
    Undo link reservation.
    """
    self.log.debug("Redoing link resources due to LinkMappingRecord handling.")
    self._updateGraphResources(link_bt_record['bw_req'], 
                               link_bt_record['path'], 
                               link_bt_record['linkids'],
                               redo = True)
    self.manager.updateChainLatencyInfo(c['id'], 
                                        -1*link_bt_record['used_lat'], 
                                        link_bt_record['path'][0])
    self.manager.link_mapping.remove_edge(link_bt_record['vnf1'], 
                                          link_bt_record['vnf2'], 
                                          key = link_bt_record['reqlinkid'])

  def _resolveBacktrackRecord(self, c, bt_record):
    """
    Undo VNF resource reservetion on host and path leading to it.
    """
    self._updateGraphResources(bt_record['bw_req'],
                               bt_record['path'], 
                               bt_record['path_link_ids'],
                               bt_record['vnf_id'], 
                               bt_record['target_infra'],
                               redo = True)
    try:
      self.manager.link_mapping.remove_edge(bt_record['prev_vnf_id'], 
                                            bt_record['vnf_id'],
                                            key=bt_record['reqlinkid'])
    except nx.NetworkXError as nxe:
      raise uet.InternalAlgorithmException("Tried to remove edge from link "
                "mapping structure which is not mapped!")
    if self.req.node[bt_record['vnf_id']].type != 'SAP':
      self.manager.vnf_mapping.remove((bt_record['vnf_id'], 
                                       bt_record['target_infra']))
    self.manager.updateChainLatencyInfo(c['id'], 
                                        -1*bt_record['used_latency'],
                                        bt_record['last_used_node'])

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
    if 'infra_ports' in helperlink:
      flowsrc = helperlink['infra_ports'][0]
      flowdst = helperlink['infra_ports'][1]
    else:
      flowsrc = None
      flowdst = None
    reqlink = self.req[v1][v2][reqlid]
    bw = reqlink.bandwidth
    # Let's use the substrate SAPs' ID-s for TAG definition.
    if self.req.node[v1].type == 'SAP':
      v1 = self.manager.getIdOfChainEnd_fromNetwork(v1)
    if self.req.node[v2].type == 'SAP':
      v2 = self.manager.getIdOfChainEnd_fromNetwork(v2)
    # The action and match are the same format
    tag = "TAG=%s|%s|%s" % (v1, v2, reqlid)
    if len(path) == 1:
      # collocation happened, none of helperlink`s port refs should be None
      match_str = "in_port="
      action_str = "output="
      if flowdst is None or flowsrc is None:
        raise uet.InternalAlgorithmException(
          "No InfraPort found for a dynamic link of collocated VNFs")
      match_str += str(flowsrc.id)
      if reqlink.flowclass is not None:
        match_str += ";flowclass=%s" % reqlink.flowclass
      action_str += str(flowdst.id)
      self.log.debug("Collocated flowrule %s => %s added to Port %s of %s" % (
        match_str, action_str, flowsrc.id, path[0]))
      flowsrc.add_flowrule(match_str, action_str, bw, hop_id = reqlid)
    else:
      # set the flowrules for the transit Infra nodes
      for i, j, k, lidij, lidjk in zip(path[:-2], path[1:-1], path[2:],
                                       linkids[:-1], linkids[1:]):
        match_str = "in_port="
        action_str = "output="
        match_str += str(self.net[i][j][lidij].dst.id)
        if reqlink.flowclass is not None:
          match_str += ";flowclass=%s" % reqlink.flowclass
        action_str += str(self.net[j][k][lidjk].src.id)
        if not (self.net.node[i].type == 'SAP' and self.net.node[k].type == 'SAP'\
           and len(path) == 3):
          # if traffic is just going through, we dont have to TAG at all.
          # Transit SAPs would mess it up pretty much, but it is not allowed.
          if self.net.node[i].type == 'SAP' and self.net.node[k].type != 'SAP':
            action_str += ";" + tag
          else:
            match_str += ";" + tag
        self.log.debug("Transit flowrule %s => %s added to Port %s of %s" % (
          match_str, action_str, self.net[i][j][lidij].dst.id, j))
        nffg.network[i][j][lidij].dst.add_flowrule(match_str, action_str, bw, 
                                                   hop_id = reqlid)

      # set flowrule for the first element if that is not a SAP
      if nffg.network.node[path[0]].type != 'SAP':
        match_str = "in_port="
        action_str = "output="
        if flowsrc is None:
          raise uet.InternalAlgorithmException(
            "No InfraPort found for a dynamic link which starts a path")
        match_str += str(flowsrc.id)
        if reqlink.flowclass is not None:
          match_str += ";flowclass=%s" % reqlink.flowclass
        action_str += str(nffg.network[path[0]][path[1]][linkids[0]].src.id)
        action_str += ";" + tag
        self.log.debug("Starting flowrule %s => %s added to Port %s of %s" % (
          match_str, action_str, flowsrc.id, path[0]))
        flowsrc.add_flowrule(match_str, action_str, bw, hop_id = reqlid)

      # set flowrule for the last element if that is not a SAP
      if nffg.network.node[path[-1]].type != 'SAP':
        match_str = "in_port="
        action_str = "output="
        match_str += str(self.net[path[-2]][path[-1]][linkids[-1]].dst.id)
        if reqlink.flowclass is not None:
          match_str += ";flowclass=%s" % reqlink.flowclass
        match_str += ";" + tag
        if flowdst is None:
          raise uet.InternalAlgorithmException(
            "No InfraPort found for a dynamic link which finishes a path")
        action_str += str(flowdst.id) + ";UNTAG"
        self.log.debug("Finishing flowrule %s => %s added to Port %s of %s" % (
          match_str, action_str,
          self.net[path[-2]][path[-1]][linkids[-1]].dst.id, path[-1]))
        nffg.network[path[-2]][path[-1]][linkids[-1]].dst.add_flowrule(
          match_str, action_str, bw, hop_id = reqlid)

  def _retrieveOrAddVNF (self, nffg, vnfid):
    if vnfid not in nffg.network:
      nodenf = copy.deepcopy(self.req.node[vnfid])
      nffg.add_node(nodenf)
    else:
      nodenf = nffg.network.node[vnfid]
    return nodenf

  def _addSAPportIfNeeded(self, nffg, sapid, portid):
    """
    The request and substrate SAPs are different objects, the substrate does not
    neccessarily have the same ports which were used by the service graph.
    """
    if portid in [p.id for p in nffg.network.node[sapid].ports]:
      return portid
    else:
      return nffg.network.node[sapid].add_port(portid).id

  def _getSrcDstPortsOfOutputEdgeReq(self, nffg, sghop_id, infra, src=True, dst=True):
    """
    Retrieve the ending and starting infra port, where EdgeReq 
    should be connected. Raises exception if either of them is not found.
    If one of the ports is not requested, it remains None.
    NOTE: we can be sure there is only one flowrule with 'sghop_id' in this infra
    because we map SGHops based on shortest path algorithm and it would cut 
    loops from the shortest path (because there are only positive edge weights)
    """
    start_port_for_req = None
    end_port_for_req = None
    found = False
    for p in nffg.network.node[infra].ports:
      for fr in p.flowrules:
        if fr.hop_id == sghop_id:
          if src:
            start_port_for_req = p
            if not dst:
              found = True
              break
          if dst:
            for action in fr.action.split(";"):
              comm_param = action.split("=")
              if comm_param[0] == "output":
                end_port_id = comm_param[1]
                try:
                  end_port_id = int(comm_param[1])
                except ValueError: 
                  pass
                end_port_for_req = nffg.network.node[infra].ports[end_port_id]
                found = True
                break
        if found:
          break
      if found:
        break
    else:
      raise uet.InternalAlgorithmException("One of the ports was not "
            "found for output EdgeReq!")
    return start_port_for_req, end_port_for_req
  
  def _addEdgeReqToChainPieceStruct(self, e2e_chainpieces, cid, outedgereq):
    """
    Handles the structure for output EdgeReqs. Logs, helps avoiding code 
    duplication.
    """
    if cid in e2e_chainpieces:
      e2e_chainpieces[cid].append(outedgereq)
    else:
      e2e_chainpieces[cid] = [outedgereq]
    self.log.debug("Requirement chain added to BiSBiS %s with path %s and"
                   " latency %s."%(outedgereq.src.node.id, outedgereq.sg_path, 
                                   outedgereq.delay))

  def _divideEndToEndRequirements(self, nffg):
    """
    Splits the E2E latency requirement between all BiSBiS nodes, which were used
    during the mapping procedure. Draws EdgeReqs into the output NFFG, saves the
    SGHop path where it should be satisfied, divides the E2E latency weighted by
    the offered latency of the affected BiSBiS-es.
    """
    # remove if there are any EdgeReqs in the graph
    for req in [r for r in nffg.reqs]:
      nffg.del_edge(req.src, req.dst, req.id)
    e2e_chainpieces = {}
    last_sghop_id = None
    for cid, first_vnf, infra in self.manager.genPathOfChains(nffg):
      if nffg.network.node[infra].type == 'INFRA':
        if nffg.network.node[infra].infra_type == NFFG.TYPE_INFRA_BISBIS:
          mapped_req = self.req.subgraph((vnf.id for vnf in \
                                          nffg.running_nfs(infra)))
          outedgereq = None
          delay_of_infra = self._sumLatencyOnPath([infra], [])
          if len(mapped_req) == 0 or \
             not self.manager.isAnyVNFInChain(cid, mapped_req) or \
             first_vnf is None:
            # we know that 'cid' traverses 'infra', but if this chain has no 
            # mapped node here, then it olny uses this infra in its path
            # OR              
            # This can happen when this BiSBiS is only forwarding the traffic 
            # of this service chain, BUT only VNFs from another service chains 
            # has been mapped here
            # OR 
            # there is some VNF of 'cid' mapped here, but now we traverse this
            # infra as transit
            sghop_id = self.manager.getSGHopOfChainMappedHere(cid, infra, 
                                                              last_sghop_id)
            src, dst = self._getSrcDstPortsOfOutputEdgeReq(nffg,
                                                           sghop_id, infra)
            # this is as much latency as we used for the mapping
            # 0 bandwith should be forwarded, because they are already taken into
            # account in SGHop bandwith
            outedgereq = nffg.add_req(src, dst, delay=delay_of_infra,
                                      bandwidth=0,
                                      id=self.manager.getNextOutputChainId(), 
                                      sg_path=[sghop_id])
            self._addEdgeReqToChainPieceStruct(e2e_chainpieces, cid, outedgereq)
          else:
            chain_pieces_of_infra = self.manager.\
                                    getChainPiecesOfReqSubgraph(cid, mapped_req)
            for chain_piece, link_ids_piece in chain_pieces_of_infra:
              src, _ = self._getSrcDstPortsOfOutputEdgeReq(nffg, 
                                                           link_ids_piece[0], 
                                                           infra, dst=False)
              _, dst = self._getSrcDstPortsOfOutputEdgeReq(nffg,
                                                           link_ids_piece[-1],
                                                           infra, src=False)
              # a chain part spends one time of delay_of_infra for every link 
              # mapped here, becuase it is valid between all the port pairs only.
              outedgereq = nffg.add_req(src, dst, 
                                        delay=len(link_ids_piece)*delay_of_infra, 
                                        bandwidth=0,
                                        id=self.manager.getNextOutputChainId(),
                                        sg_path=link_ids_piece)
              self._addEdgeReqToChainPieceStruct(e2e_chainpieces, cid, 
                                                 outedgereq)
          last_sghop_id = outedgereq.sg_path[-1]
            
    # now iterate on the chain pieces
    for cid in e2e_chainpieces:
      # this is NOT equal to permitted minus remaining!
      sum_of_latency_pieces = sum((er.delay for er in e2e_chainpieces[cid]))
      # divide the remaining E2E latency weighted by the least necessary latency
      # and add this to the propagated latency as extra.
      if sum_of_latency_pieces > 0:
        for er in e2e_chainpieces[cid]:
          er.delay += float(er.delay) / sum_of_latency_pieces * \
                      self.manager.getRemainingE2ELatency(cid)
          self.log.debug("Output latency requirement increased to %s in %s for "
                         "path %s"%(er.delay, er.src.node.id, er.sg_path))

  def constructOutputNFFG (self):
    # use the unchanged input from the lower layer (deepcopied in the
    # constructor, modify it now)
    if self.full_remap:
      # use the already preprocessed network we don't need to append the VNF
      # mappings to the existing VNF mappings
      nffg = self.bare_infrastucture_nffg
    else:
      # the just mapped request should be appended to the one sent by the 
      # lower layer indicating the already mapped VNF-s.
      nffg = self.net0
    for vnf, host in self.manager.vnf_mapping:
      # duplicate the object, so the original one is not modified.
      if self.req.node[vnf].type == 'NF':
        mappednodenf = self._retrieveOrAddVNF(nffg, vnf)

        for i, j, k, d in self.req.out_edges_iter([vnf], data=True, keys=True):
          # i is always vnf
          # Generate only ONE InfraPort for every Port of the NF-s with 
          # predictable port ID. Format: <<InfraID|NFID|NFPortID>>
          infra_port_id = "|".join((str(host),str(vnf),str(d.src.id)))
          # WARNING: PortContainer's "in" operator needs a Port object!!
          # We need to use try catch to test inclusion for port ID
          try:
            out_infra_port = nffg.network.node[host].ports[infra_port_id]
            self.log.debug("Port %s found in Infra %s leading to port %s of NF"
                           " %s."%(infra_port_id, host, d.src.id, vnf))
          except KeyError:
            out_infra_port = nffg.network.node[host].add_port(id=infra_port_id)
            self.log.debug("Port %s added to Infra %s to NF %s." 
                           % (out_infra_port.id, host, vnf))
            # this is needed when an already mapped VNF is being reused from an 
            # earlier mapping, and the new SGHop's port only exists in the 
            # current request. WARNING: no function for Port object addition!
            try:
              mappednodenf.ports[d.src.id]
            except KeyError:
              mappednodenf.add_port(id = d.src.id, properties = d.src.properties)
            # use the (copies of the) ports between the SGLinks to
            # connect the VNF to the Infra node.
            # Add the mapping indicator DYNAMIC link only if the port was just
            # added. NOTE: In case of NOT FULL_REMAP, the VNF-s left in place 
            # still have these links. In case of (future) VNF replacement, 
            # change is required here!
            nffg.add_undirected_link(out_infra_port, mappednodenf.ports[d.src.id],
                                     dynamic=True)
          helperlink = self.manager.link_mapping[i][j][k]
          if 'infra_ports' in helperlink:
            helperlink['infra_ports'][0] = out_infra_port
          else:
            helperlink['infra_ports'] = [out_infra_port, None]

        for i, j, k, d in self.req.in_edges_iter([vnf], data=True, keys=True):
          # j is always vnf
          infra_port_id = "|".join((str(host),str(vnf),str(d.dst.id)))
          try:
            in_infra_port = nffg.network.node[host].ports[infra_port_id]
            self.log.debug("Port %s found in Infra %s leading to port %s of NF"
                           " %s."%(infra_port_id, host, d.dst.id, vnf))
          except KeyError:
            in_infra_port = nffg.network.node[host].add_port(id=infra_port_id)
            self.log.debug("Port %s added to Infra %s to NF %s." 
                           % (in_infra_port.id, host, vnf))
            try:
              mappednodenf.ports[d.dst.id]
            except KeyError:
              mappednodenf.add_port(id = d.dst.id, properties = d.dst.properties)
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
    # NFFG instance. Ports for the SG link ends are reused from the mapped NFFG.
    # Add all the SGHops to the NFFG keeping the SGHops` identifiers, so the
    # installed flowrules and TAG-s will be still valid
    try:
      for i, j, d in self.req.edges_iter(data=True):
        if self.req.node[i].type == 'SAP':
          # if i is a SAP we have to find what is its ID in the network
          # d.id is the link`s key
          sapstartid = self.manager.getIdOfChainEnd_fromNetwork(i)
          if self.req.node[j].type == 'SAP':
            sapendid = self.manager.getIdOfChainEnd_fromNetwork(j)
            nffg.add_sglink(nffg.network.node[sapstartid].ports[
                 self._addSAPportIfNeeded(nffg, sapstartid, d.src.id)],
                            nffg.network.node[sapendid].ports[
                 self._addSAPportIfNeeded(nffg, sapendid, d.dst.id)], 
                            id=d.id, flowclass=d.flowclass, tag_info=d.tag_info,
                            delay=d.delay, bandwidth=d.bandwidth)
          else:
            nffg.add_sglink(nffg.network.node[sapstartid].ports[
                 self._addSAPportIfNeeded(nffg, sapstartid, d.src.id)],
                            nffg.network.node[j].ports[d.dst.id], id=d.id,
                            flowclass=d.flowclass, tag_info=d.tag_info,
                            delay=d.delay, bandwidth=d.bandwidth)
        elif self.req.node[j].type == 'SAP':
          sapendid = self.manager.getIdOfChainEnd_fromNetwork(j)
          nffg.add_sglink(nffg.network.node[i].ports[d.src.id],
                          nffg.network.node[sapendid].ports[
                            self._addSAPportIfNeeded(nffg, sapendid, d.dst.id)],
                          id=d.id, flowclass=d.flowclass, tag_info=d.tag_info,
                          delay=d.delay, bandwidth=d.bandwidth)
        else:
          nffg.add_sglink(nffg.network.node[i].ports[d.src.id],
                          nffg.network.node[j].ports[d.dst.id], id=d.id,
                          flowclass=d.flowclass, tag_info=d.tag_info,
                          delay=d.delay, bandwidth=d.bandwidth)
    except RuntimeError as re:
      raise uet.InternalAlgorithmException("RuntimeError catched during SGLink"
          " addition to the output NFFG. Not Yet Implemented feature: keeping "
          "already mapped SGLinks in place if not full_remap. Maybe same SGLink "
          "ID in current request and a previous request?")
    
    # Add EdgeReqs to propagate E2E latency reqs.
    self._divideEndToEndRequirements(nffg)

    return nffg


  def start (self):
    # breaking when there are no more BacktrackLevels forward, meaning the 
    # mapping is full. Or exception is thrown, when mapping can't be finished.
    self.log.info("Starting core mapping procedure...")
    while True:
      # Mapping must be started with subchains derived from e2e chains,
      # with lower latency requirement. It is realiyed by the preprocessor,
      # because it adds the subchains in the appropriate order.
      # ANF moveOneSubchainLevelForward() respects this order.
      tmp = self.bt_handler.moveOneBacktrackLevelForward()
      if tmp is None:
        break
      else:
        c, sub, curr_vnf, next_vnf, linkid = tmp
        bt_record = None
        last_used_node = self.manager.getIdOfChainEnd_fromNetwork(curr_vnf)
        # break when we can step forward a BacktrackLevel, in other words: don't
        # break when we have to do backtrack then substrate network state is 
        # restored and we shall try another mapping. MappingException is reraised
        # when no backtrack is available.
        while True:
          try:
            # Last element of chain is already mapped or SAP, if not
            # mapped do it now!
            if self.req.node[
              next_vnf].type != 'SAP' and self.manager.getIdOfChainEnd_fromNetwork(
              next_vnf) == -1:
              if bt_record is None:
                self._mapOneVNF(c['id'], sub, last_used_node,
                                curr_vnf, next_vnf, linkid)
              else:
                self._takeOneGreedyStep(c['id'], bt_record)
                
            else:
              '''We are on the end of the (sub)chain, and all chain
              elements are mapped except the last link.
              Execution is here if the IF condition evaluated to false:
                - next_vnf is a SAP OR
                - next_vnf is already mapped'''
              self._mapOneRequestLink(c['id'], sub, curr_vnf, next_vnf,
                                      linkid)
            break
          except uet.MappingException as me:
            self.log.debug("MappingException catched for backtrack purpose, "
                           "its message is: "+me.msg)
            if not me.backtrack_possible:
              # re-raise the exception, we have ran out of backrack 
              # possibilities.
              raise uet.MappingException(me.msg, False, peak_sc_cnt=me.peak_sc_cnt,
                                         peak_vnf_cnt=self.peak_mapped_vnf_count)
            else:
              try:
                c, sub, bt_record, link_bt_rec_list = \
                   self.bt_handler.getNextBacktrackRecordAndSubchainSubgraph([])
              except uet.MappingException as me2:
                if not me2.backtrack_possible:
                  raise uet.MappingException(me2.msg, False, 
                            peak_sc_cnt=me2.peak_sc_cnt,
                            peak_vnf_cnt=self.peak_mapped_vnf_count)
                else:
                  raise
              for c_prime, prev_bt_rec, link_mapping_rec in link_bt_rec_list:
                if link_mapping_rec is not None:
                  self._resolveLinkMappingRecord(c_prime, link_mapping_rec)
                if prev_bt_rec is not None:
                  self._resolveBacktrackRecord(c_prime, prev_bt_rec)
              # use this bt_record to try another greedy step
              curr_vnf = bt_record['prev_vnf_id']
              next_vnf = bt_record['vnf_id']
              linkid = bt_record['reqlinkid']
              last_used_node = bt_record['last_used_node']

    # construct output NFFG with the mapping of VNFs and links
    return self.constructOutputNFFG()

  def setBacktrackParameters(self, bt_limit=6, bt_branching_factor=3):
    """
    Sets the depth and maximal branching factor for the backtracking process on
    nodes. bt_limit determines how many request graph nodes should be remembered
    for backtracking purpose. bt_branching_factor determines how many possible 
    host-path pairs should be remembered at most for one VNF.
    """
    if bt_branching_factor < 1 or "." in str(bt_branching_factor) or \
       bt_limit < 1 or "." in str(bt_limit):
      raise uet.BadInputException("Branching factor and backtrack limit should "
                                  "be at least 1, integer values", 
                                  "%s and %s were given."\
                                  %(bt_limit, bt_branching_factor))
    self.bt_branching_factor = bt_branching_factor
    self.bt_limit = bt_limit
    self.bt_handler = backtrack.BacktrackHandler(\
                        self.bt_handler.subchains_with_subgraphs, 
                        self.bt_branching_factor, self.bt_limit)
    
  def setResourcePrioritiesOnNodes(self, cpu=0.3333, mem=0.3333, 
                                   storage=0.3333):
    """
    Sets what weights should be used for adding up the preference values of 
    resource utilization on nodes.
    """
    sumw = cpu + mem + storage 
    if abs(sumw - 1) > 0.0000001:
      raise uet.BadInputException("The sum of resource priorities should be 1.0",
                                  "the sum of resource priorities are %s"%sumw)
    self.resource_priorities = [cpu, mem, storage]

  def reset (self):
    """Resets the CoreAlgorithm instance to its initial (after preprocessor) 
    and   state. Links weights are also calculated by the preprocessor, so those
    are reset too. self.original_chains is the list of input chains."""
    self._preproc(copy.deepcopy(self.net0), copy.deepcopy(self.req0),
                  self.original_chains)
