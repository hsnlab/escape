
__author__="Jokin Garay <jokin.garay@ehu.eus>"
__date__ ="$06-Feb-2015 12:45:02$"

import mysql.connector
import networkx as nx
from networkx.readwrite import json_graph
import json
import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import pylab as pyl
import pprint

# Connection params for MySQL
MYSQL_CONFIG = {
    'user' : 'elwud',
    'password' : 'elwuddb',
    'host' : 'localhost',
    'database' : 'ehuoef',
    'raise_on_warnings': True,
}

# MySQL tables (fed by User layer)
SGIB_TABLE = 'sgib'
SG_TABLE = 'sg_instances'
SGNF_TABLE = 'sg_instances_nfs'
SGLINKS_TABLE = 'sgib_links'
NFIB_TABLE = 'nfib'
NFPORTS_TABLE = 'nf_ports'
NFIMP_TABLE = 'nfib_implementations'

# SG Version
SG_VERSION = '1.0'

# Params for SG drawing
NF_NODE_SIZE=1600
SAP_NODE_SIZE=600
NF_NODE_COLOR='blue'
SAP_NODE_COLOR='red'
NODE_ALPHA=0.3
NODE_TEXT_SIZE=12
EDGE_COLOR='blue'
EDGE_ALPHA=0.3
EDGE_THICKNESS=1
EDGE_TEXT_POS=0.5
EDGE_TEXT_SIZE=8
TEXT_FONT='sans-serif'


