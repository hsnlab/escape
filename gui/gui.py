#!/usr/bin/env python
import networkx as nx
import os
import sys

import viewer_thread as vt

try:
  from nffg import NFFG
except ImportError:
  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                               "../escape/escape/nffg_lib/")))
  from nffg import NFFG

if __name__ == '__main__':
  graph = None
  if len(sys.argv) > 1:
    nffg_path = os.path.abspath(os.path.join(os.getcwd(), sys.argv[1]))
    with open(nffg_path, 'r') as f:
      graph = NFFG.parse(f.read())
  else:
    # creating basic network graph
    G = nx.complete_graph(4)
    iterator = G.nodes_iter()
    for i in iterator:
      # creating a dict for storing node parameters
      # TODO create data structure according to NFFG model
      G.node[i]['type'] = 'sap'
      G.node[i]['color'] = 'blue'
      G.node[i]['pattern'] = 'outline'
  # creating thread
  # t_view = vt.ViewerThread(viewer_type="get", graph=G)
  t_view = vt.ViewerThread(viewer_type="get", graph=graph)
  t_view.start()
  # t_view.join()
