import networkx as nx
from tokens import CustomNodeToken, CustomEdgeToken
import sys
import threading

try:
    # Python 3
    import tkinter as tk
    import tkinter.messagebox as tkm
    import tkinter.simpledialog as tkd
except ImportError:
    # Python 2
    import Tkinter as tk
    import tkMessageBox as tkm
    import tkSimpleDialog as tkd

from networkx_viewer import *

class SetterDialog( tkd.Dialog):

  def body (self, master):
    tk.Label (master, text="URL: ").grid(row=0);
    self.e1 = tk.Entry(master)
    self.e1.grid(row=0, column=1)
    return self.e1

  def apply(self):
    self.result = self.e1.get()

  def get(self):
    return self.result

class CustomViewerCanvas( ViewerApp):

  def __init__(self, graph, **kwargs):
    self.__kwargs = kwargs
    ViewerApp.__init__(self, graph, NodeTokenClass=CustomNodeToken, EdgeTokenClass=CustomEdgeToken, **kwargs)
    self.url = None

    #Building menu
    tools = tk.Menu(self.menubar, tearoff=0)
    tools.add_command(label="Set URL", command=self.setURL)
    self.menubar.add_cascade(label="Tools", menu=tools)

  def setURL(self):
    self.url = SetterDialog(self).get()

  def refresh(self):
    #search for removable nodes; if found, then redraw whole graph
    iteratorD = self.canvas.dispG.nodes_iter()
    try:
      for k in self.canvas.dispG.nodes():
        dataG_id = self.canvas.dispG.node[k]['dataG_id']
        if not self.canvas.dataG.has_node(dataG_id):
          for e in self.canvas.dispG.edges():
            for id in self.canvas.dispG.edge[e[0]][e[1]]:
              t_id = self.canvas.dispG.edge[e[0]][e[1]][id]['token_id']
              self.canvas.delete(t_id)
          for n in self.canvas.dispG.nodes():
            t_id = self.canvas.dispG.node[n]['token_id']
            self.canvas.dispG.node[n]['token'].delete('all')
            del(self.canvas.dispG.node[n])
          self.canvas.dispG.clear()
          self.canvas.refresh()
          self.canvas._graph_changed()
          self.canvas.plot(self.canvas.dataG.nodes())
      for e in self.canvas.dispG.edges():
        u_dataG_id = self.canvas.dispG.node[e[0]]['dataG_id']
        v_dataG_id = self.canvas.dispG.node[e[1]]['dataG_id']
        
        if not self.canvas.dataG.has_edge(u_dataG_id,v_dataG_id) and not self.canvas.dataG.has_edge(v_dataG_id,u_dataG_id):
          #TODO needed to add switched edge to-from because a particular link would've been removed. Need to investigate further
          for id in self.canvas.dispG.edge[e[0]][e[1]]:
            t_id = self.canvas.dispG.edge[e[0]][e[1]][id]['token_id']
            self.canvas.delete(t_id)
          del (self.canvas.dispG.edge[e[0]][e[1]])
    except:
      print "%s Unhandled exception: %s" % (__name__,sys.exc_info()[0])

    #need to add new/updated node/edge to dispG
    iterator = self.canvas.dataG.nodes_iter()
    for n in iterator:
      iteratorD = self.canvas.dispG.nodes_iter()
      found = False
      for k in iteratorD:
        if self.canvas.dispG.node[k]['dataG_id'] == n:
          found = True
          break
      if not found:
        t = CustomNodeToken(self.canvas,self.canvas.dataG.node[n],n)
        id = self.canvas.create_window(50, 50, window=t, anchor=tk.CENTER,
                         tags='node')
        self.canvas.dispG.add_node(id,{'dataG_id' : n,'token' : t, 'token_id' : id})
    return
    #TODO code below is copied from parent class, currently unused
    #going through possible new edges
    iterator = self.canvas.dataG.edges_iter()
    for e in iterator:
      u = e[0]
      v = e[1]

      iteratorD = self.canvas.dispG.nodes_iter()
      try:
        frm_disp = self.canvas._find_disp_node(e[0])
        to_disp = self.canvas._find_disp_node(e[1])
      except NodeFiltered:
        break
      if not self.canvas.dispG.has_edge(frm_disp,to_disp):
        #TODO create EdgeToken
        if isinstance(self.canvas.dataG, nx.MultiGraph):
          edges = self.canvas.dataG.edge[u][v]
        elif isinstance(self.canvas.dataG, nx.Graph):
          edges = {0: self.canvas.dataG.edge[u][v]}

        if len(edges) == 1:
          m = 0
        else:
          m = 15

        for key, data in edges.items():
          token = CustomEdgeToken(data)
          if isinstance(self.canvas.dataG, nx.MultiGraph):
            dataG_id = (u,v,key)
          elif isinstance(self.canvas.dataG, nx.Graph):
            dataG_id = (u,v)
          self.canvas.dispG.add_edge(frm_disp, to_disp, key, {'dataG_id': dataG_id,
                                    'dispG_frm': frm_disp,
                                    'token': token,
                                    'm': m})
          x1,y1 = self.canvas._node_center(frm_disp)
          x2,y2 = self.canvas._node_center(to_disp)
          xa,ya = self.canvas._spline_center(x1,y1,x2,y2,m)

          cfg = token.render()
          l = self.canvas.create_line(x1,y1,xa,ya,x2,y2, tags='edge', smooth=True, **cfg)
          self.canvas.dispG[frm_disp][to_disp][key]['token_id'] = l

          if m > 0:
            m = -m # Flip sides
          else:
            m = -(m+m)  # Go next increment out
