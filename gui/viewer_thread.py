import logging
import networkx as nx
import threading

import http_client as http
import viewer_canvas as vCanvas

try:
  import nffg as ng
except ImportError:
  import sys, os

  for p in ("/../pox/ext/escape/nffg_lib/",
            "/../pox/ext/escape/util/",
            "/../pox/ext/escape/unify_virtualizer/"):
    sys.path.append(os.path.abspath(os.path.dirname(__file__) + p))
  from nffg import NFFG
  from conversion import NFFGConverter


# from multiprocessing import Process

class ViewerThread(threading.Thread):
  def __init__ (self, viewer_type='get', graph=None, address="127.0.0.1:80"):
    super(ViewerThread, self).__init__()
    '''
    Constructor
    Takes a networkx object and launches a GUI to view the parameters
    of the network using networkx_viewer
    '''
    self.__viewer = None
    # handling other parameters
    self.__http_client = None
    self.__timer = None
    if graph is None:
      graph = nx.MultiDiGraph()
      graph.add_node(1, {'name': 'Set URL'})
      graph.add_node(2, {'name': 'to view NFFG'})
      graph.add_edge(1, 2)
    self.__network = graph
    if viewer_type == 'get':
      self.__http_client = http.GetClient()
      self.__timer = threading.Timer(1, self.timerHandler)
    # self.__update = False
    self._converter = NFFGConverter(logger=logging.getLogger(__name__))

  def timerHandler (self):
    new_nffg = None
    if self.__viewer.url is not None:
      n = self.__http_client.getNFFG(self.__viewer.url)
      if n is not None:
        if str(n).startswith("<?xml"):
          new_nffg = self._converter.parse_from_Virtualizer(n)
        else:
          new_nffg = NFFG.parse(n)
      if new_nffg is not None:
        new_nffg.merge_duplicated_links()
        # Add new nodes from new NFFG - Must add before remove
        # self.__network.add_nodes_from(new_nffg.network.nodes())
        for node in new_nffg.network.nodes():
          self.__network.add_node(node)
          self.__network.node[node].update(
            new_nffg.network.node[node].persist())
          self.__network.node[node].update(
            {"element type": new_nffg.network.node[node].type})

        # Add new edges from new NFFG
        for u, v in new_nffg.network.edges():
          for i in new_nffg.network.edge[u][v]:
            # checking for multiple links between the two nodes
            istr = i
            if self.__network.has_edge(u, v) and istr in self.__network.edge[u][
              v]:
              # TODO link already added, only update
              pass
            else:
              self.__network.add_edge(u, v, istr)
            self.__network.edge[u][v][istr].update(
              new_nffg.network.edge[u][v][i].persist())
            self.__network.edge[u][v][istr].update(
              {"element type": new_nffg.network.edge[u][v][i].type})

        # Remove nodes not present in new NFFG
        for node in self.__network.nodes():
          if not new_nffg.network.has_node(node):
            self.__network.remove_node(node)
          else:
            # updating dict of the node
            self.__network.node[node].update(
              new_nffg.network.node[node].persist())
            self.__network.node[node].update(
              {"element type": new_nffg.network.node[node].type})

        # Remove edges not present in new NFFG
        for u, v in self.__network.edges():
          if not new_nffg.network.has_edge(u, v):
            self.__network.remove_edge(u, v)
          else:
            # updating dict of the edge
            for i in new_nffg.network.edge[u][v]:
              self.__network.edge[u][v][i].update(
                new_nffg.network.edge[u][v][i].persist())
              self.__network.edge[u][v][i].update(
                {"element type": new_nffg.network.edge[u][v][i].type})

        self.__viewer.canvas.dataG = self.__network
        self.__viewer.refresh()

    self.__timer = threading.Timer(1, self.timerHandler)
    self.__timer.start()

  def run (self):
    # Modified Node renderer
    self.__viewer = vCanvas.CustomViewerCanvas(self.__network)
    if self.__timer:
      self.__timer.start()
    try:
      # self.__viewer.update_idletasks()
      # self.__viewer.update()
      self.__viewer.mainloop()
    except:
      self.__timer.cancel()
    self.__timer.cancel()
    return
