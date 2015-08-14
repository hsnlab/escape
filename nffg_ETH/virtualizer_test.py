import virtualizer
# import list
from virtualizer3 import *
import xml.etree.ElementTree as ET
import re
import fnmatch
import os
import copy
import unittest
import xml.dom.minidom
# from xml.dom.minidom import parseString

def getFilenames():
    filenames = []
    # filenames = [
    #     './test.in/1-node.xml',
    #     './test.in/3-node.xml',
    #     './test.in/1-node-with-delay-matrix.xml',
    #     './test.in/1-node-simple-request.xml',
    #     './test.in/1-node-simple-request-with-virtual-link-requirements.xml',
    #     './test.in/1-node-simple-request-with-NF-requirements.xml',
    #     './test.in/1-node-simple-request-with-delete.xml',
    #     './test.in/link-sharing-request-step1.xml',
    #     './test.in/link-sharing-request-step2.xml',
    #     './test.in/link-sharing-request-step3.xml'
    #     #'./test.in/list.xml',
    #     ]
    for root, dirnames, files in os.walk('test.in'):
      for filename in fnmatch.filter(files, '*.xml'):
        filenames.append(os.path.join(root, filename))
    return filenames


class InvalidXML(Exception):
    def __init__(self,message):
        print "Exception: " + str(Exception)

def writexmlfile(outfilename, text):
    if not os.path.exists(os.path.dirname(outfilename)):
        os.makedirs(os.path.dirname(outfilename))
    print 'Writing', outfilename
    with open(outfilename, 'w') as outfile:
        outfile.writelines(text)

def prettyformat(xml_fname):
        dom = xml.dom.minidom.parse(xml_fname)
        return dom.toprettyxml()

def parse(filename=None, text=None):
    if filename and text:
        raise InvalidXML("Dual XML input provided to be parsed")
    elif filename:
        try:
            tree = ET.parse(filename)
        except ET.ParseError as e:
            raise InvalidXML('ParseError: %s' % e.message)
    elif text:
        try:
            tree = ET.ElementTree(ET.fromstring(text))
        except ET.ParseError as e:
            raise InvalidXML('ParseError: %s' % e.message)
    else:
        raise InvalidXML("No XML input provided to be parsed")
    # return virtualizer.container_virtualizer.parse(root=tree.getroot())

    return Virtualizer.parse(root=tree.getroot())

def specification_test():
    """Example usage for the Virtualizer class parsing/dumping
    """
    inpts = dict()
    xmldumps = dict()

    filenames = getFilenames()

    for filename in filenames:
        print 'Parsing', filename
        inpts[filename] = parse(filename=filename)
        print 'Dumping', filename
        xmldumps[filename] = inpts[filename].xml()
        # head, tail = os.path.split(filename)
        writexmlfile(filename.replace("test.in", "test.out"), xmldumps[filename])

def escape_test():

    # builder.id = "UUID-ETH-001"
    # builder.name = "ETH OpenStack-OpenDaylight domain"
    v = Virtualizer(id="UUID-ETH-001", name="ETH OpenStack-OpenDaylight domain")

    # infra = builder.add_infra(
    #     name="single Bis-Bis node representing the whole domain")
    # builder.add_node_resource(infra, cpu="10 VCPU", mem="32 GB", storage="5 TB")
    v.nodes.add(
        Infra_node(
            id='infra',
            name='single Bis-Bis node representing the whole domain',
            type='BisBis',
            resources=NodeResources(
                cpu='10 VCPU',
                mem='32 GB',
                storage='5 TB'
            )
        )
    )

    # iport0 = builder.add_node_port(infra, name="OVS-north external port")
    iport0 = Port(id='0', name='OVS-north external port', port_type='port-sap')

    # iport1 = builder.add_node_port(infra, name="OVS-south external port")
    iport1 = Port(id='1',name='OVS-south external port',port_type='port-abstract')

    v.nodes['infra'].ports.add((iport0, iport1))

    # nf1 = builder.add_nf_instance(infra, id="NF1", name="example NF")
    v.nodes['infra'].NF_instances.add(Node(id="NF1", name="example NF"))

    # nf1port0 = builder.add_node_port(nf1, name="Example NF input port")
    nf1port0 = Port(id='in',name='Example NF input port',port_type='port-abstract')

    # nf1port1 = builder.add_node_port(nf1, name="Example NF output port")
    nf1port1 = Port(id='out',name='Example NF output port',port_type='port-abstract')

    v.nodes['infra'].NF_instances["NF1"].ports.add((nf1port0, nf1port1))

    # for port in v.nodes['infra'].NF_instances["NF1"].ports:
    #     print port
    #
    # print nf1port0.getRelPath(nf1port1)
    # print iport1.getRelPath(nf1port1)

    # sup_nf = builder.add_supported_nf(infra, id="nf_a",
    #                                 name="tcp header compressor")


    v.nodes['infra'].NF_instances.add(
        Node(id="nf_a", name="tcp header compressor")
    )
    # builder.add_node_port(sup_nf, name="in", param="...")
    v.nodes['infra'].NF_instances["NF1"].ports.add(
        Port(id="in", name="in", port_type="port-abstract"))

    # builder.add_node_port(sup_nf, name="out", param="...")
    v.nodes['infra'].NF_instances["NF1"].ports.add(
        Port(id="out", name="out", port_type="port-abstract"))

    flowe = Flowentry(port=iport0, out=nf1port0)
    # builder.add_flow_entry(infra, in_port=iport0, out_port=nf1port0)
    v.nodes['infra'].flowtable.add(flowe)

    print v
    return



    # builder.add_flow_entry(infra, in_port=nf1port1, out_port=iport1,
    #                  action="mod_dl_src=12:34:56:78:90:12")
    v.nodes['infra'].flowtable.add(Flowentry(port=nf1port1, action="mod_dl_src=12:34:56:78:90:12", out=iport1))

    print v

