#!/usr/bin/python -u
#
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


"""
TODO Adapt text
"""
from networkx.algorithms.flow.mincost import cost_of_flow

__author__ = 'Matthias Rost (mrost@inet.tu-berlin.de)'

import traceback
import json

from pprint import pformat

try:
  from escape.nffg_lib.nffg import NFFG, NFFGToolBox
except ImportError:
  import sys, os
  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                  "../escape/escape/nffg_lib/")))
  from nffg import NFFG, NFFGToolBox

#try:
import gurobipy
from gurobipy import GRB, Model, LinExpr
#except ImportError:
#    print "couldn't load gurobi!"

from Alg1_Core import CoreAlgorithm
import UnifyExceptionTypes as uet
import Alg1_Helper as helper

# object for the algorithm instance
alg = None



class Graph(object):
    """ represents a directed graph ( G = ( V , E) )
        is used for modeling the substrate as well as the request (service) graphs
    """

    def __init__(self, id):
        self.id = id
        self.graph = {}
        self.nodes = set()
        self.edges = set()
        self.out_neighbors = {}
        self.in_neighbors = {}


        self.edge_id_to_edge = {}

        #for storing general data
        self.graph = {}
        #for storing node related data
        self.node = {}
        #for storing edge related data
        self.edge = {}

        self.shortest_paths_costs = None
        self._shortest_paths_attribute_identifier = "cost"

    def add_node(self, node, **kwargs):
        self.nodes.add(node)
        self.out_neighbors[node] = []
        self.in_neighbors[node] = []
        self.node[node] = {}
        for key,value in kwargs.items():
            self.node[node][key] = value
            #self.node[node] = {}
            #self.node[node][k] = v


    def add_edge(self, id, tail, tail_port, head_port, head, bidirected=False, **kwargs):
        if (not tail in self.nodes) or (not head in self.nodes):
            raise Exception("Either node {} or node {} was not found while adding edge; "
                            "current node set is {}".format(tail, head, self.nodes))

        self._add_edge_one_direction(id, tail=tail, tail_port=tail_port, head_port=head_port, head=head, **kwargs)
        if bidirected:
            self._add_edge_one_direction(id + "_back", tail=head, tail_port=head_port, head_port=tail_port, head=tail, **kwargs )

    def _add_edge_one_direction(self, id, tail, tail_port, head_port, head, **kwargs):

        if id in self.edge_id_to_edge.values():
            raise Exception("The edge id {} is not unique.".format(id))

        if not tail in self.out_neighbors:
            self.out_neighbors[tail] = []
        if not head in self.in_neighbors:
            self.in_neighbors[head] = []

        self.edge_id_to_edge[id] = (tail, tail_port, head_port, head)

        self.out_neighbors[tail].append((tail, tail_port, head_port, head))
        self.in_neighbors[head].append((tail, tail_port, head_port, head))
        self.edges.add((tail, tail_port, head_port, head))
        self.edge[(tail,tail_port, head_port, head)] = {}
        for key,value in kwargs.items():
            self.edge[(tail, tail_port, head_port, head)][key] = value
            #self.edge[(tail,head)] = {}
            #self.edge[(tail,head)][key] = value

    def get_nodes(self):
        return self.nodes

    def get_edges(self):
        return self.edges

    def get_out_neighbors(self, node):
        return self.out_neighbors[node]

    def get_in_neighbors(self, node):
        return self.in_neighbors[node]

    def get_name(self):
        return self.name

    def get_number_of_nodes(self):
        return len(self.nodes)

    def get_number_of_edges(self):
        return len(self.edges)

    def get_shortest_paths_cost(self, node, other):
        if self.shortest_paths_costs is None:
            self.initialize_shortest_paths_costs()
        return self.shortest_paths_costs[node][other]

    def get_shortest_paths_cost_dict(self):
        if self.shortest_paths_costs is None:
            self.initialize_shortest_paths_costs()
        return self.shortest_paths_costs

    def initialize_shortest_paths_costs(self):

        #this can only be used if costs are defined as such for each edge
        self.shortest_paths_costs = {}

        for edge in self.edges:
            if self._shortest_paths_attribute_identifier not in self.edge[edge]:
                raise Exception("cost not defined for edge {}".format(edge))

        for u in self.nodes:
            self.shortest_paths_costs[u] = {}
            for v in self.nodes:
                if u is v:
                    self.shortest_paths_costs[u][v] = 0
                else:
                    self.shortest_paths_costs[u][v] = None


        for (u,u_p, v_p, v) in self.edges:
            if self.shortest_paths_costs[u][v] is None:
                self.shortest_paths_costs[u][v] = self.edge[(u,u_p,v_p,v)][self._shortest_paths_attribute_identifier]
            elif self.shortest_paths_costs[u][v] > self.edge[(u,u_p,v_p,v)][self._shortest_paths_attribute_identifier]:
                self.shortest_paths_costs[u][v] = self.edge[(u,u_p,v_p,v)][self._shortest_paths_attribute_identifier]

        for k in self.nodes:
            for u in self.nodes:
                for v in self.nodes:
                    if self.shortest_paths_costs[u][k] is not None and self.shortest_paths_costs[k][v] is not None:
                        cost_via_k = self.shortest_paths_costs[u][k] + self.shortest_paths_costs[k][v]
                        if self.shortest_paths_costs[u][v] is None or cost_via_k < self.shortest_paths_costs[u][v]:
                            self.shortest_paths_costs[u][v] = cost_via_k


    def check_connectivity(self):
        if self.shortest_paths_costs is None:
            self.initialize_shortest_paths_costs()
        for u in self.nodes:
            for v in self.nodes:
                if self.shortest_paths_costs[u][v] is None:
                    return False

        return True

    def print_it(self, including_shortest_path_costs=True, data=False):
        print "Graph {}".format(self.id)
        print "\tnodes: {}, edges: {}".format(self.nodes, self.edges)
        if data:
            print "additional data.."
            print "\tof graph: {}".format(self.graph)
            print "\tof nodes: {}".format(self.node)
            print "\tof edges: {}".format(self.edge)
        if including_shortest_path_costs:
            if self.shortest_paths_costs is None:
                self.initialize_shortest_paths_costs()
            print "Distances:"
            for u in self.nodes:
                for v in self.nodes:
                    print "\t{} to {}: {}".format(u,v,self.shortest_paths_costs[u][v])


