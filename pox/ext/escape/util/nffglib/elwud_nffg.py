"""Base class for NetworkFunctionForwrdingGraphs.

"""

__author__="Jokin Garay <jokin.garay@ehu.eus>"
__date__ ="$06-Feb-2015 12:45:02$"
            
from networkx.readwrite import json_graph
import json
import copy
from elwud_sg import ServiceGraph
from elwud_rg import ResourceGraph

# NFFG Version
NFFG_VERSION = '1.0'

class NetworkFunctionForwardingGraph(object):
    """
    Base class for NetworkFunctionForwrdingGraphs.

    A Graph stores nodes and edges with optional data, or attributes.

    Graphs hold undirected edges.  Self loops are allowed but multiple
    (parallel) edges are not.

    Nodes can be arbitrary (hashable) Python objects with optional
    key/value attributes.

    Edges are represented as links between nodes with optional
    key/value attributes.

    Parameters
    ----------
    data : input graph
        Data to initialize graph.  If data=None (default) an empty
    attr : keyword arguments, optional (default= no attributes)
        Attributes to add to graph as key=value pairs.

    See Also
    --------
    ServiceGraph
    ResourceGraph

    Examples
    --------
    Create an empty graph structure (a "null graph") with no nodes and
    no edges.

    >>> G = nx.Graph()

    **Nodes:**

    Add one node at a time:

    **Edges:**

    G can also be grown by adding edges.

    **Attributes:**

    Each graph, node, and edge can hold key/value attribute pairs
    in an associated attribute dictionary (the keys must be hashable).


    **Shortcuts:**

    Many common graph features allow python syntax to speed reporting.

    >>> 1 in G     # check if node in graph
    True
    >>> [n for n in G if n<3]   # iterate through nodes
    [1, 2]
    >>> len(G)  # number of nodes in graph
    5

    **Reporting:**

    Simple graph information is obtained using methods.

    **Subclasses (Advanced):**

    The Graph class uses a dict-of-dict-of-dict data structure.
    """


    def __init__(self, base_sg, base_rg, mapping_function=None,verbose=False):
        """Initialize a graph with edges, name, graph attributes.

        Parameters
        ----------
        data : input graph
            Data to initialize graph.  If data=None (default) an empty
        name : string, optional (default='')
            An optional name for the graph.
        attr : keyword arguments, optional (default= no attributes)
            Attributes to add to graph as key=value pairs.

        See Also
        --------
        convert

        Examples
        --------
        >>> G = nx.Graph()   # or DiGraph, MultiGraph, MultiDiGraph, etc
        >>> G = nx.Graph(name='my graph')
        >>> e = [(1,2),(2,3),(3,4)] # list of edges
        >>> G = nx.Graph(e)

        """

        self.sg=ServiceGraph()
        self.sg.__dict__ = copy.deepcopy(base_sg.__dict__)
        self.rg=ResourceGraph()
        self.rg.__dict__ = copy.deepcopy(base_rg.__dict__)
        if mapping_function is not None:
            self.map(self.rg, mapping_function,verbose)

    def draw(self, sg_outfile,rg_outfile):
        self.sg.draw(sg_outfile)
        self.rg.draw(rg_outfile)

    def printout(self, message=None, detail=False):
        self.sg.printout(message, detail)
        self.rg.printout(message, detail)
        
    def dumps(self, encode='True'):
        """Return data in node-link format that is suitable for JSON serialization
        and use in Javascript documents.

        Parameters
        ----------
        G : NetworkX graph

        attrs : dict
            A dictionary that contains four keys 'id', 'source', 'target' and

        Returns
        -------
        data : dict
           A dictionary with node-link formatted data.

        Raises
        ------
        NetworkXError
            If values in attrs are not unique.

        Examples
        --------
        >>> from networkx.readwrite import json_graph
        >>> G = nx.Graph([(1,2)])
        >>> data = json_graph.node_link_data(G)

        To serialize with json

        >>> import json
        >>> s = json.dumps(data)

        Notes
        -----
        Graph, node, and link attributes are stored in this format. Note that
        attribute keys will be converted to strings in order to comply with

        See Also
        --------
        node_link_graph, adjacency_data, tree_data
        """
    
        sg_data = json_graph.node_link_data(self.sg)
        rg_data = json_graph.node_link_data(self.rg)
        data = {'sg': sg_data, 'rg': rg_data}
        if encode:
            return json.dumps(data, sort_keys=True).encode()
        else:
            return data
  
    def dump(self, outfile):
        sg_data = json_graph.node_link_data(self.sg)
        rg_data = json_graph.node_link_data(self.rg)
        data = { 'sg' : sg_data, 'rg' : rg_data }
        with open(outfile, 'w') as rg_file:
            json.dump(data, rg_file, sort_keys=True, indent=2)            

    def loads(injson):
        sg_json = injson['sg']
        rg_json = injson['rg']
        sg = ServiceGraph.loads(sg_json)
        rg = ResourceGraph.loads(rg_json)
        return NetworkFunctionForwardingGraph(sg,rg)
  
    def load(infile):
        try:
            with open(infile) as data_file:    
                data = json.load(data_file)
        except FileNotFoundError:
            print("NF-FG file not found")
            return None
        
        sg_json = data['sg']
        rg_json = data['rg']
        sg = ServiceGraph.loads(sg_json)
        rg = ResourceGraph.loads(rg_json)
        return NetworkFunctionForwardingGraph(sg,rg)
            
    def map(self, new_rg, mapping_function,verbose=False):
        # Check if rg is different
        if self.rg.graph['id'] == new_rg.graph['id']:
            if verbose:
                print("Same RG as already used")
            # TODO: 2-low - Check if mapping is complete and pass only unmapped subgraph
        else:
            if verbose:
                print("Mapping to new RG")            
            self.rg.__dict__ = copy.deepcopy(new_rg.__dict__)
        
        mapping_function(self.sg, self.rg,verbose)

    def remap_nfs(self, new_rg, mapping_function):
        nfs=self.sg.subgraph( [n for n,attrdict in self.sg.node.items() 
                               if attrdict['type']=='NF' ] )
        # Check if rg is the same
        if self.rg.graph['id'] == new_rg.graph['id']:
            mapping_function(nfs, self.rg)
        else:
            print("Partial remapping to new RG not allowed")            

    def remap_saps(self, new_rg, mapping_function):
        saps=self.subgraph( [n for n,attrdict in self.node.items() 
                             if attrdict ['type'] == 'SAP' ])
        # Check if rg is the same
        if self.rg.graph['id'] == new_rg.graph['id']:
            mapping_function(saps, self.rg)
        else:
            print("Partial remapping to new RG not allowed")            

    def remap_links(self, new_rg, mapping_function):
        # Check if rg is different
        if self.rg.graph['id'] == new_rg.graph['id']:
            mapping_function(self.sg.edges(), self.rg)
        else:
            print("Partial remapping to new RG not allowed")            
                