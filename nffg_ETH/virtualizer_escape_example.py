__author__ = 'Robert Szabo'

from virtualizer3 import *


def escape_test ():
  # builder.id = "UUID-ETH-001"
  # builder.name = "ETH OpenStack-OpenDaylight domain"
  v = Virtualizer(id="UUID-ETH-001", name="ETH OpenStack-OpenDaylight domain")

  # infra = builder.add_infra(
  #     name="single Bis-Bis node representing the whole domain")
  # builder.add_node_resource(infra, cpu="10 VCPU", mem="32 GB", storage="5 TB")
  v.nodes.add(
    Infra_node(id='infra', name='single Bis-Bis node representing the whole '
                                'domain', type='BisBis',
               resources=NodeResources(cpu='10 VCPU', mem='32 GB',
                                       storage='5 TB')))

  # iport0 = builder.add_node_port(infra, name="OVS-north external port")
  iport0 = Port(id='0', name='OVS-north external port', port_type='port-sap')

  # iport1 = builder.add_node_port(infra, name="OVS-south external port")
  iport1 = Port(id='1', name='OVS-south external port',
                port_type='port-abstract')

  v.nodes['infra'].ports.add((iport0, iport1))

  # nf1 = builder.add_nf_instance(infra, id="NF1", name="example NF")
  v.nodes['infra'].NF_instances.add(Node(id="NF1", name="example NF"))

  # nf1port0 = builder.add_node_port(nf1, name="Example NF input port")
  nf1port0 = Port(id='in', name='Example NF input port',
                  port_type='port-abstract')

  # nf1port1 = builder.add_node_port(nf1, name="Example NF output port")
  nf1port1 = Port(id='out', name='Example NF output port',
                  port_type='port-abstract')

  v.nodes['infra'].NF_instances["NF1"].ports.add((nf1port0, nf1port1))

  # sup_nf = builder.add_supported_nf(infra, id="nf_a",
  #                                 name="tcp header compressor")
  v.nodes['infra'].NF_instances.add(
    Node(id="nf_a", name="tcp header compressor"))
  # builder.add_node_port(sup_nf, name="in", param="...")
  v.nodes['infra'].NF_instances["NF1"].ports.add(
    Port(id="in", name="in", port_type="port-abstract"))

  # builder.add_node_port(sup_nf, name="out", param="...")
  v.nodes['infra'].NF_instances["NF1"].ports.add(
    Port(id="out", name="out", port_type="port-abstract"))

  # builder.add_flow_entry(infra, in_port=iport0, out_port=nf1port0)
  v.nodes['infra'].flowtable.add(Flowentry(id="1", port=iport0, out=nf1port0))

  # builder.add_flow_entry(infra, in_port=nf1port1, out_port=iport1,
  #                  action="mod_dl_src=12:34:56:78:90:12")
  v.nodes['infra'].flowtable.add(
    Flowentry(id="2", port=nf1port1, action="mod_dl_src=12:34:56:78:90:12",
              out=iport1))
  print v


if __name__ == "__main__":
  escape_test()
