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
It maps end-to-end bandwidth requirements for links.

And divides the e2e chains to disjunct subchains for core mapping.
"""

import copy
from pprint import pformat

import networkx as nx

import UnifyExceptionTypes as uet
import Alg1_Helper as helper


class GraphPreprocessorClass(object):
  def __init__ (self, network0, req_graph0, chains0, manager0):
    self.network = network0
    self.req_graph = req_graph0
    self.chains = chains0
    self.log = helper.log.getChild(self.__class__.__name__)
    self.manager = manager0

    '''Indicates if we have already inserted a vnf in a subchain.
    At some state of the preprocessing,
    if a VNF is rechained, it means that VNF will already have a place,
    when we will be mapping (sub)chains with higher latency requirements.'''
    self.rechained = {}

    # If it has an edge i,j, this req. link is already included by a
    # subchain.
    self.link_rechained = nx.MultiDiGraph()

  def _findSubgraphForChain (self, chain):
    """
    Induced subgraph where for all node:
    dist(sap_begin)+dist(sap_end) =< chain['delay']
    Subgraphs are unwrapped from the NFFG class.
    """
    sap_begin = self.manager.getIdOfChainEnd_fromNetwork(chain['chain'][0])
    sap_end = self.manager.getIdOfChainEnd_fromNetwork(chain['chain'][-1])

    if sap_end == -1 or sap_begin == -1:
      raise uet.InternalAlgorithmException(
        "Called subgraph finding with one of the chain ends not yet mapped!")

    current = sap_begin
    pending = []
    visited = {sap_begin}
    dist = 0
    while dist <= chain['delay']:
      for n in self.net.network.neighbors_iter(current):
        if not (n in visited or n in pending):
          forwarding_latency = 0.0
          if self.net.network.node[n].type != 'SAP':
            forwarding_latency = self.net.network.node[n].resources['delay']
          if self.shortest_paths[n][sap_end] + dist + forwarding_latency <= \
               chain['delay']:
            self.log.debug("Node %s in sight with good distance" % n)
            pending.append(n)
      if len(pending) > 0:
        current = min(pending,
                      key=lambda m, paths=self.shortest_paths[sap_begin]: paths[
                        m])
        pending.remove(current)
        visited.add(current)
        dist = self.shortest_paths[sap_begin][current]
      else:
        break

    if sap_end not in visited:
      self.log.error(
        "Chain end is further than latency requirement, for chain: %s" % chain)
      raise uet.MappingException(
        "Chain end is further than latency requirement, for chain: %s" % chain)

    # attributes of nx::subgraph() points to the original, better call copy()
    # -DON`T we want attribute changes to be reflected in the big
    #  common graph.
    subg = self.net.network.subgraph(visited)
    self.log.debug("Subgraph returned: %s" % subg.edges(keys=True))
    return subg

  def _colorLinksAndVNFs (self, e2e_w_graph, not_e2e):
    """Those VNFs/links have the same color which are involved in the
    same set of chains.
    TODO: involve not E2E chains (even when not part of an e2e chain) in
    coloring and subgraph finding correctly. """
    chains = []  # instead of chains = not_e2e
    for c, sub in e2e_w_graph:
      chains.append(c)

    colored_req = nx.MultiDiGraph()
    for vnf in self.req_graph.network.nodes_iter():
      colored_req.add_node(vnf, color=set())
    for i, j, k in self.req_graph.network.edges_iter(keys=True):
      colored_req.add_edge(i, j, key=k, color=set())

    for c in chains:
      colored_req.node[c['chain'][0]]['color'].add(c['id'])
      for i, j, k in zip(c['chain'][:-1], c['chain'][1:], c['link_ids']):
        colored_req.node[j]['color'].add(c['id'])
        colored_req[i][j][k]['color'].add(c['id'])

    '''From now on the color mustn`t be modified,
    is converting to frozenset too resourceful?'''
    for vnf in colored_req.nodes_iter():
      colored_req.node[vnf]['color'] = frozenset(colored_req.node[vnf]['color'])
    for i, j, k in colored_req.edges_iter(keys=True):
      colored_req[i][j][k]['color'] = frozenset(colored_req[i][j][k]['color'])

    for i, j, k, d in colored_req.edges_iter(data=True, keys=True):
      if len(d['color']) == 0:
        # TODO: proper handling of these links and not E2E chains
        # not contained by E2E chains.
        raise uet.BadInputException(
          "All request edges should be included in some E2E chains - at least "
          "in this version Request link %s, %s, id: %s is not in any SAP-SAP "
          "chain" % (i, j, k))

    return colored_req

  def _getIntersectionOfSubgraphs_by_ChainIds (self, chain_ids,
       chains_w_graphs):
    """
    Returns an intersection of all graphs corresponding to
    the given list of chain ids.
    Subgraph intersections are unwrapped from the NFFG class
    """
    intersect = self.net.network.copy()
    for c, g in chains_w_graphs:
      if c['id'] in chain_ids:
        intersect.remove_nodes_from(
          n for n in intersect.nodes_iter() if n not in g)
    '''We want only the graph structure to be copied, the attributes
    shall point to the original ones. Set the references back to the
    PREPROCESSED NETWORK wich`s attributes will be updated during mapping
    NOTE:values are not changed in this stage.'''
    for i, j, k in intersect.edges_iter(keys=True):
      intersect[i][j][k] = self.net.network[i][j][k]
    for n in intersect.nodes_iter():
      intersect.node[n] = self.net.network.node[n]

    return intersect

  def _getNextIdOfSubchain (self, curr_vnf, act_color, colored_req, path):
    for curr, j, k, d in colored_req.out_edges_iter([curr_vnf], data=True,
                                                    keys=True):
      if j in path:
        continue
      # comparing hash values is maybe faster
      if hash(d['color']) == hash(act_color):
        return j, k
    return None, None

  def _findOneSubchain (self, start, act_color, colored_req, e2e_w_graph):
    subc_path = []
    link_ids = []
    subc = {}

    subc_path.append(start)
    next_vnf, linkid = self._getNextIdOfSubchain(start, act_color, colored_req,
                                                 subc_path)
    if next_vnf is None:
      self.log.error(
        "Subchain with color %s cannot consist of only one VNF: %s" % (
          act_color, start))
      raise uet.InternalAlgorithmException(
        "Subchain with color %s cannot consist of only one VNF: %s" % (
          act_color, start))
    while next_vnf is not None:
      subc_path.append(next_vnf)
      link_ids.append(linkid)
      if not self.rechained[next_vnf]:
        self.rechained[next_vnf] = True
        if hash(colored_req.node[next_vnf]['color']) != hash(act_color):
          subg_intersect = self._getIntersectionOfSubgraphs_by_ChainIds(
            colored_req.node[next_vnf]['color'], e2e_w_graph).nodes()
          current_place_crit = self.req_graph.network.node[
            next_vnf].placement_criteria
          if len(current_place_crit) > 0:
            new_place_crit = [n for n in subg_intersect if
                              n in current_place_crit]
            if len(new_place_crit) == 0:
              raise uet.MappingException(
                "Given and internal placement criteria has no intersection.")
            self.req_graph.network.node[
              next_vnf].placement_criteria = new_place_crit
          else:
            self.req_graph.network.node[
              next_vnf].placement_criteria = subg_intersect

        curr_vnf = next_vnf
        next_vnf, linkid = self._getNextIdOfSubchain(curr_vnf, act_color,
                                                     colored_req, subc_path)
      else:
        break

    # Put the chain together and append to output.
    subc['chain'] = subc_path
    subg = self._getIntersectionOfSubgraphs_by_ChainIds(act_color, e2e_w_graph)
    subc['link_ids'] = link_ids

    self.max_chain_id += 1
    subc['id'] = self.max_chain_id

    self.log.debug(
      "Subchain added: %s \n with subgraph: %s" % (subc, subg.edges()))

    for i, j, k in zip(subc_path[:-1], subc_path[1:], link_ids):
      self.link_rechained.add_edge(i, j, key=k)

    self.manager.addChain_SubChainDependency(subc['id'], act_color, subc_path,
                                             link_ids)

    return subc, subg

  def _compareSubchainSubgraphTuples (self, a, b, use_latency=True):
    x = a[0]['chain'][0] in b[0]['chain']
    y = b[0]['chain'][0] in a[0]['chain']
    # != is XOR
    if x != y:
      # in this case one of them is bigger based on predecessor criteria
      if x:
        # means first element of A is in B, so B is lower
        return 1
      else:
        # means first element of B is in A, so A is lower
        return -1
    elif use_latency:
      # they are considered equal based on predecessor criteria
      alat = self.manager.getLocalAllowedLatency(a[0]['id'])
      blat = self.manager.getLocalAllowedLatency(b[0]['id'])
      if alat < blat:
        # A is stricter, should be lower
        return -1
      elif alat > blat:
        return 1
      else:
        return 0
    else:
      return 0

  def _divideIntoDisjointSubchains (self, e2e_w_graph, not_e2e):
    """e2e is a list of tuples of SAP-SAP chains and corresponding subgraphs.
    not_e2e is a list of chains. Returns (subchain, subgraph) list of tuples,
    in the order those should be mapped."""

    colored_req = self._colorLinksAndVNFs(e2e_w_graph, not_e2e)
    output = []

    '''It is important to start with a chain with the most strict
    latency req. They are the most difficult to map, because they have
    fewer possible hosts in their corresponding subgraph.'''
    e2e_sorted = sorted([t[0] for t in e2e_w_graph], key=lambda c: c['delay'])

    rechaining_cycles = 0
    while colored_req.number_of_edges() != 0:
      e2e = e2e_sorted[rechaining_cycles % len(e2e_sorted)]
      vnfs_sorted_by_degree = sorted(
        [tup for tup in colored_req.out_degree_iter() if tup[1] != 0],
        key=lambda t: t[1])
      '''TODO: maybe delete sometimes the vnfs with 0 deg? '''
      rechaining_cycles += 1
      for vnf, deg in vnfs_sorted_by_degree:

        # Check if there is a neighbor where we can start looking for
        # subchain
        act_color = frozenset([])
        for currnode, j, k, d in colored_req.out_edges_iter([vnf], data=True,
                                                            keys=True):
          if e2e['id'] in d['color'] and not self.link_rechained.has_edge(vnf,
                                                                          j,
                                                                          key=k):
            act_color = d['color']
            break
          else:
            continue

        if len(act_color) > 0 and self.rechained[vnf]:
          subc_subg = self._findOneSubchain(vnf, act_color, colored_req,
                                            e2e_w_graph)
          output.append(subc_subg)
          for i, j, k in zip(subc_subg[0]['chain'][:-1],
                             subc_subg[0]['chain'][1:],
                             subc_subg[0]['link_ids']):
            '''We could also sort VNFs by the number of "unrechained"
            neighbors. Less cumbersome this way.'''
            try:
              colored_req.remove_edge(i, j, k)
            except nx.NetworkXError as e:
              raise uet.InternalAlgorithmException(
                "Mistake in  colored request graph maintenance, error: %s" % e)
          break

    '''TODO: Zero edges in colored_req doesn`t mean all links are mapped!!
    WHY? WHY SO SLOW??
    - is this still a problem? (isn`t it resolved by the possible multiple
    iterations on the e2e_sorted?)
    TODO: if there is a chain which is not E2E and not part of any E2E chain,
    then is the previous `while` an infinite loop?'''
    if not reduce(lambda a, b: a and b, self.rechained.values()):
      self.log.critical("There is a VNF, which is not in any subchain!!")
      raise uet.InternalAlgorithmException(
        "There is a VNF, which is not in any subchain!!")
    if not reduce(lambda a, b: a and b,
                  [self.link_rechained.has_edge(i, j, key=k) for i, j, k in
                   self.req_graph.network.edges_iter(keys=True)]):
      self.log.critical("There is a link, which is not in any subchain!!")
      raise uet.InternalAlgorithmException(
        "There is a link, which is not in any subchain!!")

    '''TODO: Test with more complicated req_graph - IN PROGRESS'''

    # sort the subchains in predecessor order and secondly latency req order
    # - Does it make the earlier latency sorting unnecessary?
    # - No, because this way lower latency requirement chains are
    # prioritized to being cut into less number of  peaces, so they are
    # guaranteed to be mapped in bigger peaces, maybe still not enough reason
    starting_subchains = [c for c in output if self.req_graph.network.node[
      c[0]['chain'][0]].type == 'SAP']
    output = [c for c in output if c not in starting_subchains]
    sorted_output = sorted(starting_subchains,
                           cmp=self._compareSubchainSubgraphTuples)
    while len(output) != 0:
      next_subchains = [c for c in output if reduce(lambda a, b: a or b, [
        self._compareSubchainSubgraphTuples(d, c, use_latency=False) == -1 for d
        in sorted_output])]
      output = [c for c in output if c not in next_subchains]
      sorted_output.extend(
        sorted(next_subchains, cmp=self._compareSubchainSubgraphTuples))

    return sorted_output

  def processRequest (self, preprocessed_network):
    """
    Translates the e2e bandwidth reqs to links, and chains to subchains,
    additionally finds subgraph for subchains.
    Removes the unneeded nodes and edges from the service graph.
    """
    e2e_chains_with_graphs = []
    not_e2e_chains = []
    # The parameter is needed to indicate the required order of
    # calling processReq and processNet
    # must be the same that processNetwork() returned.
    self.net = preprocessed_network

    # we want only the service graph
    for n in self.req_graph.infras:
      # DYNAMIC and STATIC links should be removed by this.
      # SG links should be already processed to chains, and link reqs.
      # WARNING: the ports of the VNFs which were connecting to the
      # host Infra node will remain in the NFFG.
      self.req_graph.del_node(n.id)

    for i, j, k, d in self.req_graph.network.edges_iter(data=True, keys=True):
      if d.type != 'SG':
        raise uet.BadInputException(
          "After removing the infras, only the service graph should remain.",
          "Link %s between nodes %s and %s is a %s link" % (k, i, j, d.type))

    # SAPs are already reachained by the manager, based on their names.
    for vnf, data in self.req_graph.network.nodes_iter(data=True):
      if data.type == 'SAP':
        self.rechained[vnf] = True
      elif data.type == 'NF':
        self.rechained[vnf] = False
      else:
        raise uet.BadInputException(
          "After preprocessing stage, only SAPs or VNFs should be in the "
          "request graph. Node %s, type: %s is still in the graph" % (
            vnf, data.type))

    self.max_chain_id = max(c['id'] for c in self.chains)
    self.manager.setMaxInputChainId(self.max_chain_id)

    """Placement criteria is a list of physical nodes, where the VNF
    can be placed. It can be also specified by the upper layer, and the
    preprocessing procedure"""
    for vnf in self.req_graph.network.nodes_iter():
      if not hasattr(self.req_graph.network.node[vnf], 'placement_criteria'):
        setattr(self.req_graph.network.node[vnf], 'placement_criteria', [])

    for chain in self.chains:
      node_path = chain['chain']
      link_ids = chain['link_ids']

      # Bandwidth of the chains are summed up on the links.
      for i, j, k in zip(node_path[:-1], node_path[1:], link_ids):
        if hasattr(self.req_graph.network[i][j][k], 'bandwidth'):
          self.req_graph.network[i][j][k].bandwidth += chain['bandwidth']
        else:
          setattr(self.req_graph.network[i][j][k], 'bandwidth',
                  chain['bandwidth'])

      # Find separate subgraph only for e2e chains from the upper layer.
      if self.req_graph.network.node[node_path[0]].type == 'SAP' and \
                self.req_graph.network.node[node_path[-1]].type == 'SAP':
        subg = self._findSubgraphForChain(chain)
        e2e_chains_with_graphs.append((chain, subg))
      else:
        '''not SAP-SAP chains will be mapped to some (intersections of)
        subgraphs found to e2e chains'''
        not_e2e_chains.append(chain)
      self.log.info("Chain %s preprocessed" % chain)
    if len(e2e_chains_with_graphs) == 0:
      self.log.error("No SAP - SAP chain was given!")
      raise uet.BadInputException(
        "Request with SAP-to-SAP chains. Service chains do not contain any "
        "SAP-to-SAP chain")

    '''These chains are disjoint on the set of links, each has a subgraph
    which it should be mapped to.'''
    divided_chains_with_graphs = self._divideIntoDisjointSubchains(
      e2e_chains_with_graphs, not_e2e_chains)

    '''After the request graph is divided, the latency and bw reqs of the
    divided chains are not valid! because those corresponds to the e2e
    chains. Handling this correctly is done by the MappingManager.'''

    return self.req_graph, divided_chains_with_graphs

  def processNetwork (self):
    """
    Computes link weights. Removes mapped VNFs from the substrate
    network, and calculates the available resources of the Infra node,
    which is running the VNFs. This also removes all the NOT SATATIC links
    from the network.
    Calculates shortest paths on the infrastructure, weighted by latency.
    """
    net = copy.deepcopy(self.network)

    # add available res attribute to all Infras and subtract the running
    # NFs` resources from the given max res
    for n in net.infras:
      setattr(net.network.node[n.id], 'availres',
              copy.deepcopy(net.network.node[n.id].resources))
      for vnf in net.running_nfs(n.id):
        # TODO:
        # we should also know how many links are mapped, now we subtract
        # only the VNF`s internal bandwidth requirement from the infra`s
        # bandwidth capacity
        newres = helper.subtractNodeRes(net.network.node[n.id].availres,
                                        net.network.node[vnf.id].resources)
        if newres is None:
          raise uet.BadInputException(
            "Infra node`s resources are expected to represent its maximal "
            "capabilities. The NodeNF(s) running on Infra node %s, use(s) more "
            "resource than the maximal." % n.name)
        else:
          net.network.node[n.id].availres = newres
          # WARNING: by deleting the VNFs the dynamic links` end port
          # in the Infra node, remains in the NFFG structure.
          net.del_node(vnf.id)

    for i, j, k in net.network.edges_iter(keys=True):
      if net.network[i][j][k].type != 'STATIC':
        # meaning there is a Dynamic, SG or Requirement link left
        raise uet.BadInputException(
          "After removing the NodeNFs from the substrate NFFG, "
          "there shouldn`t be DYNAMIC, SG or REQUIREMENT links left in "
          "the network. Link %s between nodes %s and %s is  a %s link" % (
            k, i, j, net.network[i][j][k].type))
    for n in net.nfs:
      raise uet.BadInputException(
        "NodeNF %s couldn`t be removed from the NFFG" % net.network.node[n].id,
        "This NodeNF probably isn`t mapped anywhere")

    self.shortest_paths = helper.shortestPathsInLatency(net.network)
    self.manager.addShortestRoutesInLatency(self.shortest_paths)
    self.log.debug(
      "Initial shortest_paths (in ms): %s" % pformat(self.shortest_paths))

    # calculate edge weights, we can call edges_iter, cuz there shouldn`t be
    # any NFs and dynamic links left.
    # TODO:
    # WARNING: IF the reported bandwidth on links are their maximal capacity,
    # the running traffic`s capacity should be subtracted, BUT we don`t know
    # yet how do the flow classes look like, SO for now let`s suppose
    # bandwidth and availbandwidth are the same initially
    for i, j, k, d in net.network.edges_iter(data=True, keys=True):
      setattr(net.network[i][j][k], 'availbandwidth', d.bandwidth)
      setattr(net.network[i][j][k], 'weight', 1.0 / d.bandwidth)
      self.log.debug("Weight for link %s, %s, %s: %f" % (
        i, j, k, net.network[i][j][k].weight))

    for n, d in net.network.nodes_iter(data=True):
      if d.type != 'SAP':
        net.network.node[n].weight = 1.0 / d.resources['bandwidth']
        self.log.debug(
          "Weight for node %s: %f" % (n, net.network.node[n].weight))
    self.log.info("Link and node weights calculated")
    return net