class Substrate(Graph):
    """ representing the physical network,

        nodes have the following attributes
        - id of the node
        - type (an informal description which is not really used)
        - types: NF that can be hosted on this node
        - bandwidth, cpu, memory, storage, delay are directly taken from the respective SG nodes
        node attributes are accessed e.g. via self.node[snode]['cpu'] where snode denotes the id of a substrate node

        edges are 4 tuples (tail, tail_p, head_p, head), where tail and head denote the respective nodes and
        tail_p and head_p denote the respective ports of the respective nodes. edges have the following attributes.
        - delay, bandwidth
        these attributes are accessed e.g. via self.edge[sedge]['cpu'], where sedge denotes a 4-tuple
    """
    def __init__(self, id):
        super(self.__class__, self).__init__(id)
        self.types = set()
        self.nodes_supporting_type = {}

    def add_node(self, id, type, types, delay, bandwidth, cpu, memory, storage, cost=1):
        super(self.__class__, self).add_node(id,
                                             type = type,
                                             supported_types = types,
                                             delay = delay,
                                             bandwidth = bandwidth,
                                             cpu = cpu,
                                             memory = memory,
                                             storage = storage,
                                             cost = cost)

        types_set = set(types)
        if len(types_set) != len(types):
            raise Exception("Types need to be unique and may only occur once!")

        for supported_type in types:
            self.types.add(supported_type)

        for supported_type in types:
            if supported_type not in self.nodes_supporting_type:
                self.nodes_supporting_type[supported_type] = [id]
            else:
                self.nodes_supporting_type[supported_type].append(id)

    def add_edge(self, id, tail, tail_port, head_port, head, delay, bandwidth, cost=1):
        if(tail in self.nodes and head in self.nodes):
            #is always bidirected
            # (Balazs): Yes, but they are modeled as two directed links
            super(self.__class__, self).add_edge(id,
                                                 tail,
                                                 tail_port,
                                                 head_port,
                                                 head,
                                                 bidirected=False,
                                                 delay = delay,
                                                 bandwidth = bandwidth,
                                                 cost = cost)

    def reduce_available_resources_at_node(self, node, resources):
        #TODO CHECK THAT DELAY IS REALLY NOT TOUCHED
        self.node[node]['bandwidth'] -= resources.bandwidth
        self.node[node]['cpu']  -= resources.cpu
        self.node[node]['memory'] -= resources.mem
        self.node[node]['storage'] -= self.node[node]['storage']


    def get_path_delay(self, path):
        return sum(map(lambda x:self.get_edge_delay(x),path))

    def get_edge_delay(self, edge):
        return self.edge[edge]['delay']

    def get_edge_cost(self, edge):
        return self.edge[edge]['cost']

    def get_edge_bandwidth(self, edge):
        return self.edge[edge]['bandwidth']

    def get_nodes_supporting_type(self, type):
        return self.nodes_supporting_type[type]

class Request(Graph):

    """ represents a single SG

    nodes have the following attributes
    - id of the node
    - type: the corresponding NF-type or the static string 'SAP', if the node refers to a SAP
    - cpu, memory, storage denote the standard requirements for the respective NF
    - allowed_nodes may be set to restrict the potential mapping locations; e.g. given a SAP node, the only allowed_node will be the respective SAP

    edges are 4 tuples (tail, tail_p, head_p, head), where tail and head denote the respective (virtual) nodes and
    tail_p and head_p denote the respective ports of the respective nodes. edges have the following attributes.
    - bandwidth

    attributes are accessed as in the substrate graph
    """

    def __init__(self, id):
        super(self.__class__, self).__init__(id)
        self.graph['path_requirements'] = {}
        self.types = set()


    def add_node(self, id, ntype, cpu, memory, storage, allowed_snodes=None):
        super(self.__class__, self).add_node(id,
                                             type=ntype,
                                             cpu = cpu,
                                             memory = memory,
                                             storage = storage,
                                             allowed_nodes = allowed_snodes)
        self.types.add(ntype)


    def add_edge(self, id, tail, tail_port, head_port, head, bandwidth):
        if(tail in self.nodes and head in self.nodes):
            super(self.__class__, self).add_edge(id,
                                                 tail,
                                                 tail_port,
                                                 head_port,
                                                 head,
                                                 bidirected=False,
                                                 bandwidth=bandwidth)
        else:
            raise Exception("Either the tail ({}) or the head ({}) are not contained in the node set {}.".format(tail, head, self.nodes))

    def increase_bandwidth_requirement_edge(self, edge_id, bandwidth):
        edge = self.edge_id_to_edge[edge_id]
        self.edge[edge]['bandwidth'] += bandwidth

    def add_delay_requirement(self, id, path, delay):
        """ adds to a specific 'path' a delay requirement
            important: the order of edges must be respected """
        if(set(path) <= set(self.edge_id_to_edge.keys())):
            #translate ids to edges
            tuple_path = []
            for edge_id in path:
                tuple_path.append(self.edge_id_to_edge[edge_id])

            self.graph['path_requirements'][(id, tuple(tuple_path))] = delay
        else:
            raise Exception("Path contains edges which are NOT in request edges: {} vs. {}".format(path, self.edge_id_to_edge.keys()))

    def get_path_requirements(self):
        return self.graph['path_requirements']

    def get_required_types(self):
        return self.types

    def get_type_of_node(self, node):
        return self.node[node]['type']

    def get_allowed_nodes_for_node_raw(self, node):
        return self.node[node]['allowed_nodes']



def convert_req_to_request(req):


    print "creating request {}".format(req.id)
    result = Request(id=req.id)

    # ADD NODES
    # there exist three types: infras, saps, nfs

    #   infras: make sure that none of these exist
    for infra in req.infras:
        #Matthias: this is just to check that I got the concept right
        if infra.type != NFFG.TYPE_INFRA:
            raise Exception("infra node is no infra node: {} has type {}".format(infra.id, infra.type))
        raise Exception("request cannot contain infrastructure nodes: ".format(infra.id))

    #   saps
    for sap in req.saps:
        print "\t adding SAP node {} WITHOUT CONSIDERING CPU, MEMORY or STORAGE".format(sap.id)
        print "\t\t [" + ', '.join("%s: %s" % item for item in vars(sap).items()) + "]"

        if (sap.delay is not None and sap.delay > 0) or (sap.bandwidth is not None and sap.bandwidth > 0):
            raise Exception("Cannot handle SAP delay ({}) or bandwidth ({}).".format(sap.delay, sap.bandwidth))

        result.add_node(id=sap.id, ntype="SAP", cpu=0, memory=0, storage=0, allowed_snodes=[sap.name])

    #   nfs
    for nf in req.nfs:
        print "\t adding NF node {}".format(nf.id)

        print "\t\t [" + ', '.join("%s: %s" % item for item in vars(nf).items()) + "]"

        #check that bandwidth and delay are not used
        if nf.resources.delay is not None and nf.resources.delay > 0:
            raise Exception("Cannot handle NF delay requirements of NF {}".format(nf.id))

        if nf.resources.bandwidth is not None and nf.resources.bandwidth > 0:
            raise Exception("Cannot handle NF bandwidth requirements of NF {}".format(nf.id))

        result.add_node(id=nf.id, ntype=nf.functional_type, cpu=nf.resources.cpu, memory=nf.resources.mem, storage=nf.resources.storage, allowed_snodes=None)

    # ADD EDGES
    #   there exist four types: STATIC, DYNAMIC, SG and REQUIREMENT

    #   STATIC and DYNAMIC: make sure that these are not contained
    for link in req.links:
        #Matthias: this is just to check that I got the concept right
        if link.type != NFFG.TYPE_LINK_DYNAMIC and link.type != NFFG.TYPE_LINK_STATIC:
            raise Exception("link is neither dynamic nor static: {}".format(link.id))
        raise Exception("Request may not contain static or dynamic links: {}".format(link.id))

    #   SG
    for sg_link in req.sg_hops:

        print "\t adding edge {}".format(sg_link.id)

        print "\t\t [" + ', '.join("%s: %s" % item for item in vars(sg_link).items()) + "]"


        bw_req = sg_link.bandwidth
        if bw_req is None:
            bw_req = 0

        result.add_edge(id=sg_link.id, tail=sg_link.src.node.id, tail_port = sg_link.src.id, head_port=sg_link.dst.id, head=sg_link.dst.node.id, bandwidth=bw_req)

        if sg_link.delay is not None and sg_link.delay > 0:
            #add new novel constraint
            result.add_delay_requirement(id="sg_link_req_{}".format(sg_link.id), path=[sg_link.id], delay=sg_link.delay)

    for path_req in req.reqs:

        print "\t handling path requirement {}".format(path_req.id)

        print "\t\t [" + ', '.join("%s: %s" % item for item in vars(path_req).items()) + "]"

        result.add_delay_requirement(id=path_req.id, path=path_req.sg_path, delay=path_req.delay)

        if path_req.bandwidth is not None and path_req.bandwidth > 0:
            print "\t\t there exists an additional bandwidth requirement of {} units. Augmenting every contained link with the required bandwidth.".format(path_req.bandwidth)

            #TODO I AM UNSURE WHETHER THE FOLLOWING IS CORRECT
            for edge_id in path_req.sg_path:

                edge = result.edge_id_to_edge[edge_id]
                bw_req_before = result.edge[edge]['bandwidth']
                result.edge[edge]['bandwidth'] += path_req.bandwidth
                print "\t\t\t increasing bandwidth along edge {} (i.e. {}) from {} to {}".format(edge_id, edge, bw_req_before, result.edge[edge]['bandwidth'])


    print "created request looks like .."

    result.print_it(including_shortest_path_costs=False, data=True)

    print "\n\n"

    return result





