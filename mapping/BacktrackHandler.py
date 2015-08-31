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

from collections import deque

import UnifyExceptionTypes as uet
from Alg1_Helper import log

class BacktrackHandler(object):
  """
  Manages a backtrack tree of the mapping process. All mapping exceptions shall
  be catched in the core process, and the appropriate backtrack and network 
  resource state restore function should be called.
  """

  def __init__(self, subchains_with_subgraphs, branching_factor, 
               bt_limit):
    """
    Initiates the backtrack structure, which is a deque of deques. Maxlen
    of the outer queue is bt_limit.
    bt_struct consists of 2-tuples of:
        subchain_id
      AND a dictionaries with keys (which is a bt_record): 
        prev_vnf_id, vnf_id, reqlinkid, 
        target_infra (where vnf_id is to be mapped), 
        last_used_node (where prev_vnf_id was mapped), path, path_link_ids,
        bw_req, used_latency, obj_func_value (evaluated objective funtion value
        for this mapping)
    Elements to deques are added (with append) to the right, and shifted out 
    to the left if more than maxlen would be inside.
    """
    self.log = log
    self.log = log.getChild(self.__class__.__name__)
    self.branching_factor = branching_factor
    self.bt_struct = deque(maxlen = bt_limit)
    self.subchains_with_subgraphs = subchains_with_subgraphs
    self.current_subchain_level = 0
    self.vnf_index_in_subchain = 0
    
  def moveOneBacktrackLevelForward(self):
    """
    """
    if self.current_subchain_level < len(self.subchains_with_subgraphs):
      subchain = self.subchains_with_subgraphs[self.current_subchain_level][0]
      if self.vnf_index_in_subchain < len(subchain['chain']) - 1:
        subgraph = self.subchains_with_subgraphs[self.current_subchain_level][1]
      else: 
        self.current_subchain_level += 1
        self.vnf_index_in_subchain = 0
        if self.current_subchain_level < len(self.subchains_with_subgraphs):
          subchain = self.subchains_with_subgraphs[self.current_subchain_level][0]
          subgraph = self.subchains_with_subgraphs[self.current_subchain_level][1]
        else:
          return None
      self.vnf_index_in_subchain += 1
      # if self.vnf_index_in_subchain >= len(subchain['chain']) - 1:
      #  self.vnf_index_in_subchain = len(subchain['chain']) - 2
      # return c, sub, curr_vnf, next_vnf, linkid
      return subchain, subgraph, \
          subchain['chain'][self.vnf_index_in_subchain - 1],\
          subchain['chain'][self.vnf_index_in_subchain], \
          subchain['link_ids'][self.vnf_index_in_subchain - 1]
    else:
      return None

  def addBacktrackLevel(self, subchain_id, possible_hosts_of_a_vnf):
    """
    Adds the deque of maxlen braching_factor to the backtrack structure, 
    with the possible data of one VNF,reqlink - host,path mapping.
    Plus remembers that this backtrack level (VNF,reqlink mapping) is a part 
    of which subchain by remembering the index of the subchain-subgraph 
    structure.
    """
    if self.subchains_with_subgraphs[self.current_subchain_level][0]['id'] \
       == subchain_id:
      self.bt_struct.append((self.current_subchain_level, 
                             possible_hosts_of_a_vnf))
      try:
          tmp = possible_hosts_of_a_vnf.pop()
          possible_hosts_of_a_vnf.append(tmp)
          self.log.debug("Backtrack level added with chain %s and VNF %s."%
                         (subchain_id, tmp['vnf_id']))
      except IndexError:
          pass
    else:
      raise uet.InternalAlgorithmException("Backtrack structure maintenance"
      "error: current_subchain_level is ambiguous during addBacktrackLevel!")

  def addLinkMappingRecord(self, subchain_id, bw_req, path, linkids, used_lat,
                           vnf1, vnf2, reqlinkid):
    """
    Adds an internal level between two BacktrackLevels indicating a mapping of 
    last link of a chain. If we want to store multiple possible paths for a 
    request link, the hidden backtracking step could update the path where the 
    backtracking happened (because the path feasibilities has already been 
    checked by _mapOneRequestLink()
    """
    if self.subchains_with_subgraphs[self.current_subchain_level][0]['id'] \
       == subchain_id:
      self.bt_struct.append((self.current_subchain_level, 
                             {'bw_req': bw_req, 'path': path, 
                              'linkids': linkids, 'used_lat': used_lat,
                              'vnf1': vnf1, 'vnf2': vnf2, 
                              'reqlinkid': reqlinkid,
                              'link_mapping_record': True}))
    else:
      raise uet.InternalAlgorithmException("Backtrack structure maintenance"
      "error: current_subchain_level is ambiguous during addLinkMappingRecord!")
  
  def getNextBacktrackRecordAndSubchainSubgraph(self):
    """
    Either returns a backtrack record where the mapping process can continue, 
    or raised a real, seroius MappingException, when mapping can't be continued.
    This is the actual backstepping. Should be called after catching a 
    MappingException indicating the need for backstep.
    """
    record = None
    try:
      record = self.bt_struct.pop()
      self.bt_struct.append(record)
    except IndexError:
      raise uet.MappingException("Backtrack limit reached, no further mapping"
                                 "possibilities are available", 
                                 backtrack_possible = False)
    try:
      tmp_subchain_level, possible_hosts_of_a_vnf = record
      if 0 <= self.current_subchain_level - tmp_subchain_level <= 1:
        # current_subchain_level can only stay, or decrease
        self.current_subchain_level = tmp_subchain_level
        bt_record = possible_hosts_of_a_vnf.pop()
        self.log.debug("Stepping back on VNF %s of subchain %s."%
                       (bt_record['vnf_id'], tmp_subchain_level))
        # return c, sub, bt_record
        return self.subchains_with_subgraphs[self.current_subchain_level][0],\
          self.subchains_with_subgraphs[self.current_subchain_level][1], \
          bt_record
      else:
        raise uet.InternalAlgorithmException("Backtrack structure maintenance"
                                      "error: backtrack step went wrong.")
    except IndexError:
      self.bt_struct.pop() # remove empty deque of possible mappings ('record')
      self.vnf_index_in_subchain -= 1
      return self.getNextBacktrackRecordAndSubchainSubgraph()
