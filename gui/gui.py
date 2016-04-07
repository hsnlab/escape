#!/usr/bin/env python
import networkx as nx

import viewer_thread as vt

try:
  from nffg import NFFG
except ImportError:
  import sys, os

  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                  "../escape/escape/nffg_lib/")))
  from nffg import NFFG

if __name__ == '__main__':
  # creating basic network graph
  if 1:
    G = nx.complete_graph(4)
    iterator = G.nodes_iter()
    for i in iterator:
      # creating a dict for storing node parameters
      # TODO create data structure according to NFFG model
      G.node[i]['type'] = 'sap'
      G.node[i]['color'] = 'blue'
      G.node[i]['pattern'] = 'outline'
  else:
    f = open('mapped.nffg', 'r')
    string = f.read()
    f.close()
    # print string
    nfg = NFFG.parse(string)

    G = nfg.network
    G = nx.MultiDiGraph()
    G.add_node('1')

  # creating thread
  # t_view = vt.ViewerThread(viewer_type="get", graph=G)
  t_view = vt.ViewerThread(viewer_type="get")
  t_view.start()
  # t_view.join()
