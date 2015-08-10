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

from collections import defaultdict
import sys
import logging

import networkx as nx

import UnifyExceptionTypes as uet



# these are needed for the modified NetworkX functions.
from heapq import heappush, heappop
from itertools import count

loglevel = 'DEBUG'
loghandler = logging.StreamHandler()
logformat = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
loghandler.setFormatter(logformat)

log = logging.getLogger("mapping")


def subtractNodeRes (current, substrahend, link_count=1):
  """
  Subtracts the subtrahend nffg_elements.NodeResource object from the current.
  Note: only delay component is not subtracted, for now we neglect the load`s
  inluence on the delay. Link count identifies how many times the bandwidth
  should be subtracted. Returns None if any of the components are smaller
  than the appropriate component of the substrahend.
  """
  attrlist = ['cpu', 'mem', 'storage', 'bandwidth']  # delay excepted!
  if reduce(lambda a, b: a or b, (current[attr] == None for attr in attrlist)):
    raise uet.BadInputException(
      "Node resource components should always " + "be given",
      "One of %s`s components is None" % str(current))
  if reduce(lambda a, b: a or b,
            (current[attr] < substrahend[attr] for attr in attrlist if
             attr != 'bandwidth' and substrahend[attr] is not None)):
    return None
  if substrahend['bandwidth'] is not None:
    if current['bandwidth'] < link_count * substrahend['bandwidth']:
      return None
  for attr in attrlist:
    k = 1
    if attr == 'bandwidth':
      k = link_count
    if substrahend[attr] is not None:
      current[attr] -= k * substrahend[attr]
  return current


def shortestPathsInLatency (G):
  """Wrapper function for Floyd`s algorithm to calculate shortest paths
  measured in latency, using also nodes` forwarding latencies.
  Modified source code taken from NetworkX library.
  """
  # dictionary-of-dictionaries representation for dist and pred
  # use some defaultdict magick here
  # for dist the default is the floating point inf value
  dist = defaultdict(lambda: defaultdict(lambda: float('inf')))
  for u in G:
    dist[u][u] = 0
  # initialize path distance dictionary to be the adjacency matrix
  # also set the distance to self to 0 (zero diagonal)
  try:
    for u, v, d in G.edges(data=True):
      e_weight = d.delay
      dist[u][v] = min(e_weight, dist[u][v])
  except KeyError as e:
    raise uet.BadInputException("Edge attribure(s) missing " + str(e),
                                "{'delay': VALUE}")
  try:
    for w in G:
      if G.node[w].type != 'SAP':
        for u in G:
          for v in G:
            if dist[u][v] > dist[u][w] + G.node[w].resources['delay'] + dist[w][
              v]:
              dist[u][v] = dist[u][w] + G.node[w].resources['delay'] + dist[w][
                v]
  except KeyError as e:
    raise uet.BadInputException("Node attribure missing " + str(e),
                                "{'delay': VALUE}")

  return dict(dist)


def shortestPathsBasedOnEdgeWeight (G, source, target=None, cutoff=None):
  '''Taken and modified from NetworkX source code,
  the function originally 'was single_source_dijkstra',
  now it returns the key edge data too.
  '''
  if source == target:
    return ({source: [source]}, {source: []})
  push = heappush
  pop = heappop
  dist = {}  # dictionary of final distances
  paths = {source: [source]}  # dictionary of paths
  # dictionary of edge key lists of corresponding paths
  edgekeys = {source: []}
  seen = {source: 0}
  c = count()
  fringe = []  # use heapq with (distance,label) tuples
  push(fringe, (getattr(G.node[source], 'weight', 0), next(c), source))
  while fringe:
    (d, _, v) = pop(fringe)
    if v in dist:
      continue  # already searched this node.
    dist[v] = d
    if v == target:
      break
    # for ignore,w,edgedata in G.edges_iter(v,data=True):
    # is about 30% slower than the following
    edata = []
    for w, keydata in G[v].items():
      minweight, edgekey = min(((dd.weight, k) for k, dd in keydata.items()),
                               key=lambda t: t[0])
      edata.append((w, edgekey, {'weight': minweight}))

    for w, ekey, edgedata in edata:
      vw_dist = dist[v] + getattr(G.node[w], 'weight', 0) + edgedata['weight']
      if cutoff is not None:
        if vw_dist > cutoff:
          continue
      if w in dist:
        if vw_dist < dist[w]:
          raise ValueError('Contradictory paths found:', 'negative weights?')
      elif w not in seen or vw_dist < seen[w]:
        seen[w] = vw_dist
        push(fringe, (vw_dist, next(c), w))
        paths[w] = paths[v] + [w]
        edgekeys[w] = edgekeys[v] + [ekey]
  return (paths, edgekeys)