class comparison_test(unittest.TestCase):

    def test_self_equal(self):
        for filename in getFilenames():
            virt = parse(filename=filename)
            self.assertTrue(virt == virt)

    def test_changed_not_equal_1_node(self):
        virt = parse(filename='./test.in/1-node.xml')
        virtCopy = copy.deepcopy(virt)
        virtCopy.nodes.node['UUID11'].ports.port['0'].name.setValue('Changed Value')
        self.assertFalse(virt == virtCopy)

    def test_changed_not_equal_1_node_simple_request(self):
        virt = parse(filename='./test.in/1-node-simple-request.xml')
        virtCopy = copy.deepcopy(virt)
        virtCopy.nodes['UUID11'].NF_instances['NF1'].ports.port['2'].name.setValue('Changed Value')
        self.assertFalse(virt == virtCopy)

    def test_copy_equal(self):
        virt = parse(filename='./test.in/1-node.xml')
        virtCopy = copy.deepcopy(virt)
        self.assertTrue(virt == virtCopy)

class reduction_test(unittest.TestCase):

    def test_self_reduction(self):
        for filename in getFilenames():
            if filename != 'test.in/1-node-simple-request-with-delete.xml':
                virt = parse(filename=filename)
                empty = Virtualizer(id = virt.id.data)
                virt.reducer(virt)
                self.assertEqual(virt.xml(),empty.xml())


    def test_changed_change_set_1_node(self):
        virt = parse(filename='./test.in/1-node.xml')

        virtCopy = copy.deepcopy(virt)
        virtCopy.nodes.node['UUID11'].name.setValue('Changed Value')
        virt.reducer(virtCopy)

        expectedVirt = Virtualizer(id='UUID001')
        expectedVirt.nodes.add(
            Infra_node(
                id='UUID11',
                name='Changed Value'
            )
        )

        self.assertEqual(virtCopy.xml(),expectedVirt.xml())

class operation_test(unittest.TestCase):
    def test_operation_found(self):
        virt = parse(filename='./test.in/1-node-simple-request-with-delete.xml')
        self.assertEqual(virt.nodes.node['UUID11'].NF_instances.node['NF2'].operation,'delete')

    def test_operation_doesnt_lost(self):
        virt = parse(filename='./test.in/1-node-simple-request-with-delete.xml')
        virtCopy = copy.deepcopy(virt)
        virtCopy.nodes.node['UUID11'].NF_instances.node['NF2'].name.setValue('ChangedValue')
        virt.reducer(virtCopy)
        self.assertEqual(virtCopy.nodes.node['UUID11'].NF_instances.node['NF2'].operation,'delete')

    def test_oeration_delete_childre_reduce(self):
        virt = parse(filename='./test.in/1-node-simple-request-with-delete.xml')
        virtCopy = copy.deepcopy(virt)

        virt.reducer(virtCopy)

        expectedVirt = Virtualizer(id='UUID001')
        expectedVirt.nodes.add(
            Infra_node(id='UUID11')
        )
        expectedVirt.nodes.node['UUID11'].NF_instances.node.add(Node(id='NF2',
                                                                     name='cache',
                                                                     type='Http Cache 1.2'))
        expectedVirt.nodes.node['UUID11'].NF_instances.node['NF2'].ports.port.add(Port(id='4',
                                                                                       name='in',
                                                                                       port_type='port-abstract',
                                                                                       capability='...'))
        expectedVirt.nodes.node['UUID11'].NF_instances.node['NF2'].ports.port.add(Port(id='5',
                                                                                       name='out',
                                                                                       port_type='port-abstract',
                                                                                       capability='...'))
        expectedVirt.nodes.node['UUID11'].flowtable.add(Flowentry(id='2',
                                                                  port='../../NF_instances/node[id=NF1]/ports/port[id=3]',
                                                                  match='fr-a',
                                                                  action='output:../../NF_instances/node[id=NF2]/ports/port[id=4]'))
        
        self.assertEqual(virtCopy.xml(),expectedVirt.xml())

