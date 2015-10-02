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
from collections import deque

import networkx as nx

import GraphPreprocessor
import UnifyExceptionTypes as uet
import Alg1_Helper as helper
import BacktrackHandler as backtrack

try:
  from escape.util.nffg import NFFG
except ImportError:
  import sys, os, inspect

  sys.path.insert(0, os.path.join(os.path.abspath(os.path.realpath(
    os.path.abspath(
      os.path.split(inspect.getfile(inspect.currentframe()))[0])) + "/.."),
                                  "pox/ext/escape/util/"))
  from nffg import NFFG


class CoreAlgorithm(object):
  def __init__ (self, net0, req0, chains0, full_remap, cache_shortest_path):
    self.log = helper.log.getChild(self.__class__.__name__)

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
    self.bt_branching_factor = 4
    self.bt_limit = 5

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

    # we need to store the original preprocessed NFFG too. with remove VNF-s 
    # and not STATIC links
    self.bare_infrastucture_nffg = self.net
    
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
      newres = helper.subtractNodeRes(self.net.node[node].availres,
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
          raise uet.InternalAlgorithmException("An internal bandwidth value got"
                                       " below zero or exceeded maximal value!")
        elif new_bw == 0:
          self.net.node[
            path[0]].weight = sys.float_info.max  # maybe use float("inf")?
        else:
          self.net.node[path[0]].weight = 1.0 / new_bw
      if len(path) > 1:
        for i, j, k in zip(path[:-1], path[1:], linkids):
          self.net[i][j][k].availbandwidth -= bw_req
          new_bw = self.net[i][j][k].availbandwidth
          if new_bw < 0 or new_bw > self.net[i][j][k].bandwidth:
            raise uet.InternalAlgorithmException("The bandwidth resource of "
                      "link %s got below zero, or exceeded maximal value!"%k)
          elif new_bw == 0:
            self.net[i][j][k].weight = sys.float_info.max
          else:
            self.net[i][j][k].weight = 1.0 / new_bw
          # update node bandwidth resources on the path
          if self.net.node[j].type != 'SAP':
            self.net.node[j].availres['bandwidth'] -= bw_req
            new_bw_innode = self.net.node[j].availres['bandwidth']
            if new_bw_innode < 0 or new_bw_innode > \
               self.net.node[j].resources['bandwidth']:
              raise uet.InternalAlgorithmException("The bandwidth resource"
              " of node %s got below zero, or exceeded the maximal value!"%j)
            elif new_bw_innode == 0:
              self.net.node[j].weight = sys.float_info.max
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
    # TODO: Write an utility func, which gives path based on lat AND bw
    paths, linkids = helper.shortestPathsBasedOnEdgeWeight(subgraph, start)
    for map_target in paths:
      if self.net.node[map_target].type == 'INFRA' and self.net.node[
        map_target].supported is not None:
        
        """for supp in self.net.node[map_target].supported:
          self.log.debug(" ".join((map_target,"has supported type: ",supp)))
        """
                         
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
            if value > -1:
              self.log.debug("Calculated value: %f for VNF %s and path: %s" % (
                value, vnf_id, paths[map_target]))
              just_found = copy.deepcopy(base_bt_record)
              just_found.update(zip(('target_infra', 'path', 'path_link_ids', 
                                    'used_latency', 'obj_func_value'), 
                                (map_target, paths[map_target], 
                                 linkids[map_target], used_lat, value)))
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
              self.log.debug("Host %s is not a good candidate for hosting %s."
                             %(map_target,vnf_id))
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
      self.log.error(
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
    self.manager.link_mapping.remove_edge(bt_record['prev_vnf_id'], 
                                          bt_record['vnf_id'],
                                          key=bt_record['reqlinkid'])
    if self.req.node[bt_record['vnf_id']].type != 'SAP':
      self.manager.vnf_mapping.remove((bt_record['vnf_id'], 
                                       bt_record['target_infra']))
    self.manager.updateChainLatencyInfo(c['id'], 
                                        -1*bt_record['used_latency'],
                                        bt_record['last_used_node'])


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
    if 'infra_ports' in helperlink:
      flowsrc = helperlink['infra_ports'][0]
      flowdst = helperlink['infra_ports'][1]
    else:
      flowsrc = None
      flowdst = None
    reqlink = self.req[v1][v2][reqlid]
    bw = reqlink.bandwidth
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
      flowsrc.add_flowrule(match_str, action_str, bw)
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
        nffg.network[i][j][lidij].dst.add_flowrule(match_str, action_str, bw)

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
        flowsrc.add_flowrule(match_str, action_str, bw)

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
          match_str, action_str, bw)

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
          out_infra_port = nffg.network.node[host].add_port()
          # use the (copies of the) ports between the SGLinks to
          # connect the VNF to the Infra node.
          self.log.debug("Port %s added to Infra %s from NF %s" % (
            out_infra_port.id, host, vnf))
          # this is needed when an already mapped VNF is being reused from an 
          # earlier mapping, and the new SGHop's port only exists in the 
          # current request. WARNING: no function for Port object addition!
          if d.src not in mappednodenf.ports:
            mappednodenf.add_port(id = d.src.id, properties = d.src.properties)
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
          if d.dst not in mappednodenf.ports:
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
          nffg.add_sglink(nffg.network.node[sapstartid].ports[
               self._addSAPportIfNeeded(nffg, sapstartid, d.src.id)],
                          nffg.network.node[sapendid].ports[
               self._addSAPportIfNeeded(nffg, sapendid, d.dst.id)], 
                          id=d.id, flowclass=d.flowclass)
        else:
          nffg.add_sglink(nffg.network.node[sapstartid].ports[
               self._addSAPportIfNeeded(nffg, sapstartid, d.src.id)],
                          nffg.network.node[j].ports[d.dst.id], id=d.id,
                          flowclass=d.flowclass)
      elif self.req.node[j].type == 'SAP':
        sapendid = self.manager.getIdOfChainEnd_fromNetwork(j)
        nffg.add_sglink(nffg.network.node[i].ports[d.src.id],
                        nffg.network.node[sapendid].ports[
                          self._addSAPportIfNeeded(nffg, sapendid, d.dst.id)],
                        id=d.id, flowclass=d.flowclass)
      else:
        nffg.add_sglink(nffg.network.node[i].ports[d.src.id],
                        nffg.network.node[j].ports[d.dst.id], id=d.id,
                        flowclass=d.flowclass)
    return nffg


  def start (self):
    # breaking when there are no more BacktrackLevels forward, meaning the 
    # mapping is full. Or exception is thrown, when mapping can't be finished.
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
              raise
            else:
              c, sub, bt_record, link_bt_rec_list = \
                 self.bt_handler.getNextBacktrackRecordAndSubchainSubgraph([])
              for c_prime, prev_bt_rec, link_mapping_rec in link_bt_rec_list:
                if link_mapping_rec is not None:
                  self._resolveLinkMappingRecord(c_prime, link_mapping_rec)
                self._resolveBacktrackRecord(c_prime, prev_bt_rec)
              # use this bt_record to try another greedy step
              curr_vnf = bt_record['prev_vnf_id']
              next_vnf = bt_record['vnf_id']
              linkid = bt_record['reqlinkid']
              last_used_node = bt_record['last_used_node']

    # construct output NFFG with the mapping of VNFs and links
    return self.constructOutputNFFG()

  def reset (self):
    """Resets the CoreAlgorithm instance to its initial (after preprocessor) 
    and   state. Links weights are also calculated by the preprocessor, so those
    are reset too. self.original_chains is the list of input chains."""
    self._preproc(copy.deepcopy(self.net0), copy.deepcopy(self.req0),
                  self.original_chains)
