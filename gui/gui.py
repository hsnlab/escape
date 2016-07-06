#!/usr/bin/env python
import logging
import networkx as nx
import os
import sys

import viewer_thread as vt

try:
  from nffg import NFFG
  from conversion import NFFGConverter
except ImportError:
  for p in ("../escape/escape/nffg_lib/",
            "../escape/escape/util/",
            "../unify_virtualizer/"):
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), p)))
  from nffg import NFFG
  from conversion import NFFGConverter

if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG)
  graph = None
  if len(sys.argv) > 1:
    nffg_path = os.path.abspath(os.path.join(os.getcwd(), sys.argv[1]))
    with open(nffg_path, 'r') as f:
      raw = f.read()
    if raw.startswith("<?xml"):
      converter = NFFGConverter(logger=logging.getLogger(__name__))
      graph = converter.parse_from_Virtualizer(raw)
    else:
      graph = NFFG.parse(raw)
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
  t_view.join()
  logging.info("Quitting...")