class MappingManager(object):
  '''Administrates the mapping of links and VNFs
  TODO: Connect subchain and chain requirements, controls dynamic objective
  function parameterization based on where the mapping process is in an
  (E2E) chain.
  TODO: Could handle backtrack functionality, if other possible mappings
  are also given (to some different structure)'''

  def __init__ (self, net, req, chains):
    self.log = log.getChild(self.__class__.__name__)
    # list of tuples of mapping (vnf_id, node_id)
    self.vnf_mapping = []
    # SAP mapping can be done here based on their names
    try:
      for vnf, dv in req.network.nodes_iter(data=True):
        if dv.type == 'SAP':
          sapname = dv.name
          sapfound = False
          for n, dn in net.network.nodes_iter(data=True):
            if dn.type == 'SAP':
              if dn.name == sapname:
                self.vnf_mapping.append((vnf, n))
                sapfound = True
                break
          if not sapfound:
            self.log.error("No SAP found in network with name: %s" % sapname)
            raise uet.MappingException(
              "No SAP found in network " + "with name: %s. SAPs are mapped "
                                           "exclusively by their names." %
              sapname)
    except AttributeError as e:
      raise uet.BadInputException("Node data with name %s" % str(e),
                                  "Node data not found")

    # same graph structure as the request, edge data stores the mapped path
    self.link_mapping = nx.MultiDiGraph()

    # bandwidth is not yet summed up on the links
    # AND possible Infra nodes and DYNAMIC links are not removed
    self.req = req
    # all chains are included, not only SAP-to-SAPs
    self.chains = chains

    # chain - subchain pairing, stored in a bipartie graph
    self.chain_subchain = nx.Graph()
    self.chain_subchain.add_nodes_from(
      (c['id'], {'avail_latency': c['delay']}) for c in chains)

  def getIdOfChainEnd_fromNetwork (self, _id):
    """
    SAPs are mapped by their name, NOT by thier ID in the network/request
    graphs. If the chain is between VNFs, those must be already mapped.
    Input is an ID from the request graph. Return -1 if the node is not
    mapped.
    """
    ret = -1
    for v, n in self.vnf_mapping:
      if v == _id:
        ret = n
        break
    return ret

  def addChain_SubChainDependency (self, subcid, chainids, subc, link_ids):
    '''Adds a link between a subchain id and all the chain ids that are
    contained subcid. Maybe_sap is the first element of the subchain,
    if it is a SAP add its network pair to last_used_host attribute.
    (at this stage, only SAPs are inside the vnf_mapping list)
    'subchain' is a list of (vnf1,vnf2,linkid) tuples where the subchain
    goes.
    '''
    # TODO: not E2E chains are also in self.chains, but we don`t find
    # subchains for them, so their latency is not checked, the not E2E
    # chain nodes in this graph always stay the same so far.
    self.chain_subchain.add_node(subcid,
                                 last_used_host=self.getIdOfChainEnd_fromNetwork(
                                   subc[0]),
                                 subchain=zip(subc[:-1], subc[1:], link_ids))
    for cid in chainids:
      if cid not in {c['id'] for c in self.chains}:
        raise uet.InternalAlgorithmException(
          "Invalid chain identifier" + "given to MappingManager!")
      else:
        self.chain_subchain.add_edge(cid, subcid)

  def getLocalAllowedLatency (self, subchain_id, vnf1=None, vnf2=None,
       linkid=None):
    """
    Checks all sources/types of latency requirement, and identifies
    which is the strictest. The smallest 'maximal allowed latency' will be
    the strictest one. We cannot use paths with higher latency value than
    this one.
    The request link is ordered vnf1, vnf2. This reqlink is part of
    subchain_id subchain.
    This function should only be called on SG links.
    """
    # if there is latency requirement on a request link
    link_maxlat = sys.float_info.max
    if vnf1 is not None and vnf2 is not None and linkid is not None:
      if self.req.network[vnf1][vnf2][linkid].type != 'SG':
        raise uet.InternalAlgorithmException(
          "getLocalAllowedLatency " + "function should only be called on SG "
                                      "links!")
      if hasattr(self.req.network[vnf1][vnf2][linkid], 'delay'):
        link_maxlat = self.req.network[vnf1][vnf2][linkid].delay
    try:
      # find the strictest chain latency which applies to this link
      chain_maxlat = sys.float_info.max
      for c in self.chain_subchain.neighbors_iter(subchain_id):
        if c > self.max_input_chainid:
          raise uet.InternalAlgorithmException("Subchain-subchain" \
                                               "connection is not allowed in " \
                                               "chain-subchain bipartie graph!")
        elif self.chain_subchain.node[c]['avail_latency'] < chain_maxlat:
          chain_maxlat = self.chain_subchain.node[c]['avail_latency']

      return min(chain_maxlat, link_maxlat)

    except KeyError as e:
      raise uet.InternalAlgorithmException(
        "Bad construction of chain-" % "subchain bipartie graph!")

  def isVNFMappingDistanceGood (self, vnf1, vnf2, n1, n2):
    """
    Mapping vnf2 to n2 shouldn`t be further from n1 (vnf1`s host) than
    the strictest latency requirement of all the links between vnf1 and vnf2
    """
    max_permitted_vnf_dist = sys.float_info.max
    for i, j, linkid, d in self.req.network.edges_iter([vnf1], data=True,
                                                       keys=True):
      if self.req.network[i][j][linkid].type != 'SG':
        self.log.warn(
          "There is a not SG link left in the Service " + "Graph, but now it "
                                                          "didn`t cause a "
                                                          "problem.")
        continue
      if j == vnf2:
        # i,j are always vnf1,vnf2
        for c, chdata in self.chain_subchain.nodes_iter(data=True):
          if 'subchain' in chdata.keys():
            if (vnf1, vnf2, linkid) in chdata['subchain']:
              # there is only one subchain which contains this
              # reqlink. (link -> chain mapping is not necessary
              # anywhere else, a structure only for realizing this
              # checking effectively seems not useful enough)
              lal = self.getLocalAllowedLatency(c, vnf1, vnf2, linkid)
              if lal < max_permitted_vnf_dist:
                max_permitted_vnf_dist = lal
              break
    if self.shortest_paths_lengths[n1][n2] > max_permitted_vnf_dist:
      return False
    else:
      return True

  def updateChainLatencyInfo (self, subchain_id, used_lat, last_used_host):
    '''Updates how much latency does the mapping process has left which
    applies for this subchain.
    '''
    for c in self.chain_subchain.neighbors_iter(subchain_id):
      # feasability already checked by the core algorithm
      self.chain_subchain.node[c]['avail_latency'] -= used_lat
    self.chain_subchain.node[subchain_id]['last_used_host'] = last_used_host

  def addShortestRoutesInLatency (self, sp):
    '''Shortest paths are between physical nodes. These are needed to
    estimate the importance of laltency in the objective function.
    '''
    self.shortest_paths_lengths = sp

  def setMaxInputChainId (self, maxcid):
    '''Sets the maximal chain ID given bt the user. Every chain with lower
    ID-s are given by the user, higher ID-s are subchains generated by
    the preprocessor.
    '''
    self.max_input_chainid = maxcid