class ServiceGraph(nx.DiGraph):

    def __init__(self, sg_id=None):
        # Allow calling without Sg Id for inherited methods (i.e. subgraph)
        super(ServiceGraph, self).__init__()
                
        if sg_id is not None:
            cnx = mysql.connector.connect(**MYSQL_CONFIG)
            cursor = cnx.cursor(dictionary=True)
            
            # Get SG Header data
            command = ' '.join(['SELECT sgId, tenantId, sgTemplateId,',
                                'deployStatus, transferSl, deleted FROM',
                                SG_TABLE, 'WHERE sgId = "', sg_id, '";'])
            cursor.execute(command)
            for row in cursor:
                self.graph['id'] = row['sgId']
                self.graph['template'] = row['sgTemplateId']
                self.graph['tenant'] =  row['tenantId']
                self.graph['version'] =  SG_VERSION
                self.graph['status'] = dict((
                                        ['deploy_status',row['deployStatus']],
                                        ['transfer_sl',row['transferSl']],
                                        ['deleted',row['deleted']]))

            # Get SG template data
            command = ' '.join(['SELECT sgTemplateDesc, serviceName FROM',
                                SGIB_TABLE, 'WHERE sgTemplateId = "', str(self.graph['template']), '";'])
            cursor.execute(command)
            for row in cursor:
                self.graph['name'] = row['sgTemplateDesc']
                self.graph['service'] = row['serviceName']                
            
            # Get SG NFs, careful with MySQL connector when multiple columns
            # have the same name (explicitly select the one we want)
            command = ' '.join(['SELECT sg.sgPos, sg.nfTemplateId,',
                                'sg.nfKQIValue, sg.nfDeployId,',
                                'nfib.nfTemplateDesc, nfib.nfKQIDesc FROM'
                                ,SGNF_TABLE,'sg INNER JOIN', NFIB_TABLE,'nfib',
                                'ON sg.nfTemplateId=nfib.nfTemplateId',
                                'WHERE sg.sgId = "',str(self.graph['id']),
                                '";'])
            cursor.execute(command)
            
            for row in cursor:
                if row['nfTemplateId'] == 99:
                    # TODO: 1-med - SAP - Missing flowspaces
                    self.add_node(row['sgPos'], type='SAP',
                                  functional_type=row['nfTemplateId'])
                else:
                    self.add_node(row['sgPos'], type='NF', 
                                  functional_type=row['nfTemplateId'], 
                                  name=row['nfTemplateDesc'])
                    self.node[row['sgPos']]['monitoring'] = dict((
                                  ['KQI_value',row['nfKQIValue']],
                                  ['KQI_desc',row['nfKQIDesc']]))

            # Get NF Ports
            nodes = self.nodes(data=True)
            
            for n in nodes:
                command = ' '.join(['SELECT nfPortId, nfPortDesc',
                                    'FROM', NFPORTS_TABLE,
                                    'WHERE nfTemplateId = "',
                                    str(n[1]['functional_type']), '";'])
                cursor.execute(command)
                ports = []
                for row in cursor:
                    ports.append(dict((['id',row['nfPortId']],
                                       ['property',row['nfPortDesc']])))
                self.node[n[0]]['ports'] = ports
                    
            # Get SG Links
            # Here are link reqs assigned but should be linked to imp selection
            command = ' '.join(['SELECT srcNfIndex, srcNfPort,',
                                'dstNfIndex, dstNfPort, net_bw, net_delay',
                                'FROM', SGLINKS_TABLE,'WHERE sgTemplateId = "',
                                str(self.graph['template']), '";'])
            cursor.execute(command)

            for row in cursor:
                link_requirements={"net_bw":row['net_bw'],
                           "net_delay":row['net_delay']}
                link_resources={"requirements":link_requirements}           
                self.add_edge(row['srcNfIndex'], row['dstNfIndex'], 
                              srcport=row['srcNfPort'],
                              dstport=row['dstNfPort'],
                              resources=link_resources)

            cursor.close()
            cnx.close()

    def save(self):
            cnx = mysql.connector.connect(**MYSQL_CONFIG)
            cursor = cnx.cursor(dictionary=True)
            
            # Save SG Header data
            command = ' '.join(['INSERT INTO', SG_TABLE, '(sgId, tenantId,',
                                'sgTemplateId, deployStatus, transferSl,',
                                'deleted) VALUES (', str(self.graph['id']),",",
                                str(self.graph['tenant']),",",
                                str(self.graph['template']),",",
                                str(self.graph['status']['deploy_status']),",",
                                str(self.graph['status']['transfer_sl']),",",
                                str(self.graph['status']['deleted']), ');'])
            print("Command: %s" % command)
            cursor.execute(command)
            cnx.commit()
            
            # Save SG NFs
            for nf in self.node.items():
                if nf[1]['type'] == 'NF':   
                    command = ' '.join(['INSERT INTO', SGNF_TABLE, '(sgId, sgPos,',
                                'nfTemplateId, nfKQIValue, nfDeployId) VALUES (', 
                                str(self.graph['id']),",",
                                str(nf[0]),",",
                                str(nf[1]['functional_type']),",",
                                str(nf[1]['monitoring']['KQI_value']),",",
                                str(nf[1]['specification']['deployment_type']),
                                ');'])
                elif nf[1]['type'] == 'SAP':
                    command = ' '.join(['INSERT INTO', SGNF_TABLE, '(sgId, sgPos,',
                                'nfTemplateId) VALUES (',
                                str(self.graph['id']),",",
                                str(nf[0]),",",
                                str(nf[1]['functional_type']), ');'])
                else:
                    print("Unsupported type")
                    return
                print("Command: %s" % command)
                cursor.execute(command)
                
            cnx.commit()
            cursor.close()
            cnx.close()        

    def delete(self):
            cnx = mysql.connector.connect(**MYSQL_CONFIG)
            cursor = cnx.cursor(dictionary=True)
            
            command = ' '.join(['DELETE FROM', SG_TABLE, 'WHERE sgId="',
                                str(self.graph['id']), '";'])
            print("Command: %s" % command)
            cursor.execute(command)
            cnx.commit()
            cursor.close()
            cnx.close()        

    def __iter__(self):
        return(super(ServiceGraph, self).__iter__())

    def decompose(self):
        # Check if the sg is fully defined
        # First get all NFs
        nfs=self.subgraph( [n for n,attrdict in self.node.items() 
                    if attrdict['type']=='NF' ] )
        
        # Get those without specification
        nfs_nospec=nfs.subgraph([n for n,attrdict in nfs.node.items() 
                    if 'specification' not in attrdict])
        
        # Those with specification without deployment type
        nfs_spec=nfs.subgraph([n for n,attrdict in nfs.node.items() 
                    if 'specification' in attrdict])
        nfs_nodeploy=nfs_spec.subgraph([n for n,
                    attrdict in nfs_spec.node.items() 
                    if 'deployment_type' not in attrdict['specification']])

        # Those with specification and deployment type 'None'
        nfs_deploy=nfs_spec.subgraph([n for n,
                    attrdict in nfs_spec.node.items() 
                    if 'deployment_type' in attrdict['specification']])
        nfs_deploynone=nfs_deploy.subgraph([n for n,
                    attrdict in nfs_deploy.node.items() 
                    if attrdict['specification']['deployment_type']==None])

        abstract_nfs=nx.compose_all((nfs_nospec,nfs_nodeploy,nfs_deploynone))

        for n in abstract_nfs.nodes_iter(data=True):
            try:
                self.set_implementation_nf(n[0])
            #except LookupError as e:
            #    print(e.args)
            except LookupError:
                print("LookupError")

    def set_implementation_nf(self, sg_pos):
        cnx = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = cnx.cursor(dictionary=True, buffered=True)
        
        command = ' '.join(['SELECT nfImplementationId, vnfType,'
                            'nfKQIValue, json,',
                            'com_cpu, com_mem, com_cap, net_bw, sto_hdd',
                            'FROM', NFIMP_TABLE, 'WHERE nfTemplateId = "', 
                            str(self.node[sg_pos]['functional_type'])])
        
        # Selection based on KQI Value if specified
        if self.node[sg_pos]['monitoring']['KQI_value'] is not None:
            command = ' '.join([command, '" AND nfKQIValue >= "', 
                            str(self.node[sg_pos]['monitoring']['KQI_value'])])

        # If not specified pick the lowest KQI
        command = ' '.join([command, '" ORDER BY nfKQIValue ASC LIMIT 1;'])                    

        cursor.execute(command)

        # Raise error if no implementation satisfies the KQI
        if cursor.rowcount is not 1:
            cursor.close()
            cnx.close()           
            print ('No Implementation NF available for %s / KQI %s' 
                              % (self.node[sg_pos]['functional_type'], 
                              self.node[sg_pos]['monitoring']['KQI_value']) )
            raise LookupError('No Implementation NF available for %s / KQI %s' 
                              % (self.node[sg_pos]['functional_type'], 
                              self.node[sg_pos]['monitoring']['KQI_value']) )

        # Get the data for the selected implementation and update the DB
        else:
            for row in cursor:
                nf_requirements=dict((['com_cpu',row['com_cpu']],
                                      ['com_mem',row['com_mem']],
                                      ['com_cap',row['com_cap']],                                      
                                      ['net_bw',row['net_bw']],                                        
                                      ['sto_hdd',row['sto_hdd']]))
                self.node[sg_pos]['specification'] = dict((
                                 ['deployment_type',row['nfImplementationId']],
                                 ['vnf_type',row['vnfType']],
                                 ['max_KQI_value',row['nfKQIValue']],                                        
                                 ['image_uri',row['json']]))
                #TODO: 1-med - NFFG: same place for resources in EP/NF to ease split
                #nf_resources=dict([("requirements", nf_requirements)])
                self.node[sg_pos]['resources']=dict([("requirements", 
                                                      nf_requirements)])

                                                 

            command = ' '.join(['UPDATE', SGNF_TABLE, 'SET nfDeployId = "',
                    str(self.node[sg_pos]['specification']['deployment_type']),
                    '" WHERE sgId = "', str(self.graph['id']),
                    '" AND sgPos ="', str(sg_pos), '";'])

            cursor.execute(command)
            cnx.commit()
            cursor.close()
            cnx.close()           

