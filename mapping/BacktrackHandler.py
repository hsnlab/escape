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
    bt_struct consists of 3-tuples of:
        subchain_id
      AND a dictionaries with keys (which is a bt_record): 
        prev_vnf_id, vnf_id, reqlinkid, 
        target_infra (where vnf_id is to be mapped), 
        last_used_node (where prev_vnf_id was mapped), path, path_link_ids,
        bw_req, used_latency, obj_func_value (evaluated objective funtion value
        for this mapping)
      AND a link_mapping_record dictionary if this VNF is the last of the 
      subchain. otherwise, this dict is None
    Elements to deques are added (with append) to the right, and shifted out 
    to the left if more than maxlen would be inside.
    """
    self.log = log
    self.log = log.getChild(self.__class__.__name__)
    self.branching_factor = branching_factor
    self.bt_struct = deque(maxlen = bt_limit)
    self.currently_mapped = deque()
    self.subchains_with_subgraphs = subchains_with_subgraphs
    self.current_subchain_level = 0
    self.vnf_index_in_subchain = 0
    # the number of subchain which made us fail (induced the deepest backtrack)
    self.failer_subchain_count = 1

  def moveOneBacktrackLevelForward(self, ready_for_next_subchain):
    """
    Handles the back or forward stepping on subchains and their VNFs.
    """
    if self.current_subchain_level < len(self.subchains_with_subgraphs):
      """
      MAYBE this checking is not necessary anymore since we correctly handle the
      LinkMappingRecords during backtracking
      if len(self.currently_mapped) > 0:
        tmp_mapping_rec = self.currently_mapped.pop()
        self.currently_mapped.append(tmp_mapping_rec)
        if self.vnf_index_in_subchain == len(subchain['chain']) - 1 and \
           tmp_mapping_rec[2] is None or \
           tmp_mapping_rec[1] is not None and \
           tmp_mapping_rec[1]['vnf_id'] != \
               subchain['chain'][self.vnf_index_in_subchain] and \
           tmp_mapping_rec[2] is None:
          # this means the last link or vnf of the chain is not mapped yet, 
          # but the backtrack procedure would continue on next chain (can happen
          # when we step back on the last link of a subchain)
          self.vnf_index_in_subchain -= 1
      """
      if not ready_for_next_subchain:
        subgraph = self.subchains_with_subgraphs[self.current_subchain_level][1]
        subchain = self.subchains_with_subgraphs[self.current_subchain_level][0]
      else: 
        self.current_subchain_level += 1
        self.vnf_index_in_subchain = 0
        if self.current_subchain_level < len(self.subchains_with_subgraphs):
          subchain = self.subchains_with_subgraphs[self.current_subchain_level][0]
          subgraph = self.subchains_with_subgraphs[self.current_subchain_level][1]
          self.log.info("Starting to map next subchain: %s"%subchain['chain'])
        else:
          return None
      self.vnf_index_in_subchain += 1
      # maintain peak subchain counter.
      if self.current_subchain_level + 1 > self.failer_subchain_count:
        self.failer_subchain_count = self.current_subchain_level + 1 
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
      
  def _handleOneLinkLongSubchainFromSAP(self, link_mapping_rec):
    self.currently_mapped.append((self.subchains_with_subgraphs[\
                                  self.current_subchain_level][0],
                                  None,
                                  link_mapping_rec,
                                  self.current_subchain_level))

  def addFreshlyMappedBacktrackRecord(self, bt_record, link_mapping_rec):
    """
    Handles a queue of currently mapped BacktrackRecords, these should be
    added back to the network resources when stepping back.
    """
    if bt_record is None:
      if len(self.currently_mapped) == 0:
        self._handleOneLinkLongSubchainFromSAP(link_mapping_rec)
      else:
        tmp = self.currently_mapped.pop()
        # it there is not already a link mapping record here
        if tmp[2] is None:
          self.currently_mapped.append((self.subchains_with_subgraphs[\
                                        self.current_subchain_level][0],
                                        tmp[1], 
                                        link_mapping_rec,
                                        self.current_subchain_level))
        else:
          # this can be the case when we are at a subchain which consists of only
          # one link and starts from a SAP.
          self.currently_mapped.append(tmp)
          self._handleOneLinkLongSubchainFromSAP(link_mapping_rec)
        
    else:
      self.currently_mapped.append((self.subchains_with_subgraphs[\
                                    self.current_subchain_level][0],
                                    bt_record, 
                                    link_mapping_rec,
                                    self.current_subchain_level))

  def getCurrentlyMappedBacktrackRecord(self):
    """
    Returns the BacktrackRecord which should be undone to take a proper 
    backstep.
    """
    try:
      return self.currently_mapped.pop()
    except IndexError:
      raise uet.InternalAlgorithmException("Currently mapped queue is already "
                "empty, while there is still backtrack possibility available.")

  def checkSubchainLevelStep(self, tmp_subchain_level):
    if 0 <= self.current_subchain_level - tmp_subchain_level <= 1:
      # current_subchain_level can only stay, or decrease
      if self.current_subchain_level - tmp_subchain_level == 1:
        # if we step back we need to adjust the vnf_index
        chain_to_bt_len = len(self.subchains_with_subgraphs[\
                                  tmp_subchain_level][0]['chain'])
        self.vnf_index_in_subchain = chain_to_bt_len-2 if \
                                     chain_to_bt_len-2 > 0 else 0
        self.current_subchain_level = tmp_subchain_level
    else:
      raise uet.InternalAlgorithmException("Backtrack structure maintenance"
                " error: backtrack step wanted to skip a subchain level.")

  def getNextBacktrackRecordAndSubchainSubgraph(self, link_bt_rec_list):
    """
    Either returns a backtrack record where the mapping process can continue, 
    or raised a real, seroius MappingException, when mapping can't be continued.
    This is the actual backstepping. Should be called after catching a 
    MappingException indicating the need for backstep.
    Returns the list of backtrack records to be undone and the next record which
    can be mapped.
    """
    record = None
    try:
      record = self.bt_struct.pop()
      self.bt_struct.append(record)
    except IndexError:
      raise uet.MappingException("Backtrack limit reached, no further mapping"
                                 "possibilities are available", 
                                 backtrack_possible = False,
                                 peak_sc_cnt = self.failer_subchain_count)

    c_prime, prev_bt_rec, link_mapping_rec, tmp_subchain_level = \
                         self.getCurrentlyMappedBacktrackRecord()
    self.checkSubchainLevelStep(tmp_subchain_level)
    link_bt_rec_list.append((c_prime, prev_bt_rec, link_mapping_rec))
    while prev_bt_rec is None and link_mapping_rec is not None:
      c_prime, prev_bt_rec, link_mapping_rec, tmp_subchain_level = \
                         self.getCurrentlyMappedBacktrackRecord()
      self.checkSubchainLevelStep(tmp_subchain_level)
      link_bt_rec_list.append((c_prime, prev_bt_rec, link_mapping_rec))
    try:
      tmp_subchain_level, possible_hosts_of_a_vnf = record
      self.checkSubchainLevelStep(tmp_subchain_level)
      self.vnf_index_in_subchain -= 1
      bt_record = possible_hosts_of_a_vnf.pop()
      self.log.debug("Stepping back on VNF %s of subchain level %s"%
                     (bt_record['vnf_id'], tmp_subchain_level))
      c = self.subchains_with_subgraphs[self.current_subchain_level][0]
      # return c, sub, bt_record, list of (cid, prev_bt_rec, link_mapping_rec)
      return c,\
        self.subchains_with_subgraphs[self.current_subchain_level][1], \
        bt_record, link_bt_rec_list

    except IndexError:
      self.bt_struct.pop() # remove empty deque of possible mappings ('record')
      return self.getNextBacktrackRecordAndSubchainSubgraph(link_bt_rec_list)