def convert_nffg_to_substrate(nffg):

    print "creating substrate {}".format(nffg.id)
    result = Substrate(id=nffg.id)

    print "\t [" + ', '.join("%s: %s" % item for item in vars(nffg).items()) + "]"

    # ADD NODES
    # there exist three types: infras, saps, nfs

    #   infras: make sure that these are added with the right resources

    for infra in nffg.infras:

        print "\t adding node {}".format(infra.id)

        print "\t\t [" + ', '.join("%s: %s" % item for item in vars(infra).items()) + "]"

        delay = nffg.calculate_available_node_res('delay')

        result.add_node(id=infra.id,
                        type="INFRA",
                        types=infra.supported,
                        delay=infra.resources.delay,
                        bandwidth=infra.resources.bandwidth,
                        cpu=infra.resources.cpu,
                        memory=infra.resources.mem,
                        storage=infra.resources.storage)

        # taking into account allocations..
        for vnf in nffg.running_nfs(infra.id):
            print "\t\t\t reducing resources of node {} according to resources {} of VNF {}".format(infra.id, vnf.resources, vnf.id)
            result.reduce_available_resources_at_node(infra.id, vnf.resources)

        print "\t\t final resources of node {} are {}".format(infra.id, result.node[infra.id])

        #TODO: take into account the link allocations



     #   saps
    for sap in nffg.saps:
        print "\t adding SAP node {} WITHOUT CONSIDERING CPU, MEMORY, BANDWIDTH OR DELAY".format(sap.id)
        print "\t\t [" + ', '.join("%s: %s" % item for item in vars(sap).items()) + "]"

        #if (sap.delay is not None and sap.delay > 0) or (sap.bandwidth is not None and sap.bandwidth > 0):
        #    raise Exception("Cannot handle SAP delay ({}) or bandwidth ({}).".format(sap.delay, sap.bandwidth))

        if sap.delay is not None and sap.delay > 0:
            print "\t\t ignoring {} delay at SAP {} as this is not of importance here; setting delay to 0 ".format(sap.delay, sap.id)
        print "\t\t ignoring {} bandwidth at SAP {} as this is not of importance here; setting bandwidth to inf".format(sap.bandwidth, sap.id)


        result.add_node(id=sap.id,
                        type="SAP",
                        types=["SAP"],
                        delay=0.0,
                        bandwidth=GRB.INFINITY,
                        cpu=0,
                        memory=0,
                        storage=0)

    #   nfs are not added to the substrate graph!


    # ADD EDGES

    for edge_link in nffg.links:

        if edge_link.type == "STATIC":

            print "\t adding static link {}".format(edge_link.id)
            print "\t\t [" + ', '.join("%s: %s" % item for item in vars(edge_link).items()) + "]"

            result.add_edge(id=edge_link.id,
                            tail=edge_link.src.node.id,
                            tail_port=edge_link.src.id,
                            head_port=edge_link.dst.id,
                            head=edge_link.dst.node.id,
                            delay=edge_link.delay,
                            bandwidth=edge_link.bandwidth)

        else:
            print "\t disregarding {} link {}".format(edge_link.type, edge_link.id)


    print "created substrate looks like .."

    result.print_it(including_shortest_path_costs=False, data=True)

    return result


class Scenario(object):
    """
        Binds together a substrate and a set of requests
    """

    def __init__(self, substrate, requests):
        self.substrate = substrate
        self.requests = requests

    def compute_allowed_nodes(self, request, vnode):
        substrate_nodes = self.substrate.get_nodes_supporting_type(request.get_type_of_node(vnode))
        allowed_nodes_raw = request.get_allowed_nodes_for_node_raw(vnode)
        if allowed_nodes_raw is None:
            return substrate_nodes
        else:
            if set(allowed_nodes_raw) <= set(substrate_nodes):
                return allowed_nodes_raw
            else:
                raise Exception("Couldn't resolve allowed nodes for node {} of request".format(vnode, request.id))

    #TODO add some options for realizing different objectives




def construct_name(name, req_id=None, vnode=None, snode=None, vedge=None, sedge=None):
    if req_id is not None:
        name += "_req[{}]".format(req_id)
    if vnode is not None:
        name += "_vnode[{}]".format(vnode)
    if snode is not None:
        name += "_snode[{}]".format(snode)
    if vedge is not None:
        name += "_vedge[{}]".format(shorten_edge_representation_if_necessary(vedge))
    if sedge is not None:
        name += "_sedge[{}]".format(shorten_edge_representation_if_necessary(sedge))
    return name.replace(" ", "")

def shorten_edge_representation_if_necessary(edge):
    etail, etail_p, ehead_p, ehead = edge
    if isinstance(etail_p, basestring) and len(etail_p) > 20:
        etail_p = etail_p[0:7] + "-...-" + etail_p[-7:]
    if isinstance(ehead_p, basestring) and len(ehead_p) > 20:
        ehead_p = ehead_p[0:7] + "-...-" + ehead_p[-7:]
    return (etail, etail_p, ehead_p, ehead)