class merge_test(unittest.TestCase):
    def test_self_merge(self):
        virt = parse(filename='./test.in/1-node.xml')
        virtCopy = copy.deepcopy(virt)
        virt.merge(virtCopy)
        self.assertEqual(virt.xml(),virtCopy.xml())

    def test_merge_change_set_1_node(self):
        virt = parse(filename='./test.in/1-node.xml')
        virtCopy = copy.deepcopy(virt)
        virtCopy.nodes.add(
            Infra_node(
                id='UUID12',
                name='Changed Value'
            )
        )

        virt.merge(virtCopy)

        expectedVirt = copy.deepcopy(virt)
        expectedVirt.nodes.add(
            Infra_node(
                id='UUID12',
                name='Changed Value'
            )
        )
        self.assertEqual(virt.xml(),expectedVirt.xml())

    def test_merge_change_set_3_node(self):
        virt = parse(filename='./test.in/3-node.xml')
        virt.nodes.remove('UUID12')

        virtCopy = parse(filename='./test.in/3-node.xml')
        
        virt.merge(virtCopy)

        expectedVirt = parse(filename='./test.in/3-node.xml')

        self.assertEqual(virt.xml(),expectedVirt.xml())

class handBuiltTest():
    def __init__(self):
        print "=============================== 1 Node =========================================="
        print self.test_1_node().xml()
        # print "=============================== 1 Node Simple Request ==========================="
        # print self.test_1_node_simple_request().xml()
        # print "================================================================================="

    @classmethod
    def test_1_node(cls):
        #======================= 1-node XML built by hand =======================================#
        original_xml = parse(filename='./test.in/1-node.xml').xml()

        # print original_xml

        v = Virtualizer(id='UUID001',
                        name='single node simple infrastructure report')

        print v
        v.nodes.add(
            Infra_node(
                id='UUID11',
                name='Single Bis-Bis node',
                type='BisBis',
                resources=NodeResources(
                    cpu='20',
                    mem='64 GB',
                    storage='100 TB'
                )
            )
        )

        port1 = Port(
                        id='0',
                        name='SAP0 port',
                        port_type='port-sap'
                    )
        v.nodes.node['UUID11'].ports.add((
            port1
            ,
            Port(
                id='1',
                name='North port',
                port_type='port-abstract'
            ))
        )

        # v.nodes.node['UUID11'].ports.add(NodePortsPort(id='0',
        #                                                name='SAP0 port',
        #                                                port_type='port-sap'))
        # v.nodes.node['UUID11'].ports.add(NodePortsPort(id='1',
        #                                                  name='North port',
        #                                                  port_type='port-abstract'))
        v.nodes.node['UUID11'].ports.add(Port(id='2', name='East-port', port_type='port-abstract'))
        return v

    @classmethod
    def test_1_node_simple_request(cls):
        #======================= 1 Node Simple Request built by hand =============================#
        v = Virtualizer(id='UUID11',
                        name='Single node simple request')

        v.nodes.add(VirtualizerNodesNode(id='UUID11'))

        v.nodes['UUID11'].NF_instances.add(Infra_nodeNf_instancesNode(id='NF1', name='first NF',
                                                                  type='Parental control B.4'))
        v.nodes['UUID11'].NF_instances['NF1'].ports.add(NodePortsPort(id='2',
                                                                      name='in',
                                                                      port_type='port-abstract'))
        v.nodes.node['UUID11'].NF_instances.node['NF1'].ports.port['3']=NodePortsPort(id='3',
                                                                                      name='out',
                                                                                      port_type='port-abstract')

        v.nodes.node['UUID11'].NF_instances.node['NF2']=Infra_nodeNf_instancesNode(id='NF2',
                                                                                   name='cache',
                                                                                   type='Http Cache 1.2')
        v.nodes.node['UUID11'].NF_instances.node['NF2'].ports.port['2']=NodePortsPort(id='4',
                                                                                      name='in',
                                                                                      port_type='port-abstract')
        v.nodes.node['UUID11'].NF_instances.node['NF2'].ports.port['3']=NodePortsPort(id='5',
                                                                                      name='out',
                                                                                      port_type='port-abstract')

        v.nodes.node['UUID11'].NF_instances.node['NF3']=Infra_nodeNf_instancesNode(id='NF3',
                                                                                   name='firewall',
                                                                                   type='Stateful firewall C')
        v.nodes.node['UUID11'].NF_instances.node['NF3'].ports.port['2']=NodePortsPort(id='6',
                                                                                      name='in',
                                                                                      port_type='port-abstract')
        v.nodes.node['UUID11'].NF_instances.node['NF3'].ports.port['3']=NodePortsPort(id='7',
                                                                                      name='out',
                                                                                      port_type='port-abstract')
        v.nodes.node['UUID11'].flowtable.flowentry[('../../ports/port[id=0]','*','output:../../NF_instances/node[id=NF1]/ports/port[id=2]')]=FlowtableFlowtableFlowentry(port='../../ports/port[id=0]',
                                                                                                                                                                         match='*',
                                                                                                                                                                         action='output:../../NF_instances/node[id=NF2]/ports/port[id=4]')

        v.nodes.node['UUID11'].flowtable.flowentry[('../../NF_instances/node[id=NF1]/ports/port[id=3]','*','output:../../NF_instances/node[id=NF2]/ports/port[id=4]')]=FlowtableFlowtableFlowentry(port='../../NF_instances/node[id=NF1]/ports/port[id=3]',
                                                                                                                                                                                                     match='*',
                                                                                                                                                                                                     action='output:../../NF_instances/node[id=NF1]/ports/port[id=2]')

        v.nodes.node['UUID11'].flowtable.flowentry[('../../NF_instances/node[id=NF1]/ports/port[id=3]','*','output:../../NF_instances/node[id=NF1]/ports/port[id=2]')]=FlowtableFlowtableFlowentry(port='../../ports/port[id=0]',
                                                                                                                                                                                                     match='*',
                                                                                                                                                                                                     action='output:../../NF_instances/node[id=NF3]/ports/port[id=6]')
        v.nodes.node['UUID11'].flowtable.flowentry[('../../NF_instances/node[id=NF2]/ports/port[id=5]','*','output:../../ports/port[id=1]')]=FlowtableFlowtableFlowentry(port='../../NF_instances/node[id=NF2]/ports/port[id=5]',
                                                                                                                                                                         match='*',
                                                                                                                                                                         action='output:../../ports/port[id=1]')
        v.nodes.node['UUID11'].flowtable.flowentry[('../../NF_instances/node[id=NF3]/ports/port[id=7]','*','output:../../ports/port[id=1]')]=FlowtableFlowtableFlowentry(port='../../NF_instances/node[id=NF3]/ports/port[id=7]',
                                                                                                                                                                                                     match='*',
                                                                                                                                                                                                     action='output:../../ports/port[id=1]')
        return v

def un_test():
    # read set config from escape
    v = parse(filename='./test.in/UN_examples/set-confg-from-escape.xml')

    # iterate in flowentries
    for fe in v.nodes["UUID11"].flowtable:
        print "----------------------------"
        # dump flowentry
        # print fe

        # get the port and the out target and print it
        port = fe.port.getTarget()
        out = fe.out.getTarget()
        # print "port: " + str(port)
        # print "out: " + str(out)

        # replace in and out port, leafref is updated automatically
        fe.port.setValue(out)
        fe.out.setValue(port)

        # dump updated flowentry
        print fe

        # check for string or embedded ElementTree type
        if fe.match is not None:
            print fe
            if type(fe.match.data) is str:
                print "match: " + fe.match
            elif type(fe.match.data) is ET.Element:
                print "match: "
                for node in fe.match.data:
                    print node.tag + ": " + node.text





if __name__ == "__main__":
    #specification_test()
    # escape_test()
    # un_test()
    # handBuiltTest()
    unittest.main()
    #operation_test.test_oeration_delete_childre_reduce()
    #comparison_test.test_copy_equal()
    # print parse("./test.in/UN_examples/ko.xml")

