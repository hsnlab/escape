# Copyright 2015 Sahel Sahhaf <sahel.sahhaf@intec.ugent.be>
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
Contains the class for managing NFIB.
"""
import os
from collections import deque

import networkx
import py2neo
from py2neo import Graph, Relationship, Unauthorized
from py2neo.packages.httpstream.http import SocketError

from escape.nffg_lib.nffg import NFFG
from escape.orchest import log as log
from escape.util.misc import quit_with_error


class NFIBManager(object):
  """
  Manage the handling of Network Function Information Base.

  Use neo4j implementation for storing and querying NFs and NF decompositions.
  """

  def __init__ (self):
    """
    Init.
    """
    super(NFIBManager, self).__init__()
    log.debug("Init %s based on neo4j" % self.__class__.__name__)
    # Suppress low level logging
    self.__suppress_neo4j_logging()
    try:
      self.graph_db = Graph()
    except Unauthorized as e:
      quit_with_error(
        "Got Unauthorozed error on: %s from neo4j! Disable the authorization "
        "in /etc/neo4j/neoj4-server.properties!" % e)

  @staticmethod
  def __suppress_neo4j_logging (level=None):
    """
    Suppress annoying and detailed logging of `py2neo` and `httpstream`
    packages.

    :param level: level of logging (default: WARNING)
    :type level: str
    :return: None
    """
    import logging
    level = level if level is not None else logging.WARNING
    logging.getLogger("py2neo").setLevel(level)
    logging.getLogger("neo4j").setLevel(level)
    logging.getLogger("httpstream").setLevel(level)

  def addNode (self, node):
    """
    Add new node to the DB.

    :param node: node to be added to the DB
    :type node: dict
    :return: success of addition
    :rtype: Boolean
    """
    node_db = list(
      self.graph_db.find(node['label'], 'node_id', node['node_id']))
    if len(node_db) > 0:
      log.debug("node %s exists in the DB" % node['node_id'])
      return False
    node_new = py2neo.Node(node['label'], node_id=node['node_id'])
    for key, value in node.items():
      node_new.properties[key] = value
    self.graph_db.create(node_new)
    return True

  def addClickNF (self, nf):
    """
    Add new click-based NF to the DB
 
    :param nf: nf to be added to the DB
    :type nf: dict
    :return: success of addition
    :rtype: Boolean
    """
    dirname = "/home/mininet/escape-shared/mininet/mininet"

    # 1. First check if the source can be compiled
    if nf.get('clickSource', ''):
      if not self.clickCompile(nf):
        return False

    # 2. Check the existence of the required VNFs/Click elements
    dependency = []
    clickTempPath = nf.get('clickTempPath',
                           dirname + '/templates/' + nf['node_id'] + '.jinja2')
    if os.path.exists(clickTempPath):

      with open(clickTempPath) as template:
        for line in template:
          if '::' in line:
            element = line.split('::')[-1].split('(')[0].replace(' ', '')

            node = list(self.graph_db.find('NF', 'node_id', str(element)))
            if len(node) <= 0:
              log.debug(
                "The new NF is dependent on non-existing NF %s" % element)
              return False
            else:
              dependency.append(str(element))
      template = open(clickTempPath, 'r').read()
    else:
      template = ''

    # 3. Extract the click handlers form the source files
    read_handlers = {}
    read = []
    write_handlers = {}
    write = []

    for src in nf.get('clickSource', ''):
      if '.cc' in src:
        with open(nf.get('clickPath', '') + '/' + src) as source:
          for line in source:
            if 'add_read_handler' in line:
              hdlr = line.split('"')[1]
              if hdlr not in read:
                read.append(hdlr)
            if 'add_write_handler' in line:
              hdlr = line.split('"')[1]
              if hdlr not in write:
                write.append(hdlr)
    if read:
      read_handlers[nf['node_id']] = read
    if write:
      write_handlers[nf['node_id']] = write

    # Add the handlers of other elements used in click scripts of the new NF
    if dependency:
      for element in dependency:
        NF_info = self.getNF(element)
        read = eval(NF_info['read_handlers']).get(element, '')
        write = eval(NF_info['write_handlers']).get(element, '')
        if read:
          read_handlers[element] = read
        if write:
          write_handlers[element] = write

    # 4. Add the NF to the DB
    nf.update(
      {
        'dependency': repr(dependency), 'read_handlers': repr(read_handlers),
        'write_handlers': repr(write_handlers), 'command': str(template)
      })
    self.addNode(nf)

  def addVMNF (self, nf):
    # To be updated
    self.addNode(nf)

  @staticmethod
  def clickCompile (nf):
    """
    Compile source of the click-based NF

    :param nf: the click-based NF
    :type nf: dict
    :return: success of compilation
    :rtype: Boolean
    """
    for src in nf.get('clickSource', ''):
      if not os.path.exists(nf.get('clickPath', '') + '/' + src):
        log.debug("source file does not exist: %s" % src)
        return False
    os.system('cd ' + nf.get('clickPath',
                             '') + '; make clean; ./configure; make elemlist; '
                                   'make')
    if not os.path.exists(nf.get('clickPath', '') + '/userlevel/click'):
      log.debug("The source code can not be compiled")
      return False
    else:
      return True

  def removeNF (self, nf_id):
    """
    Remove an NF and all its decompositions from the DB.

    :param nf_id: the id of the NF to be removed from the DB
    :type nf_id: string
    :return: success of removal
    :rtype: Boolean
    """
    node = list(self.graph_db.find('NF', 'node_id', nf_id))
    if len(node) > 0:
      rels_DECOMPOSE = list(
        self.graph_db.match(start_node=node[0], rel_type='DECOMPOSED'))
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
    :type nf: dict
    :return: success of the update
    :rtype: Boolean
    """
    node = list(self.graph_db.find(nf['label'], 'node_id', nf['node_id']))
    if len(node) > 0:
      node[0].set_properties(nf)
      return True
    else:
      log.debug("node %s does not exist in the DB" % nf['node_id'])
      return False

  def getNF (self, nf_id):
    """
    Get the information for the NF with id equal to nf_id.
 
    :param nf_id: the id of the NF to get the information for
    :type nf_id: string
    :return: the information of NF with id equal to nf_id
    :rtype: dict
    """
    node = list(self.graph_db.find('NF', 'node_id', nf_id))
    if len(node) > 0:
      return node[0].properties
    else:
      log.debug("node %s does not exist in the DB" % nf_id)
      return None

  def addRelationship (self, relationship):
    """
    Add relationship between two existing nodes

    :param relationship: relationship to be added between two nodes
    :type relationship: dict
    :return: success of the addition
    :rtype: Boolean
    """
    node1 = list(self.graph_db.find(relationship['src_label'], 'node_id',
                                    relationship['src_id']))
    node2 = list(self.graph_db.find(relationship['dst_label'], 'node_id',
                                    relationship['dst_id']))

    if len(node1) > 0 and len(node2) > 0:

      rel = Relationship(node1[0], relationship['rel_type'], node2[0])
      for key, value in relationship.items():
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
    :type relationship: dict
    :return: the success of the removal
    :rtype: Boolean
    """
    node1 = list(self.graph_db.find(relationship['src_label'], 'node_id',
                                    relationship['src_id']))
    node2 = list(self.graph_db.find(relationship['dst_label'], 'node_id',
                                    relationship['dst_id']))
    if len(node1) > 0 and len(node2) > 0:
      rels = list(self.graph_db.match(start_node=node1[0], end_node=node2[0],
                                      rel_type=relationship['rel_type']))
      for r in rels:
        r.delete()
      return True
    else:
      log.debug("nodes do not exist in the DB")
      return False

  def addDecomp (self, nf_id, decomp_id, decomp):
    """
    Add new decomposition for a high-level NF.

    :param nf_id: the id of the NF for which a decomposition is added
    :type nf_id: string
    :param decomp_id: the id of the new decomposition
    :type decomp_id: string
    :param decomp: the decomposition to be added to the DB
    :type decomp: Networkx.Digraph
    :return: success of the addition
    :rtype: Boolean
    """
    nf = list(self.graph_db.find('NF', 'node_id', nf_id))
    if len(nf) <= 0:
      log.debug("NF %s does not exist in the DB" % nf_id)
      return False

    for n in decomp.nodes():
      node = list(self.graph_db.find('SAP', 'node_id', n))
      if len(node) > 0:
        log.debug("SAPs exist in the DB")
        return False
    if not self.addNode({'label': 'graph', 'node_id': decomp_id}):
      log.debug("decomposition %s exists in the DB" % decomp_id)
      return False

    for n in decomp.nodes():

      if decomp.node[n]['properties']['label'] == 'SAP':
        self.addNode(decomp.node[n]['properties'])
        dst_label = 'SAP'

      elif decomp.node[n]['properties']['label'] == 'NF' and \
            decomp.node[n]['properties']['type'] == 'click':
        self.addClickNF(decomp.node[n]['properties'])
        dst_label = 'NF'

      elif decomp.node[n]['properties']['label'] == 'NF' and \
            decomp.node[n]['properties']['type'] == 'VM':
        self.addVMNF(decomp.node[n]['properties'])
        dst_label = 'NF'

      elif decomp.node[n]['properties']['label'] == 'NF' and \
            decomp.node[n]['properties']['type'] == 'NA':
        self.addNode(decomp.node[n]['properties'])
        dst_label = 'NF'
      else:
        # FIXME - czentye --> add default to dst_label variable always be
        # defined for addRelationship
        self.addNode({'label': 'NF', 'type': 'NA'})
        dst_label = 'NA'

      self.addRelationship(
        {
          'src_label': 'graph', 'dst_label': dst_label, 'src_id': decomp_id,
          'dst_id': n, 'rel_type': 'CONTAINS'
        })

    for e in decomp.edges():
      temp = {
        'src_label': decomp.node[e[0]]['properties']['label'],
        'src_id': e[0],
        'dst_label': decomp.node[e[1]]['properties']['label'],
        'dst_id': e[1], 'rel_type': 'CONNECTED'
      }
      temp.update(decomp.edge[e[0]][e[1]]['properties'])

      self.addRelationship(temp)

    self.addRelationship(
      {
        'src_label': 'NF', 'src_id': nf_id, 'dst_label': 'graph',
        'dst_id': decomp_id, 'rel_type': 'DECOMPOSED'
      })
    return True

  def removeDecomp (self, decomp_id):
    """
    Remove a decomposition from the DB.

    :param decomp_id: the id of the decomposition to be removed from the DB
    :type decomp_id: string
    :return: the success of the removal
    :rtype: Boolean
    """
    node = list(self.graph_db.find('graph', 'node_id', decomp_id))

    if len(node) > 0:
      queue = deque([node[0]])
      while len(queue) > 0:
        node = queue.popleft()

        # we search for all the nodes with relationship CONTAINS or DECOMPOSED
        rels_CONTAINS = list(
          self.graph_db.match(start_node=node, rel_type='CONTAINS'))
        rels_DECOMPOSED = list(
          self.graph_db.match(start_node=node, rel_type='DECOMPOSED'))
        if len(rels_CONTAINS) > 0:
          rels = rels_CONTAINS
        else:
          rels = rels_DECOMPOSED
        for rel in rels:
          if len(list(self.graph_db.match(end_node=rel.end_node,
                                          rel_type='CONTAINS'))) <= 1:
            queue.append(rel.end_node)
        node.isolate()
        node.delete()
      return True
    else:
      log.debug("decomposition %s does not exist in the DB" % decomp_id)
      return False

  def getSingleDecomp (self, decomp_id):
    """
    Get a decomposition with id decomp_id.
  
    : param decomp_id: the id of the decomposition to be returned
    : type decomp_id: str
    : return: decomposition with id equal to decomp_id
    : rtype: tuple of networkx.DiGraph and Relationships 
    """

    graph = networkx.DiGraph()
    node = list(self.graph_db.find('graph', 'node_id', decomp_id))

    if len(node) != 0:
      rels = list(self.graph_db.match(start_node=node[0], rel_type='CONTAINS'))
      for rel in rels:
        graph.add_node(rel.end_node.properties['node_id'])
        graph.node[rel.end_node.properties['node_id']][
          'properties'] = rel.end_node.properties
      for rel in rels:
        rel_CONNECTED = list(
          self.graph_db.match(start_node=rel.end_node, rel_type='CONNECTED'))
        for rel_c in rel_CONNECTED:
          if rel_c.end_node.properties['node_id'] in graph.nodes():
            graph.add_edge(rel_c.start_node.properties['node_id'],
                           rel_c.end_node.properties['node_id'])
            graph.edge[rel_c.start_node.properties['node_id']][
              rel_c.end_node.properties['node_id']][
              'properties'] = rel_c.properties
      return graph, rels
    else:
      log.debug("decomposition %s does not exist in the DB" % decomp_id)
      return None

  def getDecomps (self, nffg):
    """
    Get all decompositions for a given nffg.

    : param nffg: the nffg for which the decompositions should be returned
    : type nffg: nffg
    : return: all the decompositions for the given nffg
    : rtype: dict
    """
    decompositions = {}
    nodes_list = []
    index = 0

    for n in nffg.nfs:
      node = list(self.graph_db.find('NF', 'node_id', n.id))
      if len(node) != 0:
        nodes_list.append(node[0])

      else:
        log.debug("NF %s does not exist in the DB" % n.id)
        return None

    queue = deque([nodes_list])
    queue_nffg = deque([nffg])
    while len(queue) > 0:
      nodes = queue.popleft()
      nffg_init = queue_nffg.popleft()
      indicator = 0
      for node in nodes:
        rels_DECOMPOSED = list(
          self.graph_db.match(start_node=node, rel_type='DECOMPOSED'))
        for rel in rels_DECOMPOSED:
          indicator = 1
          nffg_temp = NFFG()
          graph, rels = self.getSingleDecomp(rel.end_node.properties['node_id'])

          for n in graph.nodes():
            if graph.node[n]['properties']['label'] == 'NF':
              nffg_temp.add_nf(id=n,
                               dep_type=graph.node[n]['properties']['type'],
                               cpu=graph.node[n]['properties']['cpu'],
                               mem=graph.node[n]['properties']['mem'],
                               storage=graph.node[n]['properties']['storage'])

            elif graph.node[n]['properties']['label'] == 'SAP':
              nffg_temp.add_sap(id=n)
          counter = 0
          for edge in graph.edges():

            for nf in nffg_temp.nfs:

              if nf.id == edge[0]:
                node0 = nf
              if nf.id == edge[1]:
                node1 = nf
            for sap in nffg_temp.saps:
              if sap.id == edge[0]:
                node0 = sap
              if sap.id == edge[1]:
                node1 = sap
            # FIXME - czentye --> There is a chance node0, node1 variables
            # not defined yet until here and add_port will be raise an exception
            nffg_temp.add_sglink(node0.add_port(
              graph.edge[edge[0]][edge[1]]['properties']['src_port']),
              node1.add_port(
                graph.edge[edge[0]][edge[1]]['properties']['dst_port']),
              id='hop' + str(counter))

          for n in nffg_init.nfs:
            nffg_temp.add_node(n)
          for n in nffg_init.saps:
            nffg_temp.add_node(n)
          for n in nffg_init.infras:
            nffg_temp.add_node(n)
          for l in nffg_init.links:
            nffg_temp.add_edge(l.src.node, l.dst.node, l)
          for l in nffg_init.sg_hops:
            nffg_temp.add_edge(l.src.node, l.dst.node, l)
          for l in nffg_init.reqs:
            nffg_temp.add_edge(l.src.node, l.dst.node, l)

          extra_nodes = []
          for l in nffg_temp.sg_hops:
            if node.properties['node_id'] == l.src.node.id:
              src_port = l.src
              dst_port = l.dst

              for edge in graph.edges():
                if graph.node[edge[1]]['properties']['label'] == 'SAP':

                  if str(src_port.id) == str(
                     graph.edge[edge[0]][edge[1]]['properties']['dst_port']):

                    for e in nffg_temp.sg_hops:
                      if e.src.node.id == edge[0] and e.dst.node.id == edge[1]:
                        nffg_temp.add_sglink(e.src, dst_port)
                        extra_nodes.append(edge[1])

            if node.properties['node_id'] == l.dst.node.id:
              dst_port = l.dst
              src_port = l.src

              for edge in graph.edges():
                if graph.node[edge[0]]['properties']['label'] == 'SAP':

                  if str(dst_port.id) == str(
                     graph.edge[edge[0]][edge[1]]['properties']['src_port']):
                    for e in nffg_temp.sg_hops:
                      if e.src.node.id == edge[0] and e.dst.node.id == edge[1]:
                        nffg_temp.add_sglink(src_port, e.dst)
                        extra_nodes.append(edge[0])

          nffg_temp.del_node(node.properties['node_id'])
          for extra in extra_nodes:
            nffg_temp.del_node(extra)
          queue_nffg.append(nffg_temp)

          nodes_copy = list(nodes)
          new_nodes = map(lambda x: x.end_node, rels)
          nodes_copy.remove(node)
          queue.append(nodes_copy + new_nodes)
        if indicator == 1:
          break
      if indicator == 0:
        decompositions['D' + str(index)] = nffg_init
        index += 1

    return decompositions

  def removeGraphDB (self):
    """
    Remove all nodes and relationships from the DB.
   
    :return: None
    """
    self.graph_db.delete_all()

  def __initialize (self):
    """
    Initialize NFIB with test data.
    """
    log.info("Initializing NF database with NFs and decompositions...")
    # start clean - all the existing info is removed from the DB
    self.removeGraphDB()
    # add new high-level NF to the DB, all the information related to the NF
    # should be given as a dict
    self.addNode({'label': 'NF', 'node_id': 'forwarder', 'type': 'NA'})
    self.addNode({'label': 'NF', 'node_id': 'compressor', 'type': 'NA'})
    self.addNode({'label': 'NF', 'node_id': 'decompressor', 'type': 'NA'})

    log.debug(
      "%s: high-level NFs were added to the DB" % self.__class__.__name__)

    # generate a  decomposition for a high-level forwarder NF (in form of
    # networkx)
    G1 = networkx.DiGraph()
    G1.add_path(['SAP1', 'simpleForwarder', 'SAP2'])

    # create node properties
    for n in G1.nodes():
      properties = {'node_id': n}

      if 'SAP' in n:
        properties['label'] = 'SAP'
        properties['type'] = 'NA'
      else:
        properties['label'] = 'NF'
        properties['type'] = 'click'
        properties['cpu'] = 10
        properties['mem'] = 100
        properties['storage'] = 100
      G1.node[n]['properties'] = properties

    # create edge properties
    properties = {'BW': 100, 'src_port': 1, 'dst_port': 1}
    G1.edge['SAP1']['simpleForwarder']['properties'] = properties

    properties1 = {'BW': 100, 'src_port': 2, 'dst_port': 2}
    G1.edge['simpleForwarder']['SAP2']['properties'] = properties1

    # generate a decomposition for a high-level compressor NF (in form of
    # networkx)
    G2 = networkx.DiGraph()
    G2.add_path(['SAP3', 'headerCompressor', 'SAP4'])

    # create node properties
    for n in G2.nodes():
      properties = {'node_id': n}
      if 'SAP' in n:
        properties['label'] = 'SAP'
        properties['type'] = 'NA'
      else:
        properties['label'] = 'NF'
        properties['type'] = 'click'
        properties['cpu'] = 20
        properties['mem'] = 200
        properties['storage'] = 200
      G2.node[n]['properties'] = properties

    # create edge properties 
    properties3 = {'BW': 200, 'src_port': 1, 'dst_port': 1}
    G2.edge['SAP3']['headerCompressor']['properties'] = properties3

    properties4 = {'BW': 200, 'src_port': 2, 'dst_port': 2}
    G2.edge['headerCompressor']['SAP4']['properties'] = properties4

    # generate a decomposition for a high-level decompressor NF (in form of
    # networkx)
    G3 = networkx.DiGraph()
    G3.add_path(['SAP5', 'headerDecompressor', 'SAP6'])

    # create node properties
    for n in G3.nodes():
      properties = {'node_id': n}
      if 'SAP' in n:
        properties['label'] = 'SAP'
        properties['type'] = 'NA'
      else:
        properties['label'] = 'NF'
        properties['type'] = 'click'
        properties['cpu'] = 30
        properties['mem'] = 300
        properties['storage'] = 300
      G3.node[n]['properties'] = properties

    # create edge properties
    properties5 = {'BW': 300, 'src_port': 1, 'dst_port': 1}
    G3.edge['SAP5']['headerDecompressor']['properties'] = properties5

    properties6 = {'BW': 300, 'src_port': 2, 'dst_port': 2}
    G3.edge['headerDecompressor']['SAP6']['properties'] = properties6

    # required elementary NFs should be added first to the DB
    self.addClickNF({'label': 'NF', 'node_id': 'Queue', 'type:': 'click'})
    self.addClickNF({'label': 'NF', 'node_id': 'Classifier', 'type': 'click'})
    self.addClickNF({'label': 'NF', 'node_id': 'Counter', 'type': 'click'})
    self.addClickNF({'label': 'NF', 'node_id': 'RFC2507Comp', 'type': 'click'})
    self.addClickNF(
      {'label': 'NF', 'node_id': 'RFC2507Decomp', 'type': 'click'})

    # the NF decompositions are added to the DB
    self.addDecomp('forwarder', 'G1', G1)
    self.addDecomp('compressor', 'G2', G2)
    self.addDecomp('decompressor', 'G3', G3)

    log.debug(
      "%s: NF decompositions were added to the DB" % self.__class__.__name__)

  def initialize (self):
    """
    Initialize NFIB with test data.
    """
    try:
      self.__initialize()
    except SocketError as e:
      log.error(
        "NFIB is not reachable due to failed neo4j service! Cause: " + str(e))
    except KeyboardInterrupt:
      log.warning("NFIB was interrupted by user!")
    except Unauthorized:
      log.error(
        "neo4j responded with Unauthorized error! Maybe you forgot disabling "
        "authentication in '/etc/neo4j/neo4j.conf' ?")
    except OSError as e:
      if ".neo4j/known_hosts" in str(e):
        # Skip Permission denied in case of accessing neo4j cache file (v3.0.2)
        pass
      else:
        raise
    except:
      log.exception("Got unexpected error during NFIB initialization!")