class ModelCreator(object):

    """
        interface for gurobi; NOT of interest in the current state
    """

    def __init__(self, scenario):
        #storing the essential data
        self.scenario = scenario
        self.substrate = scenario.substrate
        self.requests = scenario.requests

        #for easier lookup which nfs can be placed onto which substrate nodes
        self.allowed_nodes_copy = {}                    #a dict of req --> vnode --> [snodes]
        #as vedges may be embedded on a single node, we use the following dict to store the respective potential node embeddings
        # self.potential_vedge_embeddings_on_nodes = {}   #a dict of req --> vedge --> [snodes]

        # gurobi interface
        self.model = None
        self.status = None

        # dictionaries with the variables for value lookup
        self.var_embedding_decision = {}
        self.var_node_mapping = {}
        self.var_edge_mapping = {}
        self.var_node_load = {}
        self.var_edge_load = {}
        self.var_path_delay = {}
        # self.var_vedge_to_snode_mapping = {}

        # the final solution (if any was found)
        self.solution = None



    def init_model_creator(self):

        self.preprocess()

        #create the gurobi model
        self.model = gurobipy.Model("test")

        #create the variables
        self.create_variables()

        #necessary for accessing the variables after creation
        self.model.update()

        #create constraints and the objective
        self.create_constraints()
        self.plugin_objective_maximize_number_of_embedded_requests_and_minimize_costs()

        #final update of the model to reflect the addition of the constraints
        self.model.update()


    def run_milp(self):

        self.model.write("lala.lp")

        self.model.optimize()

        #read meta data and store it ..
        status = self.model.getAttr("Status")
        objVal = None
        objBound = GRB.INFINITY
        objGap = GRB.INFINITY
        solutionCount = self.model.getAttr("SolCount")

        if solutionCount > 0:
            objVal = objValue = self.model.getAttr("ObjVal")
            # interestingly, MIPGap and ObjBound cannot be accessed when there are no variables and the MIP is infeasible..
            objGap = self.model.getAttr("MIPGap")

        if isFeasibleStatus(status):
            objBound = self.model.getAttr("ObjBound")

        self.status = GurobiStatus(status=status,
                                   solCount=solutionCount,
                                   objValue=objVal,
                                   objGap=objGap,
                                   objBound=objBound,
                                   integralSolution=True)

        if self.status.isFeasible():
            print "\t MIP did produce a solution! Will start to parse the solution.."
            self._obtain_solution()

        else:
            print "\t MIP did not produce a solution!"

        return self.status


    def preprocess(self):
        for req in self.requests:
            self.allowed_nodes_copy[req] = {}
            for vnode in req.nodes:
                self.allowed_nodes_copy[req][vnode] = self.scenario.compute_allowed_nodes(req, vnode)

        # for req in self.requests:
        #     self.potential_vedge_embeddings_on_nodes[req] = {}
        #
        #     for vedge in req.edges:
        #         self.potential_vedge_embeddings_on_nodes[req][vedge] = []
        #
        #         vtail, vtail_p, vhead_p, vhead = vedge
        #
        #         for snode in self.substrate.nodes:
        #             if snode in self.allowed_nodes_copy[req][vtail] and snode in self.allowed_nodes_copy[req][vhead]:
        #                 self.potential_vedge_embeddings_on_nodes[req][vedge].append(snode)






    def create_variables(self):

        #for each request a decision variable is created

        for req in self.requests:
            variable_id = construct_name("embedding_decision", req_id=req.id)
            self.var_embedding_decision[req] = self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.BINARY, name=variable_id)

        for req in self.requests:
            self.var_node_mapping[req] = {}
            for vnode in req.nodes:
                self.var_node_mapping[req][vnode] = {}
                allowed_nodes = self.allowed_nodes_copy[req][vnode]
                for snode in allowed_nodes:
                    variable_id = construct_name("node_mapping", req_id=req.id, vnode=vnode, snode=snode)
                    self.var_node_mapping[req][vnode][snode] = self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.BINARY, name=variable_id)

        for req in self.requests:
            self.var_edge_mapping[req] = {}
            #TODO the above assumes that arbitrary paths are possible. However, this is not the case as delay constraints might be enforced
            #TODO Some easy (presolving) optimizations would hence be applicable.
            for vedge in req.edges:
                self.var_edge_mapping[req][vedge] = {}
                for sedge in self.substrate.edges:
                    variable_id = construct_name("edge_mapping", req_id=req.id, vedge=vedge, sedge=sedge)
                    self.var_edge_mapping[req][vedge][sedge] = self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.BINARY, name=variable_id)

        node_resources = ["bandwidth", "cpu", "memory", "storage"]
        for snode in self.substrate.nodes:
            self.var_node_load[snode] = {}
            for resource in node_resources:
                variable_id = construct_name("node_load", snode=snode) + "_" + resource
                self.var_node_load[snode][resource] = self.model.addVar(lb=0.0, ub=GRB.INFINITY, obj=0.0, vtype=GRB.CONTINUOUS, name=variable_id)

        for sedge in self.substrate.edges:
            variable_id = construct_name("edge_load", sedge=sedge)
            self.var_edge_load[sedge] = self.model.addVar(lb=0.0, ub=GRB.INFINITY, obj=0.0, vtype=GRB.CONTINUOUS, name=variable_id)

        for req in self.requests:
            self.var_path_delay[req] = {}
            for id, _ in req.graph["path_requirements"].keys():
                variable_id = construct_name("path_delay", req_id=req.id) + "_" + str(id)
                self.var_path_delay[req][id] = self.model.addVar(lb=0.0, ub=GRB.INFINITY, obj=0.0, vtype=GRB.CONTINUOUS, name=variable_id)

        # for req in self.requests:
        #     self.var_vedge_to_snode_mapping[req] = {}
        #
        #     for vedge in req.edges:
        #         self.var_vedge_to_snode_mapping[req][vedge] = {}
        #
        #         for snode in self.potential_vedge_embeddings_on_nodes[req][vedge]:
        #             variable_id = construct_name("vedge_mapping_on_snode", req_id=req.id, vedge=vedge, snode=snode)
        #             self.var_vedge_to_snode_mapping[req][vedge][sedge] = self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.BINARY, name=variable_id)


    def create_constraints(self):
        self.create_constraint_request_embedding_triggers_node_embeddings()
        self.create_constraint_induce_and_preserve_unit_flows()
        #self.create_constraint_set_vedge_via_snode_variables() #TODO currently not necessary
        self.create_constraint_node_loads_standard()
        self.create_constraint_node_load_bandwidth()
        self.create_constraint_edge_load_bandwidth()
        self.create_constraint_delay_requirements()


    def create_constraint_request_embedding_triggers_node_embeddings(self):
        for req in self.requests:
            for vnode in req.nodes:
                expr = LinExpr([(1.0, self.var_node_mapping[req][vnode][snode])
                                for snode in self.allowed_nodes_copy[req][vnode]]
                               +
                               [(-1.0, self.var_embedding_decision[req])])
                constr_name = construct_name("request_embedding_triggers_node_embeddings", req_id=req.id, vnode=vnode)
                self.model.addConstr(expr, GRB.EQUAL, 0.0, name=constr_name)


    def create_constraint_induce_and_preserve_unit_flows(self):
        for req in self.requests:
            for vedge in req.edges:
                for snode in self.substrate.nodes:

                    expr = LinExpr([(-1.0, self.var_edge_mapping[req][vedge][sedge]) for sedge in self.substrate.in_neighbors[snode]]
                                   +
                                   [(+1.0, self.var_edge_mapping[req][vedge][sedge]) for sedge in self.substrate.out_neighbors[snode]])

                    vtail,_,_,vhead = vedge

                    if snode in self.allowed_nodes_copy[req][vtail]:
                        expr.addTerms(-1.0, self.var_node_mapping[req][vtail][snode])

                    if snode in self.allowed_nodes_copy[req][vhead]:
                        expr.addTerms(+1.0, self.var_node_mapping[req][vhead][snode])

                    constr_name = construct_name("induce_and_preserve_unit_flows", req_id=req.id, vedge=vedge, snode=snode)

                    self.model.addConstr(expr, GRB.EQUAL, 0.0, name=constr_name)

    # def create_constraint_set_vedge_via_snode_variables(self):
    #
    #     for req in self.requests:
    #         for vedge in req.edges:
    #
    #             vtail, vtail_p, vhead_p, vhead = vedge
    #
    #             for snode in self.potential_vedge_embeddings_on_nodes[req][vedge]:
    #
    #                 expr = LinExpr([(+1.0, self.var_vedge_to_snode_mapping[req][vedge][snode]),
    #                                 (-1.0, self.var_node_mapping[req][vtail][snode])])
    #
    #                 constr_name = construct_name("set_vedge_via_snode_1", req_id=req.id, vedge=vedge, snode=snode)
    #
    #                 self.model.addConstr(expr, GRB.LESS_EQUAL, 0.0, name=constr_name)
    #
    #
    #                 expr = LinExpr([(+1.0, self.var_vedge_to_snode_mapping[req][vedge][snode]),
    #                                 (-1.0, self.var_node_mapping[req][vhead][snode])])
    #
    #                 constr_name = construct_name("set_vedge_via_snode_2", req_id=req.id, vedge=vedge, snode=snode)
    #
    #                 self.model.addConstr(expr, GRB.LESS_EQUAL, 0.0, name=constr_name)
    #
    #
    #                 expr = LinExpr([(+1.0, self.var_vedge_to_snode_mapping[req][vedge][snode]),
    #                                 (-1.0, self.var_node_mapping[req][vtail][snode]),
    #                                 (-1.0, self.var_node_mapping[req][vtail][snode])])
    #
    #                 constr_name = construct_name("set_vedge_via_snode_3", req_id=req.id, vedge=vedge, snode=snode)
    #
    #                 self.model.addConstr(expr, GRB.GREATE_EQUAL, -1.0, name=constr_name)


    def create_constraint_node_loads_standard(self):
        node_properties = ["cpu", "memory", "storage"]

        for node_property in node_properties:
            for snode in self.substrate.nodes:

                expr = LinExpr([(req.node[vnode][node_property], self.var_node_mapping[req][vnode][snode])
                                for req in self.requests for vnode in req.nodes if snode in self.allowed_nodes_copy[req][vnode]])

                expr.addTerms(-1.0, self.var_node_load[snode][node_property])

                constr_name = construct_name("set_node_load_var_standard", snode=snode) + "_{}".format(node_property)

                self.model.addConstr(expr, GRB.EQUAL, 0.0,  constr_name)

                expr = LinExpr([(1.0, self.var_node_load[snode][node_property])])

                constr_name = construct_name("bound_node_load_standard", snode=snode) + "_{}".format(node_property)

                self.model.addConstr(expr, GRB.LESS_EQUAL, self.substrate.node[snode][node_property],  constr_name)


    def create_constraint_node_load_bandwidth(self):
        for snode in self.substrate.nodes:

            expr = LinExpr( [
                                (req.edge[vedge]['bandwidth'], self.var_edge_mapping[req][vedge][sedge])
                                    for req in self.requests
                                    for vedge in req.edges
                                    for sedge in self.substrate.in_neighbors[snode]
                            ] +
                            [
                                (req.edge[(vtail, vtail_p, vhead_p, vhead)]['bandwidth'], self.var_node_mapping[req][vtail][snode])
                                    for req in self.requests
                                    for (vtail, vtail_p, vhead_p, vhead) in req.edges
                                    if snode in self.allowed_nodes_copy[req][vtail]
                            ]
                           )

            expr.addTerms(-1.0, self.var_node_load[snode]["bandwidth"])

            constr_name = construct_name("set_node_load_var_bw", snode=snode)

            self.model.addConstr(expr, GRB.EQUAL, 0.0,  constr_name)

            expr = LinExpr([(1.0, self.var_node_load[snode]["bandwidth"])])

            constr_name = construct_name("bound_node_load_bandwidth", snode=snode)

            self.model.addConstr(expr, GRB.LESS_EQUAL, self.substrate.node[snode]['bandwidth'],  constr_name)



    def create_constraint_edge_load_bandwidth(self):
        for sedge in self.substrate.edges:
            expr = LinExpr([(req.edge[vedge]['bandwidth'], self.var_edge_mapping[req][vedge][sedge])
                            for req in self.requests
                            for vedge in req.edges])


            expr.addTerms(-1.0, self.var_edge_load[sedge])

            constr_name = construct_name("set_edge_load", sedge=sedge)

            self.model.addConstr(expr, GRB.EQUAL, 0.0,  constr_name)

            expr = LinExpr(1.0, self.var_edge_load[sedge])

            constr_name = construct_name("bound_edge_load", sedge=sedge)

            self.model.addConstr(expr, GRB.LESS_EQUAL, self.substrate.edge[sedge]['bandwidth'],  constr_name)


    def create_constraint_delay_requirements(self):
        for req in self.requests:

            for (id, tuple_path), delay_bound in req.get_path_requirements().iteritems():
                expr = LinExpr()
                for vedge in tuple_path:

                    vtail, vtail_p, vhead_p, vhead = vedge

                    sub_expr = LinExpr( [
                                            (self.substrate.edge[(stail, stail_p, shead_p, shead)]['delay']
                                             + self.substrate.node[shead]['delay'],
                                            self.var_edge_mapping[req][vedge][(stail, stail_p, shead_p, shead)] )
                                                for (stail, stail_p, shead_p, shead) in self.substrate.edges
                                        ] +
                                        [
                                            (self.substrate.node[snode]['delay'], self.var_node_mapping[req][vtail][snode])
                                                for snode in self.allowed_nodes_copy[req][vtail]
                                        ]
                                       )

                    expr.add(sub_expr)

                expr.addTerms(-1.0, self.var_path_delay[req][id])

                constr_name = construct_name("set_delay", req_id=req.id) + "_id[{}]".format(id)

                self.model.addConstr(expr, GRB.EQUAL, 0.0, constr_name)

                expr = LinExpr(1.0, self.var_path_delay[req][id])

                constr_name = construct_name("bound_delay", req_id=req.id) + "_id[{}]".format(id)

                self.model.addConstr(expr, GRB.LESS_EQUAL, delay_bound, constr_name)



    def plugin_objective_maximize_number_of_embedded_requests(self):
        expr = LinExpr([(1.0, self.var_embedding_decision[req]) for req in self.requests])
        self.model.setObjective(expr, GRB.MAXIMIZE)


    def plugin_objective_maximize_number_of_embedded_requests_and_minimize_costs(self):

        max_edge_cost = 0.0
        for sedge in self.substrate.edges:
            max_edge_cost += self.substrate.edge[sedge]['cost'] * self.substrate.edge[sedge]['bandwidth']

        profit_expr = LinExpr([(2.0 * max_edge_cost, self.var_embedding_decision[req]) for req in self.requests])
        cost_expr = LinExpr([(-self.substrate.edge[sedge]['cost'], self.var_edge_load[sedge])
                                for sedge in self.substrate.edges])

        profit_expr.add(cost_expr)

        self.model.setObjective(profit_expr, GRB.MAXIMIZE)



    def _obtain_solution(self):
        if not isFeasibleStatus(self.status):
            raise Exception("Gurobi's solution does seem to be infeasible. Cannot parse the data!")

        self.solution = ScenarioSolution(self.scenario)

        for req in self.requests:

            mapping = None

            if self.var_embedding_decision[req].X > 0.5:
                # this means that the request is embedded
                mapping = Mapping(req, self.substrate, self.scenario, is_embedded=True)

                for vnode in req.nodes:
                    for snode, var in self.var_node_mapping[req][vnode].iteritems():
                        if var.X > 0.5:
                            mapping.map_node(vnode, snode)

                for vedge in req.edges:

                    #perform bfs to find embedding

                    parent = {}

                    vstart, vstart_p, vend_p, vend = vedge

                    start_node = mapping.vnode_to_snode[vstart]
                    end_node = mapping.vnode_to_snode[vend]

                    if start_node == end_node:
                        # we do not need to perform any search: the virtualized functions are directly connected via the same node
                        mapping.map_edge(vedge, [])
                    else:

                        queue = [start_node]

                        #perform search
                        while len(queue) > 0:
                            current_node = queue.pop(0)
                            if current_node == end_node:
                                break
                            for (stail, stail_p, shead_p, shead) in self.substrate.get_out_neighbors(current_node):
                                if not shead in parent and self.var_edge_mapping[req][vedge][(stail, stail_p, shead_p, shead)].X > 0.5:
                                    parent[shead] = (stail, stail_p, shead_p, shead)
                                    queue.append(shead)

                        #perform backtracking
                        if end_node not in parent:
                            raise Exception("Couldn't backtrack path: {}".format(parent))

                        substrate_edge_path = []
                        current_node = end_node
                        while True:
                            pred, _,_,_ = parent[current_node]
                            substrate_edge_path.append(parent[current_node])
                            current_node = pred
                            if current_node == start_node:
                                break

                        mapping.map_edge(vedge, list(reversed(substrate_edge_path)))

                        #TODO search whether other stuff is available!
                        edge_counter = 0
                        for sedge in self.substrate.edges:
                            if self.var_edge_mapping[req][vedge][(stail, stail_p, shead_p, shead)].X > 0.5:
                                edge_counter += 1

                        print edge_counter, len(substrate_edge_path)
                        if edge_counter > len(substrate_edge_path):
                            print "there might exist some unnecessary cycles!"

                for (id, vedge_path) in req.graph['path_requirements']:
                    mapping.set_raw_path_delay(id, vedge_path, self.var_path_delay[req][id].X)


            else:
                mapping = Mapping(req, self.substrate, self.scenario, is_embedded=False)

            print "\t storing the solution for request {}".format(req.id)
            self.solution.set_mapping_of_request(req, mapping)
            print mapping.vnode_to_snode
            print mapping.vedge_to_spath


        node_resources = ["bandwidth", "cpu", "memory", "storage"]

        for snode in self.substrate.nodes:
            for resource in node_resources:
                self.solution.set_raw_node_load(snode, resource, self.var_node_load[snode][resource].X)

        for sedge in self.substrate.edges:
            self.solution.set_raw_edge_load(sedge, self.var_edge_load[sedge].X)