#    def map(self, rg):
        # print("Here we map SG %s to RG %s" % (self.graph['id'],rg.graph['id']))
        # Check if SG is mapped to RG based on id
        # If it is, just check elements not mapped
        # If it is not, map to new RG (exploit rg to rg mapping)
        # The map using mapping function
    
    def printout(self, message=None, detail=False):
        if message is not None:
            print(message)
        print("SgId: %6s\tTenantId: %s\tDescription: %s\tTemplate Id: %s\nDeploy Status: %s" % 
                                                        (self.graph['id'],
                                                         self.graph['tenant'],
                                                         self.graph['name'],                                                         
                                                         self.graph['template'],
                                                         self.graph['status']))
        print("\tNumber of nodes:\t%s" % self.number_of_nodes())
        print("\tNumber of edges:\t%s" % self.number_of_edges())        
        if detail:
            print("\tDetail:")
            pprint.pprint(self.nodes(data=True))
            pprint.pprint(self.edges())

    def draw(self, outfile, node_labels=True, link_labels=True):
        # Clean buffer                   
        plt.clf()

        # No axis, spectral layout
        pyl.axis('off')
        graph_pos=nx.spectral_layout(self)
        #graph_pos=nx.spring_layout(self)
        #graph_pos=nx.circular_layout(self)

        # Create & draw different subgraphs for NFs / SAPs
        sg_nf=self.subgraph( [n for n,attrdict in self.node.items() 
                              if attrdict ['type'] == 'NF' ])
        sg_sap=self.subgraph( [n for n,attrdict in self.node.items() 
                               if (attrdict ['type'] == 'SAP' or
                                   attrdict ['type'] == 'xSAP') ])
        
        nx.draw_networkx_nodes(sg_nf,graph_pos,node_size=NF_NODE_SIZE, 
                               alpha=NODE_ALPHA, node_color=NF_NODE_COLOR)
        nx.draw_networkx_nodes(sg_sap,graph_pos,node_size=SAP_NODE_SIZE, 
                               alpha=NODE_ALPHA, node_color=SAP_NODE_COLOR)                               

        nf_labels = nx.get_node_attributes(sg_nf,'name')
        sap_labels = nx.get_node_attributes(sg_sap,'name')
        
        if node_labels:
            nx.draw_networkx_labels(self, graph_pos,nf_labels,
                                    font_size=NODE_TEXT_SIZE,font_family=TEXT_FONT)
            nx.draw_networkx_labels(self, graph_pos,sap_labels,
                                    font_size=NODE_TEXT_SIZE,font_family=TEXT_FONT)

        # Draw edges
        nx.draw_networkx_edges(self,graph_pos,width=EDGE_THICKNESS,
                               alpha=EDGE_ALPHA,EDGE_COLOR=EDGE_COLOR)
        if link_labels:                               
            nx.draw_networkx_edge_labels(self, graph_pos, label_pos=EDGE_TEXT_POS, 
                                     font_size=EDGE_TEXT_SIZE)

        # Store graph
        plt.savefig(outfile)
        
    def dumps(self, encode=True):
        data = json_graph.node_link_data(self)
        if encode:
            return json.dumps(data, sort_keys=True).encode()
        else:
            return data        
  
    def dump(self, outfile):
        data = json_graph.node_link_data(self)
        with open(outfile, 'w') as sg_file:
            json.dump(data, sg_file, sort_keys=True, indent=2)

    def loads(injson):
        sg = json_graph.node_link_graph(injson)
        sg.__class__= ServiceGraph
        return sg
                        
    def get_type(self, sg_pos):
        return self.node[sg_pos]['type']

    def get_resources(self, sg_pos):
        #TODO: 1-med - NFFG: same place for resources in EP/NF to ease split
        return self.node[sg_pos]['resources']['assignment']
#        if self.node[sg_pos]['type'] == 'SAP':
#            return self.node[sg_pos]['resources']['assignment']
#        elif self.node[sg_pos]['type'] == 'NF':
#            return self.node[sg_pos]['specification']['resources']['assignment']
#        else:
#            return None