
__author__="Jokin Garay <jokin.garay@ehu.eus>"
__date__ ="$06-Feb-2015 12:45:02$"

import networkx as nx
from networkx.readwrite import json_graph
import json
import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import pylab as pyl
import pprint
import copy

# RG Version
RG_VERSION = '1.0'

# Params for RG drawing
INF_NODE_SIZE=1200
EP_NODE_SIZE=450
INF_NODE_COLOR='green'
EP_NODE_COLOR='cyan'
NODE_ALPHA=0.3
NODE_TEXT_SIZE=10
EDGE_COLOR='green'
EDGE_ALPHA=0.3
EDGE_THICKNESS=1
EDGE_TEXT_POS=0.5
EDGE_TEXT_SIZE=6
TEXT_FONT='sans-serif'

class ResourceGraph(nx.MultiGraph):

    def __init__(self, rg_id=None, rg_path=None,verbose=True):
        # Allow calling without Rg Id for inherited methods (i.e. subgraph)
        
        super(ResourceGraph, self).__init__()
                
        if rg_id is not None and rg_path is not None:
            if verbose:
                print("Read file: %s%s" % (rg_path, rg_id))
            with open(rg_path + rg_id) as rg_file:
                data = json.load(rg_file)
            self.__dict__ = copy.deepcopy(
                                 json_graph.node_link_graph(data).__dict__)

    def __iter__(self):
        return(super(ResourceGraph, self).__iter__())

    def draw(self, outfile,node_labels=True,link_labels=True):
        # Clean buffer                   
        plt.clf()

        # No axis, spectral layout
        pyl.axis('off')
        #graph_pos=nx.spectral_layout(self)
        graph_pos=nx.circular_layout(self)        

        nx.draw_networkx_nodes(self,graph_pos,node_size=INF_NODE_SIZE, 
                               alpha=NODE_ALPHA, node_color=INF_NODE_COLOR)

        node_labels = nx.get_node_attributes(self,'name')
        
        if node_labels:
            nx.draw_networkx_labels(self, graph_pos,node_labels,
                                    font_size=NODE_TEXT_SIZE,font_family=TEXT_FONT)

        # Draw edges
        nx.draw_networkx_edges(self,graph_pos,width=EDGE_THICKNESS,
                               alpha=EDGE_ALPHA,edge_color=EDGE_COLOR)
        if link_labels:
            nx.draw_networkx_edge_labels(self, graph_pos, label_pos=EDGE_TEXT_POS, 
                                     font_size=EDGE_TEXT_SIZE)

        # Store graph
        plt.savefig(outfile)

    def printout(self, message=None, detail=False):
        if message is not None:
            print(message)
        print("RgId: %6s\tName: %s\nVersion: %s" % (self.graph['id'], 
                                                    self.graph['name'], 
                                                    self.graph['version']))
        print("\tNumber of nodes:\t%s" % self.number_of_nodes())
        print("\tNumber of edges:\t%s" % self.number_of_edges())
        if detail:
            print("\tDetail:")
            pprint.pprint(self.nodes(data=True))
            pprint.pprint(self.edges())

        
    def dumps(self, encode=True):
        data = json_graph.node_link_data(self)
        if encode:
            return json.dumps(data, sort_keys=True).encode()
        else:
            return data        
  
    def dump(self, outfile):
        data = json_graph.node_link_data(self)
        with open(outfile, 'w') as rg_file:
            json.dump(data, rg_file, sort_keys=True, indent=2)

    def loads(injson):
        rg = json_graph.node_link_graph(injson)
        rg.__class__= ResourceGraph
        return rg

    def get_domain(self, rg_pos):
        return self.node[rg_pos]['domain']

    def get_type(self, rg_pos):
        return self.node[rg_pos]['type']
        
        