class Mapping(object):

    """ represents the mapping of a single request onto the substrate
        may also represent the "non-embedding", if is_embedded is not set.

    """

    def __init__(self, request, substrate, scenario, is_embedded=True):
        self.request = request
        self.substrate = substrate
        self.scenario = scenario
        self.is_embedded = is_embedded

        self.vnode_to_snode = {}
        self.vedge_to_spath = {}

        self.snode_to_hosted_vnodes = {}
        self.snode_to_incident_vedges = {}
        self.sedge_to_vedges = {}

        self.raw_path_delay = {}


    def map_node(self, vnode, snode):
        if not self.is_embedded:
            raise Exception("If the request is not embedded, it cannot be mapped!")

        if vnode not in self.request.nodes:
            raise Exception("NF {} does not belong to the request {}".format(vnode, self.request.id))
        if snode not in self.substrate.nodes:
            raise Exception("Substrate node {} does not belong to the substrate {}".format(snode, self.substrate.id))
        if snode not in self.scenario.compute_allowed_nodes(self.request, vnode):
            raise Exception("Substrate node {} does not match required type of vnode {} of request {}".format(snode, vnode, self.request.id))

        self.vnode_to_snode[vnode] = snode

        if not snode in self.snode_to_hosted_vnodes:
            self.snode_to_hosted_vnodes[snode] = [vnode]
        else:
            self.snode_to_hosted_vnodes[snode].append(vnode)


    def map_edge(self, vedge, substrate_edge_path):
        if not self.is_embedded:
            raise Exception("If the request is not embedded, it cannot be mapped!")

        if vedge not in self.request.edges:
            raise Exception("vedge {} does not belong to the request {}".format(vedge, self.request.id))

        for sedge in substrate_edge_path:
            if sedge not in self.substrate.edges:
                raise Exception("Substrate edge {} does not belong to the substrate {}".format(sedge, self.substrate.id))

        vtail, vtail_p, vhead_p, vhead = vedge

        last_snode = None
        for index, (stail,stail_p, shead_p, shead) in enumerate(substrate_edge_path):
            if index == 0:
                if vtail not in self.vnode_to_snode:
                    raise Exception("Before adding mappings of edges, please add the node mappings: vnode {}".format(vtail))
                if stail != self.vnode_to_snode[vtail]:
                    raise Exception("The substrate path {} does not start at the substrate node {} onto which the tail of the virtual link {} was mapped".format(substrate_edge_path, stail, vedge))
                last_snode = shead

            elif index > 0:
                if last_snode != stail:
                    raise Exception("{} is not a path!".format(substrate_edge_path))
                last_snode = shead

                if index == len(substrate_edge_path) -1:
                    if vhead not in self.vnode_to_snode:
                        raise Exception("Before adding mappings of edges, please add the node mappings: vnode {}".format(vhead))
                    if shead != self.vnode_to_snode[vhead]:
                        raise Exception("The substrate path {} does not end at the substrate node {} onto which the head of the virtual link {} was mapped".format(substrate_edge_path, shead, vedge))


        self.vedge_to_spath[vedge] = substrate_edge_path

        #set mapping of edges to vedges
        for sedge in substrate_edge_path:
            if not sedge in self.sedge_to_vedges:
                self.sedge_to_vedges[sedge] = [vedge]
            else:
                self.sedge_to_vedges[sedge].append(vedge)

        if len(substrate_edge_path) > 0:

            #set mapping of substrate nodes to vedges
            for index, sedge in enumerate(substrate_edge_path):

                stail,stail_p, shead_p, shead = sedge

                if index == 0:
                    if not stail in self.snode_to_incident_vedges:
                        self.snode_to_incident_vedges[stail] = [vedge]
                    else:
                        self.snode_to_incident_vedges[stail].append(vedge)

                if not shead in self.snode_to_incident_vedges:
                    self.snode_to_incident_vedges[shead] = [vedge]
                else:
                    self.snode_to_incident_vedges[shead].append(vedge)
        else:
            #both the head and the tail of the vedge are mapped onto the same node..
            if self.vnode_to_snode[vtail] != self.vnode_to_snode[vhead]:
                raise Exception("Empty edge mapping implies being hosted on the same node!")
            snode = self.vnode_to_snode[vtail]
            if snode not in self.snode_to_incident_vedges:
                self.snode_to_incident_vedges[snode] = [vedge]
            else:
                self.snode_to_incident_vedges[snode].append(vedge)


    def set_raw_path_delay(self, id, vedge_path, delay):
        if (id, vedge_path) not in self.request.graph['path_requirements']:
            raise Exception("Cannot set raw path delay for path {} with id {} as it is not part of the request.".format(vedge_path, id))
        if (id, vedge_path) not in self.raw_path_delay:
            self.raw_path_delay[(id,vedge_path)] = delay
        else:
            raise Exception("Raw path delay of request {} and id {} was already set.".format(self.request.id, id))


    def get_hosted_vnodes_on_snode(self, snode):
        if snode not in self.snode_to_hosted_vnodes:
            return []
        return self.snode_to_hosted_vnodes[snode]

    def get_hosted_vedges_on_sedge(self, sedge):
        if sedge not in self.sedge_to_vedges:
            return []
        return self.sedge_to_vedges[sedge]

    def get_hosted_vedges_using_snode(self, snode):
        if snode not in self.snode_to_incident_vedges:
            return []
        return self.snode_to_incident_vedges[snode]

    def print_mapping(self):
        print "\t Mapping of Request {}".format(self.request.id)
        if self.is_embedded:
            for vnode in self.request.nodes:
                print "\t\t Node {} --> {}".format(vnode, self.vnode_to_snode[vnode])
            for vedge in self.request.edges:
                print "\t\t Edge {} --> {}".format(vedge, self.vedge_to_spath[vedge])


