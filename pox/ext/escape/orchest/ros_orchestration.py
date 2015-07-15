# Copyright 2015 Janos Czentye <czentye@tmit.bme.hu>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Contains classes relevant to Resource Orchestration Sublayer functionality.
"""
from escape.orchest.ros_mapping import ResourceOrchestrationMapper
from escape.orchest import log as log
from escape.orchest.virtualization_mgmt import AbstractVirtualizer, \
  VirtualizerManager
from py2neo import Graph, Node, Relationship
from collections import deque

class ResourceOrchestrator(object):
  """
  Main class for the handling of the ROS-level mapping functions.
  """

  def __init__ (self, layer_API):
    """
    Initialize main Resource Orchestration Layer components.

    :param layer_API: layer API instance
    :type layer_API: :any:`ResourceOrchestrationAPI`
    :return: None
    """
    super(ResourceOrchestrator, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self.nffgManager = NFFGManager()
    # Init virtualizer manager
    # Listeners must be weak references in order the layer API can garbage
    # collected
    self.virtualizerManager = VirtualizerManager()
    self.virtualizerManager.addListeners(layer_API, weak=True)
    # Init Resource Orchestration Mapper
    # Listeners must be weak references in order the layer API can garbage
    # collected
    self.nffgMapper = ResourceOrchestrationMapper()
    self.nffgMapper.addListeners(layer_API, weak=True)
    # Init NFIB manager
    self.nfibManager = NFIBManager()

  def instantiate_nffg (self, nffg):
    """
    Main API function for NF-FG instantiation.

    :param nffg: NFFG instance
    :type nffg: :any:`NFFG`
    :return: mapped NFFG instance
    :rtype: :any:`NFFG`
    """
    log.debug("Invoke %s to instantiate NF-FG" % self.__class__.__name__)
    # Store newly created NF-FG
    self.nffgManager.save(nffg)
    # Get Domain Virtualizer to acquire global domain view
    global_view = self.virtualizerManager.dov
    if global_view is not None:
      if isinstance(global_view, AbstractVirtualizer):
        # Run Nf-FG mapping orchestration
        mapped_nffg = self.nffgMapper.orchestrate(nffg, global_view)
        log.debug(
          "NF-FG instantiation is finished by %s" % self.__class__.__name__)
        return mapped_nffg
      else:
        log.warning("Global view is not subclass of AbstractVirtualizer!")
    else:
      log.warning("Global view is not acquired correctly!")
    log.error("Abort mapping process!")


class NFFGManager(object):
  """
  Store, handle and organize Network Function Forwarding Graphs.
  """

  def __init__ (self):
    """
    Init.
    """
    super(NFFGManager, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self._nffgs = dict()

  def save (self, nffg):
    """
    Save NF-FG in a dict.

    :param nffg: Network Function Forwarding Graph
    :type nffg: :any:`NFFG`
    :return: generated ID of given NF-FG
    :rtype: int
    """
    nffg.id = len(self._nffgs)
    self._nffgs[nffg.id] = nffg
    log.debug(
      "NF-FG is saved by %s with id: %s" % (self.__class__.__name__, nffg.id))
    return nffg.id

  def get (self, nffg_id):
    """
    Return NF-FG with given id.

    :param nffg_id: ID of NF-FG
    :type nffg_id: int
    :return: NF-Fg instance
    :rtype: :any:`NFFG`
    """
    return self._nffgs.get(nffg_id, default=None)


class NFIBManager(object):
  """
  Manage the handling of Network Function Information Base.
  """

  def __init__ (self):
    """
    Init.
    """
    super(NFIBManager, self).__init__()
    log.debug("Init %s" % self.__class__.__name__)
    self.graph_db = Graph()
   

  def addNF (self, nf):
    """
    Add new NF to the DB.

    :param nf: NF to be added to the DB
    :type: dict
    :return: success of addition
    :rtupe: Boolean
    """
    node = list(self.graph_db.find('NF','node_id',nf['node_id']))
    if len(node)>0:
      log.debug("node %s exists in the DB" % nf['node_id'])
      return False
    node = Node(nf['label'], node_id=nf['node_id'])
    for key,value in nf.items():
      node.properties[key] = value
    self.graph_db.create(node)
    return True

  def addClickNF (self, nf):
    # To be implemented
    pass

  def addVMNF (self, nf):
    # To be implemented
    pass

  def removeNF (self, nf_id):
    """
    Remove an NF and all its decompositions from the DB.

    :param nf_id: the id of the NF to be removed from the DB
    :type: string
    :return: success of removal
    :rtype: Boolean
    """
    node = list(self.graph_db.find('NF','node_id',nf_id))
    if len(node)>0:
      rels_DECOMPOSE = list(self.graph_db.match(start_node=node[0], rel_type='DECOMPOSED'))
      for rel in rels_DECOMPOSE:
        self.removeDecomp(rel.end_node.properties['node_id'])
      node[0].delete_related()
      return True
    else:
      log.debug("node %s does not exist in the DB" % nf_id)
      return False

  def updateNF (self, nf):
    """
    Update the information of a NF.

    :param nf: the information for the NF to be updated
    :type: dict
    :return: success of the update
    :rtype: Boolean
    """
    node = list(self.graph_db.find(nf['label'],'node_id', nf['node_id']))
    if len(node)>0:
      node[0].set_properties(nf)
      return True
    else:
      log.debug("node %s does not exist in the DB" % nf['node_id'])
      return False

  def getNF (self, nf_id):
    """
    Get the information for the NF with id equal to nf_id.
 
    :param nf_id: the id of the NF to get the information for
    :type: string
    :return: the information of NF with id equal to nf_id
    :rtype: dict
    """
    node = list(self.graph_db.find('NF','node_id',nf_id))
    if len(node)>0:
      return node[0].properties
    else:
      log.debug("node %s does not exist in the DB" % nf_id)
      return None

  def addRelationship (self, relationship):
    """
    Add relationship between two existing nodes

    :param relationshp: relationship to be added between two nodes
    :type: dict
    :return: success of the addition
    :rtype: Boolean
    """
    node1 = list(self.graph_db.find(relationship['src_label'],'node_id',relationship['src_id']))
    node2 = list(self.graph_db.find(relationship['dst_label'],'node_id',relationship['dst_id']))

    if len(node1)>0 and len(node2)>0:

      rel = Relationship(node1[0], relationship['rel_type'], node2[0])
      for key,value in relationship.items():
        if 'src' not in key and 'dst' not in key:
          rel.properties[key] = value
      self.graph_db.create(rel)
      return True
    else:
      log.debug("nodes do not exist in the DB")
      return False

  def removeRelationship (self, relationship):
    """
    Remove the relationship between two nodes in the DB.

    :param relationship: the relationship to be removed
    :type: dict
    :return: the success of the removal
    :rtype: Boolean
    """
    node1 = list(self.graph_db.find(relationship['src_label'],'node_id',relationship['src_id']))
    node2 = list(self.graph_db.find(relationship['dst_label'],'node_id',relationship['dst_id']))
    if len(node1)>0 and len(node2)>0:
      rels = list(self.graph_db.match(start_node=node1[0], end_node=node2[0],rel_type=relationship['rel_type']))
      for r in rels:
        r.delete()
      return True
    else:
      log.debug("nodes do not exist in the DB")
      return False

  def addDecomp (self, nf_id, decomp_id, decomp):
    """
    Add new decompostion for a high-level NF.

    :param nf_id: the id of the NF for which a decomposition is added
    :type: string
    :param decomp_id: the id of the new decomposition
    :type: string
    :param decomp: the decomposition to be added to the DB
    :type: Networkx.Digraph
    :return: success of the addition
    :rtype: Boolean
    """
    nf = list(self.graph_db.find('NF','node_id',nf_id))
    if len(nf)<=0:
      log.debug("node %s does not exist in the DB" % nf_id)
      return False

    for n in decomp.nodes():
      node = list(self.graph_db.find('NF','node_id',n))
      if len(node)>0 and 'EP' in n:
        log.debug("Endpoints exist in the DB")
        return False
    if self.addNF({'label':'graph','node_id':decomp_id})==False:
      log.debug("decomposition %s exists in the DB" % decomp_id)
      return False

    for n in decomp.nodes():
      self.addNF(decomp.node[n]['properties'])
      self.addRelationship({'src_label':'graph', 'dst_label':'NF','src_id':decomp_id,'dst_id':n,'rel_type':'CONTAINS'})

    for e in decomp.edges():
      temp = {'src_label':'NF','src_id':e[0],'dst_label':'NF','dst_id':e[1],'rel_type':'CONNECTED'}
      temp.update(decomp.edge[e[0]][e[1]]['properties'])
      self.addRelationship(temp)

    self.addRelationship({'src_label':'NF','src_id':nf_id,'dst_label':'graph','dst_id':decomp_id,'rel_type':'DECOMPOSED'})
    return True

  def removeDecomp (self, decomp_id):
    """
    Remove a decomposition from the DB.

    :param decomp_id: the id of the decomposition to be removed from the DB
    :type: string
    :return: the success of the removal
    :rtype: Boolean
    """
    node = list(self.graph_db.find('graph','node_id',decomp_id))

    if len(node)>0:
      queue = deque([node[0]])
      while len(queue)>0:
        node = queue.popleft()

        # we search for all the nodes with relationship CONTAINS or DECOMPOSED
        rels_CONTAINS = list(self.graph_db.match(start_node=node, rel_type='CONTAINS'))
        rels_DECOMPOSED = list(self.graph_db.match(start_node=node,rel_type='DECOMPOSED'))
        if len(rels_CONTAINS)>0:
          rels = rels_CONTAINS
        else:
          rels = rels_DECOMPOSED
        for rel in rels:
          if len(list(self.graph_db.match(end_node = rel.end_node,rel_type='CONTAINS')))<=1:
	    queue.append(rel.end_node)
        node.isolate()
        node.delete()
      return True
    else:
      log.debug("decomposition %s does not exist in the DB" % decomp_id)
      return False

  def getDecomp (self, nffg):
    # To be implemented
    pass

  def removeGraphDB (self):
    """
    Remove all nodes and relationships from the DB.
   
    :return: None
    """
    self.graph_db.delete_all()