def isFeasibleStatus(status):
    result = True
    if status == GurobiStatus.INFEASIBLE:
        result = False
    elif status == GurobiStatus.INF_OR_UNBD:
        result = False
    elif status == GurobiStatus.UNBOUNDED:
        result = False
    elif status == GurobiStatus.LOADED:
        result = False

    return result


class GurobiStatus(object):
    LOADED = 1  # Model is loaded, but no solution information is available.
    OPTIMAL = 2  # Model was solved to optimality (subject to tolerances), and an optimal solution is available.
    INFEASIBLE = 3  # Model was proven to be infeasible.
    INF_OR_UNBD = 4  # Model was proven to be either infeasible or unbounded. To obtain a more definitive conclusion, set the DualReductions parameter to 0 and reoptimize.
    UNBOUNDED = 5  # Model was proven to be unbounded. Important note: an unbounded status indicates the presence of an unbounded ray that allows the objective to improve without limit. It says nothing about whether the model has a feasible solution. If you require information on feasibility, you should set the objective to zero and reoptimize.
    CUTOFF = 6  # Optimal objective for model was proven to be worse than the value specified in the Cutoff parameter. No solution information is available.
    ITERATION_LIMIT = 7  # Optimization terminated because the total number of simplex iterations performed exceeded the value specified in the IterationLimit parameter, or because the total number of barrier iterations exceeded the value specified in the BarIterLimit parameter.
    NODE_LIMIT = 8  # Optimization terminated because the total number of branch-and-cut nodes explored exceeded the value specified in the NodeLimit parameter.
    TIME_LIMIT = 9  # Optimization terminated because the time expended exceeded the value specified in the TimeLimit parameter.
    SOLUTION_LIMIT = 10  # Optimization terminated because the number of solutions found reached the value specified in the SolutionLimit parameter.
    INTERRUPTED = 11  # Optimization was terminated by the user.
    NUMERIC = 12  # Optimization was terminated due to unrecoverable numerical difficulties.
    SUBOPTIMAL = 13  # Unable to satisfy optimality tolerances; a sub-optimal solution is available.
    IN_PROGRESS = 14  # A non-blocking optimization call was made (by setting the NonBlocking parameter to 1 in a Gurobi Compute Server environment), but the associated optimization run is not yet complete.

    def __init__(self,
                 status=1,
                 solCount=0,
                 objValue=gurobipy.GRB.INFINITY,
                 objBound=gurobipy.GRB.INFINITY,
                 objGap=gurobipy.GRB.INFINITY,
                 integralSolution=True
                 ):
        self.solCount = solCount
        self.status = status
        self.objValue = objValue
        self.objBound = objBound
        self.objGap = objGap
        self.integralSolution = integralSolution

    def _convertInfinityToNone(self, value):
        if value is gurobipy.GRB.INFINITY:
            return None
        return value

    def isIntegralSolution(self):
        return self.integralSolution

    def getObjectiveValue(self):
        return self._convertInfinityToNone(self.objValue)

    def getObjectiveBound(self):
        return self._convertInfinityToNone(self.objBound)

    def getMIPGap(self):
        return self._convertInfinityToNone(self.objGap)

    def hasFeasibleStatus(self):
        return isFeasibleStatus(self.status)

    def isFeasible(self):
        feasibleStatus = self.hasFeasibleStatus()
        result = feasibleStatus
        if not self.integralSolution and feasibleStatus:
            return True
        elif self.integralSolution:
            result = self.solCount > 0
            if result and not feasibleStatus:
                raise Exception("Solutions exist, but the status ({}) indicated an infeasibility.".format(self.status))
            return result

        return result

    def isOptimal(self):
        if self.status == self.OPTIMAL:
            return True
        else:
            return False

    def __str__(self):
        return "solCount: {0}; status: {1}; objValue: {2}; objBound: {3}; objGap: {4}; integralSolution: {5}; ".format(self.solCount, self.status, self.objValue, self.objBound, self.objGap, self.integralSolution)


def check_deviation(text, value1, value2, eps=0.001):
    if abs(value2) < 0.001:
        if abs(value1 - value2) + abs(value2- value1) > eps:
            raise Exception(text + " {} vs. {}".format(value1, value2))
    else:
        if (value1 / value2 > 1.0 + eps) or (value1 / value2 < 1.0 - eps):
            raise Exception(text + " {} vs. {}".format(value1, value2))

class ScenarioSolution(object):

    def __init__(self, scenario):
        self.scenario = scenario
        self.substrate = scenario.substrate
        self.requests = scenario.requests

        self.mapping_of_request = {}

        self.raw_node_load = {}
        self.raw_edge_load = {}

    def set_mapping_of_request(self, request, mapping):
        if request not in self.mapping_of_request:
            self.mapping_of_request[request] = mapping
        else:
            raise Exception("The request {} was already mapped!".format(request.id))

    def set_raw_node_load(self, snode, resource, value):
        if snode not in self.raw_node_load:
            self.raw_node_load[snode] = {}
        if resource in self.raw_node_load[snode]:
            raise Exception("Raw node load for resource {} on node {} was already set.".format(resource, snode))
        self.raw_node_load[snode][resource] = value

    def set_raw_edge_load(self, sedge, value):
        if sedge not in self.raw_node_load:
            self.raw_edge_load[sedge] = value
        else:
            raise Exception("Raw edge load on edge {} was already set.".format(sedge))


    def validate_solution(self, debug_output = True):

        print "starting to validate solution..."

        #   NODES

        #       check the three basic node properties, i.e. cpu, mem, storage

        basic_node_resources = ['cpu', 'memory', 'storage']

        for resource in basic_node_resources:
            if debug_output:
                "\t checking {} allocations on nodes".format(resource)
            for snode in self.substrate.nodes:
                used_resources = 0

                for req in self.requests:
                    mapping = self.mapping_of_request[req]
                    if mapping.is_embedded:
                        for vnode in mapping.get_hosted_vnodes_on_snode(snode):
                            used_resources += req.node[vnode][resource]

                if self.substrate.node[snode][resource] < used_resources:
                    raise Exception("The capacity of resource {} on substrate node {} is exceeded by {} many units.".format(resource,
                                                                                                                            snode,
                                                                                                                            used_resources - self.substrate.node[snode][resource]))

                check_deviation("Comparison of LP resource allocation of resource {} on node {} and a posteriori computed allocations do not match.".format(resource, snode),
                                used_resources,
                                self.raw_node_load[snode][resource])


        #       check that bandwidth at nodes is sufficient

        if debug_output:
            print "\t checking bandwidth allocations on nodes"
        for snode in self.substrate.nodes:

            used_resources = 0

            for req in self.requests:

                mapping = self.mapping_of_request[req]
                if mapping.is_embedded:

                    if debug_output:
                        print "\t\t vedges being hosted on {} are {}".format(snode, mapping.get_hosted_vedges_using_snode(snode))

                    # reduce bandwidth for each link that is incident to the edge
                    for vedge in mapping.get_hosted_vedges_using_snode(snode):
                        used_resources += req.edge[vedge]["bandwidth"]

            if used_resources > self.substrate.node[snode]["bandwidth"]:
                raise Exception("The capacity of resource bandwidth on substrate node {} is exceeded by {} many units.".format(snode,
                                                                                                                               self.substrate.node[snode]["bandwidth"] - used_resources))
            self.print_solution()

            check_deviation("Comparison of LP resource allocation of resource bandwidth on node {} and a posteriori computed allocations do not match.".format(snode),
                                used_resources,
                                self.raw_node_load[snode]["bandwidth"])


        #   EDGES

        #       check that edges' capacities are not exceeded

        if debug_output:
            print "\t checking bandwidth allocations on edges"
        for sedge in self.substrate.edges:
            used_resources = 0

            for req in self.requests:

                mapping = self.mapping_of_request[req]

                if mapping.is_embedded:

                    if debug_output:
                        print "\t\t vedges being hosted on {} are {}".format(sedge, mapping.get_hosted_vedges_on_sedge(sedge))

                    for vedge in mapping.get_hosted_vedges_on_sedge(sedge):
                        used_resources += req.edge[vedge]["bandwidth"]

            if used_resources > self.substrate.edge[sedge]["bandwidth"]:
                raise Exception("The capacity of resource bandwidth on substrate edge {} is exceeded by {} many units.".format(sedge,
                                                                                                                               self.substrate.edge[sedge]["bandwidth"] - used_resources))

            check_deviation("Comparison of LP resource allocation of resource bandwidth on edge {} and a posteriori computed allocations do not match.".format(sedge),
                                used_resources,
                                self.raw_edge_load[sedge])
        #       check that requested latencies are not violated

        if debug_output:
            print "\t checking delay requirements"
        for req in self.requests:
            mapping = self.mapping_of_request[req]

            if mapping.is_embedded:
                for (id, vedge_path), delay in req.graph['path_requirements'].iteritems():
                    cumulative_delay = 0

                    for vedge in vedge_path:
                        delay_of_vedge = self.substrate.get_path_delay(mapping.vedge_to_spath[vedge])
                        if debug_output:
                            print "\t\t vedge {} has pure edge delay of {}".format(vedge, delay_of_vedge)
                        cumulative_delay += delay_of_vedge

                    for vedge in vedge_path:
                        vtail, vtail_p, vhead_p, vhead = vedge
                        for index, (stail, stail_p, shead_p, shead) in enumerate(mapping.vedge_to_spath[vedge]):
                            if index == 0:
                                delay_of_tail = self.substrate.node[stail]['delay']
                                if debug_output:
                                    print "\t\t .. adding delay of {} for using snode {} for embedding {}".format(delay_of_tail,
                                                                                                             stail,
                                                                                                             (vtail, vtail_p, vhead_p, vhead))
                                cumulative_delay += delay_of_tail

                            delay_of_head = self.substrate.node[shead]['delay']
                            if debug_output:
                                print "\t\t .. adding delay of {} for using snode {} for embedding {}".format(delay_of_head,
                                                                                                          shead,
                                                                                                          (vtail, vtail_p, vhead_p, vhead))
                            cumulative_delay += delay_of_head

                    if cumulative_delay > delay:
                        raise Exception("Delay bound of requirement {} is exceeded: {} vs. {}.".format(id, cumulative_delay, delay))

                    check_deviation("Comparison of delay computed in LP and a posteriori computed delay does not match for delay requirement {} of request {} [{}]".format(id, req.id, vedge_path),
                                        cumulative_delay,
                                        mapping.raw_path_delay[(id, vedge_path)])


        #some more checks here

        if debug_output:
            print "...everything looks fine."

    def print_solution(self):
        for req in self.requests:
            self.mapping_of_request[req].print_mapping()



if __name__ == '__main__':
  try:
    # req = _constructExampleRequest()
    # net = _constructExampleNetwork()

    # req = _example_request_for_fallback()
    # print req.dump()
    # req = _onlySAPsRequest()
    # print net.dump()
    # req = _testRequestForBacktrack()
    # net = _testNetworkForBacktrack()
    with open('../examples/escape-mn-req.nffg', "r") as f:
      req = NFFG.parse(f.read())

    request = convert_req_to_request(req)

    #print json.dumps(req, indent=2, sort_keys=False)
    with open('../examples/escape-mn-topo.nffg', "r") as g:
      net = NFFG.parse(g.read())
      #net.duplicate_static_links()

    substrate = convert_nffg_to_substrate(net)

    scen = Scenario(substrate, [request])
    mc = ModelCreator(scen)
    mc.init_model_creator()
    if isFeasibleStatus(mc.run_milp()):
        solution = mc.solution
        solution.print_solution()
        solution.validate_solution()



    import sys
    sys.exit(0)

  except uet.UnifyException as ue:
    print ue, ue.msg
    print traceback.format_exc()
