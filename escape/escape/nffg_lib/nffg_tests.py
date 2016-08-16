#!/usr/bin/env python

import sys

from nffg import *

DOMAIN_INTERNAL = "INTERNAL"
DOMAIN_SDN = "SDN"


def test_parse_load ():
  # NF
  nf = NodeNF()
  nf.id = "nf1"
  nf.name = "NetworkFunction1"
  nf.functional_type = "functype1"
  nf.deployment_type = "virtual"
  nf.resources.cpu = "10"
  nf.resources.mem = "1"
  nf.resources.storage = "10"
  nf.resources.bandwidth = "2"
  nf.resources.delay = "2"
  # nf.add_port("port_nf1", "port1", "virtual", "vlan:1025")
  p1 = nf.add_port(id="port_nf1",
                   properties={"port1": 42, "virtual": 24, "vlan": 1025})
  # SAP
  sap = NodeSAP()
  sap.id = "sap1"
  sap.name = "sap1"
  p2 = sap.add_port(id="port_sap")
  # Infra
  infra = NodeInfra()
  infra.id = "infra1"
  infra.operation = Element.ADD
  infra.name = "BisBis1"
  infra.domain = "virtual"
  infra.resources.cpu = "20"
  infra.resources.mem = "2"
  infra.resources.storage = "20"
  infra.resources.bandwidth = "4"
  infra.add_metadata("meta1", "lorem")
  infra.add_metadata("meta2", "ipsum")
  # infra.add_supported_type("functype1")
  infra.add_supported_type(("functype1", "functype2", "functype3"))
  # infra.resources.delay = "4"
  p3 = port_infra = infra.add_port(id="port_infra")
  port_infra.add_flowrule("match123", "action456")
  # Edge link
  edge_link = EdgeLink(p2, p3, id="link3")
  edge_link.bandwidth = "100"
  edge_link.delay = "5"
  edge_link.backward = True
  edge_link.operation = Element.DEL
  # Edge SG next hop
  edge_sg = EdgeSGLink(p1, p2, id="link1")
  edge_sg.flowclass = "flowclass1"
  # Edge requirement
  edge_req = EdgeReq(p2, p3)
  edge_req.id = "link2"
  edge_req.bandwidth = "100"
  edge_req.delay = "5"
  edge_req.sg_path.append(edge_sg.id)
  edge_req.sg_path.append(edge_link.id)
  # Generate
  nffg = NFFGModel()
  nffg.name = "NFFG1"
  nffg.metadata['lorem'] = 'ipsum'
  nffg.node_infras.append(infra)
  nffg.node_nfs.append(nf)
  nffg.node_saps.append(sap)
  nffg.edge_links.append(edge_link)
  nffg.edge_sg_nexthops.append(edge_sg)
  nffg.edge_reqs.append(edge_req)
  data = nffg.dump()
  print "\nGenerated NF-FG:"
  print data
  nffg2 = NFFGModel.parse(data)
  print "\nParsed NF-FG:"
  print nffg2.dump()
  return nffg


def test_NFFG ():
  # Add nodes
  nffg = NFFG(id="BME-001")
  infra = nffg.add_infra(id="node0", name="INFRA0")
  sap0 = nffg.add_sap(id="SAP1")
  sap1 = nffg.add_sap(id="SAP2")
  nf1 = nffg.add_nf(id="NF1", name="NetFunc1")
  nf2 = nffg.add_nf(id="NF2", name="NetFunc2")
  nf3 = nffg.add_nf(id="NF3", name="NetFunc3")
  # Add ports and edges
  nffg.add_link(sap0.add_port(1), infra.add_port(0), id="infra_in")
  nffg.add_link(sap1.add_port(1), infra.add_port(1), id="infra_out")
  nffg.add_link(infra.add_port(2), nf1.add_port(1), id="nf1_in", dynamic=True)
  nffg.add_link(nf1.add_port(2), infra.add_port(3), id="nf1_out", dynamic=True)
  nffg.add_link(infra.add_port(4), nf2.add_port(1), id="nf2_in", dynamic=True)
  nffg.add_link(nf2.add_port(2), infra.add_port(5), id="nf2_out", dynamic=True)
  nffg.add_link(infra.add_port(6), nf3.add_port(1), id="nf3_in", dynamic=True)
  nffg.add_link(nf3.add_port(2), infra.add_port(7), id="nf3_out", dynamic=True)
  # Add SG hops
  nffg.add_sglink(sap0.ports[1], nf1.ports[1], id="hop1")
  nffg.add_sglink(nf1.ports[2], nf2.ports[1], id="hop2")
  nffg.add_sglink(nf2.ports[2], nf3.ports[1], id="hop3")
  nffg.add_sglink(nf3.ports[1], sap1.ports[1], id="hop4")
  nffg.add_sglink(sap1.ports[1], sap0.ports[1], id="hop_back")
  # Add req
  nffg.add_req(sap0.ports[1], sap1.ports[1], id="req", delay=10, bandwidth=100)
  # Dump NetworkX structure
  from pprint import pprint
  print "\nNetworkX:"
  pprint(nffg.network.__dict__)
  # Dump NFFGModel structure
  print "\nNFFGModel:"
  nffg_dump = nffg.dump()
  print nffg_dump
  # Dump tests
  print "\nNFs:"
  for nf in nffg.nfs:
    print nf
  print "\nSG next hops:"
  for hop in nffg.sg_hops:
    print hop

  # Parse NFFG
  print "\nParsed NF-FG:"
  print NFFG.parse(nffg_dump).dump()

  # Copy test

  print "Copied NF-FG:"
  # pprint(nffg.copy().network.__dict__)
  pprint(copy.deepcopy(nffg).network.__dict__)


def generate_mn_topo ():
  # Create NFFG
  nffg = NFFG(id="INTERNAL", name="Internal-Mininet-Topology")
  # Add environments
  ee1 = nffg.add_infra(id="EE1", name="ee-infra-1", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                       delay=0.9, bandwidth=5000)
  ee2 = nffg.add_infra(id="EE2", name="ee-infra-2", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                       delay=0.9, bandwidth=5000)
  # Add supported types
  ee1.add_supported_type(
    ('headerCompressor', 'headerDecompressor', 'simpleForwarder'))
  ee2.add_supported_type(
    ('headerCompressor', 'headerDecompressor', 'simpleForwarder'))
  # Add OVS switches
  sw3 = nffg.add_infra(id="SW3", name="switch-3", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.2,
                       bandwidth=10000)
  sw4 = nffg.add_infra(id="SW4", name="switch-4", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.2,
                       bandwidth=10000)
  # Add SAPs
  sap1 = nffg.add_sap(id="SAP1", name="SAP1")
  sap2 = nffg.add_sap(id="SAP2", name="SAP2")
  sap14 = nffg.add_sap(id="SAP14", name="SAP14")
  sap14.domain = "eth0"

  # Add links
  link_res = {'delay': 1.5, 'bandwidth': 10}
  nffg.add_link(ee1.add_port(1), sw3.add_port(1), id="mn-link1", **link_res)
  nffg.add_link(ee2.add_port(1), sw4.add_port(1), id="mn-link2", **link_res)
  nffg.add_link(sw3.add_port(2), sw4.add_port(2), id="mn-link3", **link_res)
  nffg.add_link(sw3.add_port(3), sap1.add_port(1), id="mn-link4", **link_res)
  nffg.add_link(sw4.add_port(3), sap2.add_port(1), id="mn-link5", **link_res)
  nffg.add_link(sw4.add_port(4), sap14.add_port(1), id="mn-link6", **link_res)
  # nffg.duplicate_static_links()
  return nffg


def generate_mn_topo2 ():
  # Create NFFG
  nffg = NFFG(id="INTERNAL2", name="Internal-Mininet-Topology2")
  # Add environments
  ee1 = nffg.add_infra(id="EE11", name="ee-infra-11", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                       delay=0.9, bandwidth=5000)
  ee2 = nffg.add_infra(id="EE12", name="ee-infra-12", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                       delay=0.9, bandwidth=5000)
  # Add supported types
  ee1.add_supported_type(
    ('headerCompressor', 'headerDecompressor', 'simpleForwarder'))
  ee2.add_supported_type(
    ('headerCompressor', 'headerDecompressor', 'simpleForwarder'))
  # Add OVS switches
  sw3 = nffg.add_infra(id="SW13", name="switch-13", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.2,
                       bandwidth=10000)
  sw4 = nffg.add_infra(id="SW14", name="switch-14", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.2,
                       bandwidth=10000)
  # Add SAPs
  sap1 = nffg.add_sap(id="SAP3", name="SAP3")
  sap2 = nffg.add_sap(id="SAP4", name="SAP4")
  sap14 = nffg.add_sap(id="SAP14", name="SAP14")
  sap14.domain = "eth0"

  # Add links
  link_res = {'delay': 1.5, 'bandwidth': 10}
  nffg.add_link(ee1.add_port(1), sw3.add_port(1), id="mn-link11", **link_res)
  nffg.add_link(ee2.add_port(1), sw4.add_port(1), id="mn-link12", **link_res)
  nffg.add_link(sw3.add_port(2), sw4.add_port(2), id="mn-link13", **link_res)
  nffg.add_link(sw3.add_port(3), sap1.add_port(1), id="mn-link14", **link_res)
  nffg.add_link(sw4.add_port(3), sap2.add_port(1), id="mn-link15", **link_res)
  nffg.add_link(sw4.add_port(4), sap14.add_port(1), id="mn-link16", **link_res)
  # nffg.duplicate_static_links()
  return nffg


def generate_dynamic_fallback_nffg ():
  nffg = NFFG(id="DYNAMIC-FALLBACK-TOPO", name="fallback-dynamic")
  nc1 = nffg.add_infra(id="nc1", name="NC1", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                       delay=0.9, bandwidth=5000)
  nc2 = nffg.add_infra(id="nc2", name="NC2", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                       delay=0.9, bandwidth=5000)
  nc1.add_supported_type(['A', 'B'])
  nc2.add_supported_type(['A', 'C'])
  s3 = nffg.add_infra(id="s3", name="S3", domain=DOMAIN_INTERNAL,
                      infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.2,
                      bandwidth=10000)
  s4 = nffg.add_infra(id="s4", name="S4", domain=DOMAIN_INTERNAL,
                      infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.2,
                      bandwidth=10000)
  sap1 = nffg.add_sap(id="sap1", name="SAP1")
  sap2 = nffg.add_sap(id="sap2", name="SAP2")
  linkres = {'delay': 1.5, 'bandwidth': 2000}
  nffg.add_link(nc1.add_port(1), s3.add_port(1), id="l1", **linkres)
  nffg.add_link(nc2.add_port(1), s4.add_port(1), id="l2", **linkres)
  nffg.add_link(s3.add_port(2), s4.add_port(2), id="l3", **linkres)
  nffg.add_link(s3.add_port(3), sap1.add_port(1), id="l4", **linkres)
  nffg.add_link(s4.add_port(3), sap2.add_port(1), id="l5", **linkres)
  nffg.duplicate_static_links()
  return nffg


def generate_static_fallback_topo ():
  nffg = NFFG(id="STATIC-FALLBACK-TOPO", name="fallback-static")
  s1 = nffg.add_infra(id="s1", name="S1", domain=DOMAIN_INTERNAL,
                      infra_type=NFFG.TYPE_INFRA_SDN_SW)
  s2 = nffg.add_infra(id="s2", name="S2", domain=DOMAIN_INTERNAL,
                      infra_type=NFFG.TYPE_INFRA_SDN_SW)
  s3 = nffg.add_infra(id="s3", name="S3", domain=DOMAIN_INTERNAL,
                      infra_type=NFFG.TYPE_INFRA_SDN_SW)
  s4 = nffg.add_infra(id="s4", name="S4", domain=DOMAIN_INTERNAL,
                      infra_type=NFFG.TYPE_INFRA_SDN_SW)
  sap1 = nffg.add_sap(id="sap1", name="SAP1")
  sap2 = nffg.add_sap(id="sap2", name="SAP2")
  nffg.add_link(s1.add_port(1), s3.add_port(1), id="l1")
  nffg.add_link(s2.add_port(1), s4.add_port(1), id="l2")
  nffg.add_link(s3.add_port(2), s4.add_port(2), id="l3")
  nffg.add_link(s3.add_port(3), sap1.add_port(1), id="l4")
  nffg.add_link(s4.add_port(3), sap2.add_port(1), id="l5")
  nffg.duplicate_static_links()
  return nffg


def generate_one_bisbis ():
  nffg = NFFG(id="1BiSBiS", name="One-BiSBiS-View")
  bb = nffg.add_infra(id="1bisbis", name="One-BiSBiS",
                      domain=NFFG.DEFAULT_DOMAIN,
                      infra_type=NFFG.TYPE_INFRA_BISBIS)
  # FIXME - very basic heuristic for virtual resource definition
  # bb.resources.cpu = min((infra.resources.cpu for infra in
  #                         self.global_view.get_resource_info().infras))
  # bb.resources.mem = min((infra.resources.cpu for infra in
  #                         self.global_view.get_resource_info().infras))
  # bb.resources.storage = min((infra.resources.cpu for infra in
  #                             self.global_view.get_resource_info().infras))
  # bb.resources.delay = min((infra.resources.cpu for infra in
  #                           self.global_view.get_resource_info().infras))
  # bb.resources.bandwidth = min((infra.resources.cpu for infra in
  #                               self.global_view.get_resource_info().infras))
  bb.resources.cpu = sys.maxint
  bb.resources.mem = sys.maxint
  bb.resources.storage = sys.maxint
  bb.resources.delay = 0
  bb.resources.bandwidth = sys.maxint
  sap1 = nffg.add_sap(id="sap1", name="SAP1")
  sap2 = nffg.add_sap(id="sap2", name="SAP2")
  nffg.add_link(sap1.add_port(1), bb.add_port(1), id='link1')
  nffg.add_link(sap2.add_port(1), bb.add_port(2), id='link2')
  nffg.duplicate_static_links()
  return nffg


def generate_mn_test_req ():
  test = NFFG(id="SG-decomp", name="SG-name")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  comp = test.add_nf(id="comp", name="COMPRESSOR", func_type="headerCompressor",
                     cpu=1, mem=1, storage=0)
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1, storage=0)
  fwd = test.add_nf(id="fwd", name="FORWARDER", func_type="simpleForwarder",
                    cpu=1, mem=1, storage=0)
  test.add_sglink(sap1.add_port(1), comp.add_port(1), id=1)
  test.add_sglink(comp.ports[1], decomp.add_port(1), id=2)
  test.add_sglink(decomp.ports[1], sap2.add_port(1), id=3)
  test.add_sglink(sap2.ports[1], fwd.add_port(1), id=4)
  test.add_sglink(fwd.ports[1], sap1.ports[1], id=5)

  test.add_req(sap1.ports[1], sap2.ports[1], bandwidth=4, delay=20,
               sg_path=(1, 2, 3))
  test.add_req(sap2.ports[1], sap1.ports[1], bandwidth=4, delay=20,
               sg_path=(4, 5))
  return test


def generate_mn_test_req2 ():
  test = NFFG(id="SG-decomp", name="SG-name")
  sap1 = test.add_sap(name="SAP3", id="sap3")
  sap2 = test.add_sap(name="SAP4", id="sap4")
  comp = test.add_nf(id="comp", name="COMPRESSOR", func_type="headerCompressor",
                     cpu=1, mem=1, storage=0)
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1, storage=0)
  fwd = test.add_nf(id="fwd", name="FORWARDER", func_type="simpleForwarder",
                    cpu=1, mem=1, storage=0)
  test.add_sglink(sap1.add_port(1), comp.add_port(1), id=1)
  test.add_sglink(comp.ports[1], decomp.add_port(1), id=2)
  test.add_sglink(decomp.ports[1], sap2.add_port(1), id=3)
  test.add_sglink(sap2.ports[1], fwd.add_port(1), id=4)
  test.add_sglink(fwd.ports[1], sap1.ports[1], id=5)

  test.add_req(sap1.ports[1], sap2.ports[1], bandwidth=4, delay=20,
               sg_path=(1, 2, 3))
  test.add_req(sap2.ports[1], sap1.ports[1], bandwidth=4, delay=20,
               sg_path=(4, 5))
  return test


def generate_mn_req_hackathon ():
  test = NFFG(id="SG-hackathon", name="SG-name")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap3 = test.add_sap(name="SAP3", id="sap3")
  comp = test.add_nf(id="comp", name="COMPRESSOR", func_type="headerCompressor",
                     cpu=1, mem=1, storage=0)
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1, storage=0)
  fwd = test.add_nf(id="fwd", name="FORWARDER", func_type="simpleForwarder",
                    cpu=1, mem=1, storage=0)
  test.add_sglink(sap1.add_port(1), comp.add_port(1), id=1)
  test.add_sglink(comp.ports[1], decomp.add_port(1), id=2)
  test.add_sglink(decomp.ports[1], sap3.add_port(1), id=3)
  test.add_sglink(sap3.ports[1], fwd.add_port(1), id=4)
  test.add_sglink(fwd.ports[1], sap1.ports[1], id=5)

  test.add_req(sap1.ports[1], sap3.ports[1], bandwidth=4, delay=20,
               sg_path=(1, 2, 3))
  test.add_req(sap3.ports[1], sap1.ports[1], bandwidth=4, delay=20,
               sg_path=(4, 5))
  return test


def gen ():
  nffg = NFFG(id="SG-decomp", name="SG-name")
  sap1 = nffg.add_sap(name="SAP1", id="sap1")
  sap2 = nffg.add_sap(name="SAP2", id="sap2")
  nc1 = nffg.add_infra(id="nc1", name="NC1", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                       delay=0.9, bandwidth=5000)
  nc2 = nffg.add_infra(id="nc2", name="NC2", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                       delay=0.9, bandwidth=5000)
  comp = nffg.add_nf(id="comp", name="COMPRESSOR", func_type="headerCompressor",
                     cpu=2, mem=2, storage=0)
  decomp = nffg.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=2, mem=2, storage=0)
  linkres = {'delay': 1.5, 'bandwidth': 2000}
  nffg.add_link(sap1.add_port(1), nc1.add_port(1), id="l1", **linkres)
  nffg.add_link(nc1.add_port(2), nc2.add_port(2), id="l2", **linkres)
  nffg.add_link(nc2.add_port(1), sap2.add_port(1), id="l3", **linkres)
  nffg.duplicate_static_links()
  nffg.add_undirected_link(nc1.add_port(), comp.add_port(1), dynamic=True)
  nffg.add_undirected_link(nc1.add_port(), comp.add_port(2), dynamic=True)
  nffg.add_undirected_link(nc2.add_port(), decomp.add_port(1), dynamic=True)
  nffg.add_undirected_link(nc2.add_port(), decomp.add_port(2), dynamic=True)
  nc1.ports[1].add_flowrule(match="in_port=1;TAG=sap1-comp-139956882597136",
                            action="output=%s;UNTAG" % nc1.ports.container[
                              -1].id)
  nc2.ports[2].add_flowrule(match="in_port=2;UNTAG",
                            action="output=%s;TAG=sap1-comp-139956882597136" %
                                   nc2.ports.container[-1].id)
  p1 = nc1.ports.container[-1].id
  # nc1.ports[p1].add_flowrule(match="in_port=%s;TAG=comp-sap1-%s" % (p1, 42),
  # action="output=%s;UNTAG" % 1)
  nc1.ports[p1].add_flowrule(match="in_port=%s;" % p1,
                             action="output=%s;TAG=comp-sap1-%s" % (1, 42))
  p2 = nc2.ports.container[-1].id
  nc2.ports[p2].add_flowrule(match="in_port=%s;TAG=comp-sap1-%s" % (p2, 42),
                             action="output=%s;" % 1)
  return nffg


def generate_sdn_topo ():
  # Create NFFG
  nffg = NFFG(id="SDN", name="SDN-Topology")
  # Add MikroTik OF switches
  mt1 = nffg.add_infra(id="MT1", name="MikroTik-SW-1", domain=DOMAIN_SDN,
                       infra_type=NFFG.TYPE_INFRA_SDN_SW)
  mt2 = nffg.add_infra(id="MT2", name="MikroTik-SW-2", domain=DOMAIN_SDN,
                       infra_type=NFFG.TYPE_INFRA_SDN_SW)
  mt1.resources.delay = 0.2
  mt1.resources.bandwidth = 4000
  mt2.resources.delay = 0.2
  mt2.resources.bandwidth = 4000
  # Add SAPs
  sap14 = nffg.add_sap(id="SAP14", name="SAP14")
  sap24 = nffg.add_sap(id="SAP24", name="SAP24")
  sap34 = nffg.add_sap(id="SAP34", name="SAP34")
  # Add links
  l1 = nffg.add_link(mt1.add_port(1), mt2.add_port(1), id="sdn-link1")
  l2 = nffg.add_link(sap14.add_port(1), mt1.add_port(2), id="sdn-link2")
  mt1.add_port(3)
  mt1.add_port(4)
  l3 = nffg.add_link(mt2.add_port(2), sap24.add_port(1), id="sdn-link3")
  l4 = nffg.add_link(mt2.add_port(3), sap34.add_port(1), id="sdn-link4")
  mt2.add_port(4)
  l1.delay = 0.1
  l1.bandwidth = 1000
  l2.delay = 1.5
  l2.bandwidth = 1000
  l3.delay = 1.5
  l3.bandwidth = 1000
  l4.delay = 1.5
  l4.bandwidth = 1000
  return nffg


def generate_sdn_topo2 ():
  # Create NFFG
  nffg = NFFG(id="SDN", name="SDN-Topology")
  # Add MikroTik OF switches
  mt1 = nffg.add_infra(id="MT1", name="MikroTik-SW-1", domain=DOMAIN_SDN,
                       infra_type=NFFG.TYPE_INFRA_SDN_SW)
  mt1.resources.delay = 0.2
  mt1.resources.bandwidth = 4000
  # Add SAPs
  sap14 = nffg.add_sap(id="SAP14", name="SAP14")
  sap24 = nffg.add_sap(id="SAP24", name="SAP24")
  sap34 = nffg.add_sap(id="SAP34", name="SAP34")
  # Add links
  l1 = nffg.add_link(sap14.add_port(1), mt1.add_port(1), id="sdn-link1")
  l2 = nffg.add_link(sap24.add_port(1), mt1.add_port(2), id="sdn-link2")
  l3 = nffg.add_link(sap34.add_port(1), mt1.add_port(3), id="sdn-link3")
  l1.delay = 0.1
  l1.bandwidth = 1000
  l2.delay = 1.5
  l2.bandwidth = 1000
  l3.delay = 1.5
  l3.bandwidth = 1000
  return nffg


def generate_sdn_req ():
  # Create NFFG
  nffg = NFFG(id="SDN", name="SDN-Topology")
  # Add SAPs
  sap14 = nffg.add_sap(id="SAP14", name="SAP14")
  sap24 = nffg.add_sap(id="SAP24", name="SAP24")
  # sap34 = nffg.add_sap(id="SAP34", name="SAP34")
  sap14.add_port(1)
  sap24.add_port(1)
  # sap34.add_port(1)
  nffg.add_sglink(sap14.ports[1], sap24.ports[1], id=1)
  # nffg.add_sglink(sap14.ports[1], sap34.ports[1])
  # nffg.add_sglink(sap24.ports[1], sap14.ports[1])
  # nffg.add_sglink(sap34.ports[1], sap14.ports[1])
  nffg.add_req(sap14.ports[1], sap24.ports[1], bandwidth=10, delay=100, id=2)
  # nffg.add_req(sap14.ports[1], sap34.ports[1], bandwidth=10, delay=100)
  # nffg.add_req(sap24.ports[1], sap14.ports[1], bandwidth=10, delay=100)
  # nffg.add_req(sap34.ports[1], sap14.ports[1], bandwidth=10, delay=100)
  return nffg


def generate_os_req ():
  test = NFFG(id="OS-req", name="SG-name")
  sap1 = test.add_sap(name="SAP24", id="0")
  sap2 = test.add_sap(name="SAP42", id="1")
  webserver = test.add_nf(id="webserver", name="webserver",
                          func_type="webserver", cpu=1, mem=1, storage=0)
  # echo = test.add_nf(id="echo", name="echo", func_type="echo",
  #                    cpu=1, mem=1, storage=0)
  test.add_sglink(sap1.add_port(0), webserver.add_port(0), id=1)
  test.add_sglink(webserver.ports[0], sap2.add_port(0), id=2)

  # test.add_req(sap1.ports[0], webserver.ports[0], bandwidth=1, delay=20)
  # test.add_req(webserver.ports[0], sap2.ports[0], bandwidth=1, delay=20)
  test.add_req(sap1.ports[0], sap2.ports[0], bandwidth=1, delay=100)
  return test


def generate_os_mn_req ():
  test = NFFG(id="OS-MN-req", name="SG-name")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  # comp = test.add_nf(id="comp", name="COMPRESSOR",
  # func_type="headerCompressor",
  #                    cpu=1, mem=1, storage=0)
  # decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
  #                      func_type="headerDecompressor", cpu=1, mem=1,
  # storage=0)
  # fwd = test.add_nf(id="fwd", name="FORWARDER",
  #                   func_type="simpleForwarder", cpu=1, mem=1, storage=0)
  # sap14 = test.add_sap(name="SAP14", id="0")
  # sap24 = test.add_sap(name="SAP24", id="1")

  webserver = test.add_nf(id="webserver", name="webserver",
                          func_type="webserver", cpu=1, mem=1, storage=0)
  # echo = test.add_nf(id="echo", name="echo", func_type="echo",
  #                    cpu=1, mem=1, storage=0)
  test.add_sglink(sap1.add_port(0), webserver.add_port(0), id=1)
  test.add_sglink(webserver.ports[0], sap2.add_port(0), id=2)

  # test.add_req(sap1.ports[0], webserver.ports[0], bandwidth=1, delay=20)
  # test.add_req(webserver.ports[0], sap2.ports[0], bandwidth=1, delay=20)
  test.add_req(sap1.ports[0], sap2.ports[0], bandwidth=1, delay=100)
  return test


def generate_dov ():
  # Create NFFG
  nffg = NFFG(id="INTERNAL", name="SIGCOMM")
  # Add environments
  ee1 = nffg.add_infra(id="EE1", name="ee-infra-1", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                       delay=0.9, bandwidth=5000)
  ee2 = nffg.add_infra(id="EE2", name="ee-infra-2", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                       delay=0.9, bandwidth=5000)
  # Add supported types
  ee1.add_supported_type(
    ('headerCompressor', 'headerDecompressor', 'simpleForwarder'))
  ee2.add_supported_type(
    ('headerCompressor', 'headerDecompressor', 'simpleForwarder'))
  # Add OVS switches
  sw3 = nffg.add_infra(id="SW3", name="switch-3", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.2,
                       bandwidth=10000)
  sw4 = nffg.add_infra(id="SW4", name="switch-4", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.2,
                       bandwidth=10000)
  # Add SAPs
  sap1 = nffg.add_sap(id="SAP1", name="SAP1")
  sap2 = nffg.add_sap(id="SAP2", name="SAP2")
  # Add links
  link_res = {'delay': 1.5, 'bandwidth': 10}
  nffg.add_link(ee1.add_port(1), sw3.add_port(1), id="link1", **link_res)
  nffg.add_link(ee2.add_port(1), sw4.add_port(1), id="link2", **link_res)
  nffg.add_link(sw3.add_port(2), sw4.add_port(2), id="link3", **link_res)
  nffg.add_link(sw3.add_port(3), sap1.add_port(1), id="link4", **link_res)
  nffg.add_link(sw4.add_port(3), sap2.add_port(1), id="link5", **link_res)

  # Add MikroTik OF switches
  mt1 = nffg.add_infra(id="MT1", name="MikroTik-SW-1", domain=DOMAIN_SDN,
                       infra_type=NFFG.TYPE_INFRA_SDN_SW)
  mt2 = nffg.add_infra(id="MT2", name="MikroTik-SW-2", domain=DOMAIN_SDN,
                       infra_type=NFFG.TYPE_INFRA_SDN_SW)
  mt1.resources.delay = 0.2
  mt1.resources.bandwidth = 4000
  mt2.resources.delay = 0.2
  mt2.resources.bandwidth = 4000

  # Add links
  l11 = nffg.add_link(mt1.add_port(1), mt2.add_port(1), id="link11")
  l12 = nffg.add_link(sw4.add_port(4), mt1.add_port(2), id="link12")
  mt1.add_port(3)
  mt1.add_port(4)
  mt2.add_port(4)
  l11.delay = 0.1
  l11.bandwidth = 1000
  l12.delay = 1.5
  l12.bandwidth = 1000

  os_bb = nffg.add_infra(id="UUID-01", name="Single BiSBiS in OS Domain",
                         domain="OPENSTACK",
                         infra_type=NFFG.TYPE_INFRA_BISBIS, cpu=10, mem=32,
                         storage=5, delay=0, bandwidth=100000)
  # Add supported types
  os_bb.add_supported_type(('webserver', 'echo'))

  l21 = nffg.add_link(mt2.add_port(2), os_bb.add_port(0), id="link21")
  l21.delay = 10
  l21.bandwidth = 1000

  un_bb = nffg.add_infra(id="UUID11", name="Universal Node",
                         domain="UN",
                         infra_type=NFFG.TYPE_INFRA_BISBIS, cpu=5, mem=16,
                         storage=5, delay=0, bandwidth=100000)
  # Add supported types
  un_bb.add_supported_type(('dpi', 'example'))

  l31 = nffg.add_link(mt2.add_port(3), un_bb.add_port(1), id="link31")
  l31.delay = 10
  l31.bandwidth = 1000

  nffg.duplicate_static_links()
  return nffg


def generate_global_req ():
  test = NFFG(id="SIGCOMM-demo-req", name="SIGCOMM-2web-1dpi-2SAP-req")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  # comp = test.add_nf(id="comp", name="COMPRESSOR",
  # func_type="headerCompressor",
  #                    cpu=1, mem=1, storage=0)
  # decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
  #                      func_type="headerDecompressor", cpu=1, mem=1,
  # storage=0)
  # fwd = test.add_nf(id="fwd", name="FORWARDER",
  #                   func_type="simpleForwarder", cpu=1, mem=1, storage=0)

  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  webserver2 = test.add_nf(id="webserver2", name="webserver2",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
                    storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id='11')
  test.add_sglink(webserver1.ports[0], dpi.add_port(1), id='12')
  test.add_sglink(dpi.add_port(2), sap1.ports[1], id='13')

  test.add_sglink(sap2.add_port(1), webserver2.add_port(0), id='21')
  test.add_sglink(webserver2.ports[0], sap2.ports[1], id='22')

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=('11', '12', '13'))
  test.add_req(sap2.ports[1], sap2.ports[1], bandwidth=1, delay=100,
               sg_path=('21', '22'))

  return test


def generate_ewsdn_req1 ():
  test = NFFG(id="EWSDN-demo-req1", name="EWSDN-2web-2SAP-req")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")

  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  webserver2 = test.add_nf(id="webserver2", name="webserver2",
                           func_type="webserver", cpu=1, mem=1, storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id='11')
  test.add_sglink(webserver1.ports[0], sap1.ports[1], id='12')

  test.add_sglink(sap2.add_port(1), webserver2.add_port(0), id='21')
  test.add_sglink(webserver2.ports[0], sap2.ports[1], id='22')

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=('11', '12'))
  test.add_req(sap2.ports[1], sap2.ports[1], bandwidth=1, delay=100,
               sg_path=('21', '22'))

  return test


def generate_ewsdn_req2 ():
  test = NFFG(id="EWSDN-demo-req2", name="EWSDN-2web-1dpi-2SAP-req")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  # comp = test.add_nf(id="comp", name="COMPRESSOR",
  # func_type="headerCompressor",
  #                    cpu=1, mem=1, storage=0)
  # decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
  #                      func_type="headerDecompressor", cpu=1, mem=1,
  # storage=0)
  # fwd = test.add_nf(id="fwd", name="FORWARDER",
  #                   func_type="simpleForwarder", cpu=1, mem=1, storage=0)

  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  webserver2 = test.add_nf(id="webserver2", name="webserver2",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
                    storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id='11')
  test.add_sglink(webserver1.ports[0], dpi.add_port(1), id='12')
  test.add_sglink(dpi.add_port(2), sap1.ports[1], id='13')

  test.add_sglink(sap2.add_port(1), webserver2.add_port(0), id='21')
  test.add_sglink(webserver2.ports[0], sap2.ports[1], id='22')

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=('11', '12', '13'))
  test.add_req(sap2.ports[1], sap2.ports[1], bandwidth=1, delay=100,
               sg_path=('21', '22'))

  return test


def generate_ewsdn_req3 ():
  test = NFFG(id="EWSDN-demo-req3",
              name="EWSDN-2web-1dpi-1comp-1decomp-2SAP-req")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  comp = test.add_nf(id="comp", name="COMPRESSOR",
                     func_type="headerCompressor",
                     cpu=1, mem=1, storage=0)
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1,
                       storage=0)
  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  webserver2 = test.add_nf(id="webserver2", name="webserver2",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
                    storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id='11')
  test.add_sglink(webserver1.ports[0], dpi.add_port(1), id='12')
  test.add_sglink(dpi.add_port(2), comp.add_port(1), id='13')
  test.add_sglink(comp.ports[1], decomp.add_port(1), id='14')
  test.add_sglink(decomp.ports[1], sap1.ports[1], id='15')

  test.add_sglink(sap2.add_port(1), webserver2.add_port(0), id='21')
  test.add_sglink(webserver2.ports[0], sap2.ports[1], id='22')

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=('11', '12', '13', '14', '15'))
  test.add_req(sap2.ports[1], sap2.ports[1], bandwidth=1, delay=100,
               sg_path=('21', '22'))

  return test


def test_conversion ():
  from escape.util.conversion import NFFGConverter
  with open("/home/czentye/escape/src/escape_v2/tools/os_domain.xml") as f:
    os_nffg, os_virt = NFFGConverter(
      domain="OPENSTACK").parse_from_Virtualizer(f.read(), with_virt=True)
  with open("/home/czentye/escape/src/escape_v2/tools/un_domain.xml") as f:
    un_nffg, un_virt = NFFGConverter(
      domain="UN").parse_from_Virtualizer(f.read(), with_virt=True)
  with open("/home/czentye/escape/src/escape_v2/pox/escape-mn-topo.nffg") as f:
    internal = NFFG.parse(f.read())
    internal.duplicate_static_links()
  # print
  # pprint(os_nffg.network.__dict__)
  # print
  # pprint(un_nffg.network.__dict__)
  # print
  # pprint(internal.network.__dict__)

  merged = NFFGToolBox.merge_new_domain(internal, os_nffg)
  merged = NFFGToolBox.merge_new_domain(merged, un_nffg)

  # pprint(merged.network.__dict__)
  print
  splitted = NFFGToolBox.split_into_domains(merged)
  print splitted
  # for d, p in splitted:
  #   print "\n", d
  #   print p.dump()
  os_virt.nodes['UUID-01'].clearData()
  os_virt.nodes['UUID-01'].flowtable.clearData()
  print
  print str(os_virt)
  os_splitted = [n for d, n in splitted if d == "OPENSTACK"][0]
  os_splitted['UUID-01'].domain = "UN"
  os_splitted['UUID-01'].ports[0].add_flowrule(match="in_port=0;TAG=42",
                                               action="output=3;UNTAG")
  os_splitted['UUID-01'].ports[2].add_flowrule(match="in_port=2;UNTAG",
                                               action="output=1;TAG=24")

  print os_splitted.dump()


def generate_merged_mapped ():
  with open("/home/czentye/escape/src/escape_v2/pox/merged-global.nffg") as f:
    nffg = NFFG.parse(f.read())
  nffg.id = "test-mapped-web-dpi"
  nffg.name = "Test-NFFG"
  nf_dpi = nffg.add_nf(id="dpi", name="DPI", func_type="dpi")
  nf_web = nffg.add_nf(id="webserver", name="Webserver", func_type="webserver")
  nffg.add_undirected_link(port1=nf_dpi.add_port(1),
                           port2=nffg['UUID11'].add_port(111), dynamic=True)
  nffg.add_undirected_link(port1=nf_dpi.add_port(2),
                           port2=nffg['UUID11'].add_port(222), dynamic=True)
  nffg.add_undirected_link(port1=nf_web.add_port(0),
                           port2=nffg['UUID-01'].add_port(100), dynamic=True)
  nffg.add_undirected_link(port1=nf_web.add_port(1),
                           port2=nffg['UUID-01'].add_port(111), dynamic=True)
  # UN domain flowrules
  nffg['UUID11'].ports[1].add_flowrule("in_port=1;TAG=4242", "output=111;UNTAG")
  nffg['UUID11'].ports[222].add_flowrule("in_port=222", "output=1;TAG=2424")

  # OS domain flowrules
  nffg['UUID-01'].ports[0].add_flowrule("in_port=0;TAG=1313",
                                        "output=100;UNTAG")
  nffg['UUID-01'].ports[111].add_flowrule("in_port=111", "output=0;TAG=3131")
  return nffg.dump()


def generate_simple_test_topo ():
  # Create NFFG
  nffg = NFFG(id="TEST", name="Simple-Test-Topology")
  # Add environments
  ee1 = nffg.add_infra(id="EE1", name="ee-infra-1", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                       delay=0.9, bandwidth=5000)
  # Add supported types
  ee1.add_supported_type(
    ('headerCompressor', 'headerDecompressor', 'simpleForwarder', 'ovs'))
  # Add SAPs
  sap1 = nffg.add_sap(id="SAP1", name="SAP1")
  sap2 = nffg.add_sap(id="SAP2", name="SAP2")

  # Add links
  link_res = {'delay': 1.5, 'bandwidth': 10}
  nffg.add_link(sap1.add_port(1), ee1.add_port(1), id="mn-link1", **link_res)
  nffg.add_link(sap2.add_port(1), ee1.add_port(2), id="mn-link2", **link_res)
  # nffg.duplicate_static_links()
  return nffg


def generate_simple_test_req ():
  test = NFFG(id="Simple-test-req", name="Simple test request")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  ovs = test.add_nf(id="ovs", name="OVS switch", func_type="ovs",
                    cpu=1, mem=1, storage=0)
  test.add_sglink(sap1.add_port(1), ovs.add_port(1), id=1)
  test.add_sglink(ovs.ports[1], sap2.add_port(1), id=2)

  test.add_req(sap1.ports[1], sap2.ports[1], bandwidth=1, delay=10,
               sg_path=(1, 2))
  return test


def generate_hwloc2nffg_test_req ():
  test = NFFG(id="Dataplane-req", name="Dataplane-req")
  wlan0 = test.add_sap(name="wlan0", id="wlan0")
  eth0 = test.add_sap(name="eth0", id="eth0")
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1, storage=0)
  # wlan0 --> decomp --> eth0 --> wlan0
  test.add_sglink(wlan0.add_port(38), decomp.add_port(1), id=1)
  test.add_sglink(decomp.ports[1], eth0.add_port(34), id=2)
  test.add_sglink(eth0.ports[34], wlan0.ports[38], id=3)

  test.add_req(wlan0.ports[38], eth0.ports[34], bandwidth=50, delay=100,
               sg_path=(1, 2))
  test.add_req(eth0.ports[34], wlan0.ports[38], bandwidth=50, delay=100,
               sg_path=(3,))
  return test


def generate_5gex_req0 ():
  test = NFFG(id="SG-1", name="SG-name1")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")

  test.add_sglink(sap1.add_port(1), sap2.add_port(1), id=1)
  test.add_sglink(sap1.ports[1], sap2.ports[1], id=2)

  test.add_req(sap1.ports[1], sap2.ports[1], bandwidth=4, delay=20,
               sg_path=(1, 2))
  return test


def generate_5gex_req1 ():
  test = NFFG(id="SG-1", name="SG-name1")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  bridge = test.add_nf(id="bridge", name="BRIDGE", func_type="bridge",
                       cpu=1, mem=1, storage=0)
  fwd = test.add_nf(id="fwd", name="FORWARDER", func_type="simpleForwarder",
                    cpu=1, mem=1, storage=0)
  test.add_sglink(sap1.add_port(1), bridge.add_port(1), id=1)
  test.add_sglink(bridge.add_port(2), sap2.add_port(1), id=2)
  test.add_sglink(sap2.ports[1], fwd.add_port(1), id=3)
  test.add_sglink(fwd.ports[1], sap1.ports[1], id=4)

  test.add_req(sap1.ports[1], sap2.ports[1], bandwidth=4, delay=20,
               sg_path=(1, 2))
  test.add_req(sap2.ports[1], sap1.ports[1], bandwidth=4, delay=20,
               sg_path=(3, 4))
  return test


def generate_5gex_req2 ():
  test = NFFG(id="SG-2", name="SG-name2")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  comp = test.add_nf(id="comp", name="COMPRESSOR", func_type="headerCompressor",
                     cpu=1, mem=1, storage=0)
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1, storage=0)
  fwd = test.add_nf(id="fwd", name="FORWARDER", func_type="simpleForwarder",
                    cpu=1, mem=1, storage=0)
  test.add_sglink(sap1.add_port(1), comp.add_port(1), id=1)
  test.add_sglink(comp.ports[1], decomp.add_port(1), id=2)
  test.add_sglink(decomp.ports[1], sap2.add_port(1), id=3)
  test.add_sglink(sap2.ports[1], fwd.add_port(1), id=4)
  test.add_sglink(fwd.ports[1], sap1.ports[1], id=5)

  test.add_req(sap1.ports[1], sap2.ports[1], bandwidth=4, delay=20,
               sg_path=(1, 2, 3))
  test.add_req(sap2.ports[1], sap1.ports[1], bandwidth=4, delay=20,
               sg_path=(4, 5))
  return test


def generate_req_verification ():
  test = NFFG(id="verification-2sap-web-fw-dpi-nat",
              name="verification-2sap-web-fw-dpi-nat")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  sap3 = test.add_sap(name="SAP3", id="sap3")
  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  nat = test.add_nf(id="nat", name="NAT", func_type="nat",
                    cpu=1, mem=1, storage=0)
  fw = test.add_nf(id="fw", name="FIREWALL", func_type="firewall",
                   cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi",
                    cpu=1, mem=1, storage=0)

  test.add_sglink(sap1.add_port(1), nat.add_port(1), id=11)
  test.add_sglink(nat.add_port(2), webserver1.add_port(1), id=12)
  test.add_sglink(webserver1.ports[1], fw.add_port(1), id=13,
                  flowclass='dl_type=0x0800,nw_dst=20.0.0.1')
  test.add_sglink(fw.add_port(2), nat.ports[2], id=14)
  test.add_sglink(nat.ports[1], sap1.ports[1], id=15,
                  flowclass='dl_type=0x0800,nw_dst=10.0.0.1')

  test.add_sglink(sap2.add_port(1), nat.ports[1], id=21)
  test.add_sglink(nat.ports[1], dpi.add_port(1), id=25,
                  flowclass='dl_type=0x0800,nw_dst=10.0.0.2')
  test.add_sglink(dpi.add_port(2), sap2.ports[1], id=26)

  test.add_sglink(sap3.add_port(1), webserver1.ports[1], id=31)
  test.add_sglink(webserver1.ports[1], sap3.ports[1], id=32,
                  flowclass='dl_type=0x0800,nw_dst=20.0.0.3')

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=(11, 12, 13, 14, 15))
  # test.add_req(sap2.ports[1], sap2.ports[1], bandwidth=1, delay=100,
  #              sg_path=(21, 22, 14, 23))
  return test


def generate_etsi_req1a ():
  test = NFFG(id="ETSI-1sap-web", name="ETSI-1sap-web")
  sap1 = test.add_sap(name="SAP1", id="SAP1")

  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
  test.add_sglink(webserver1.ports[0], sap1.ports[1], id=12,
                  flowclass='dl_dst=00:00:00:00:00:01')

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=(11, 12))
  return test


def generate_etsi_req1b ():
  test = NFFG(id="ETSI-2sap-web", name="ETSI-2sap-web")
  sap1 = test.add_sap(name="SAP1", id="SAP1")
  sap2 = test.add_sap(name="SAP2", id="SAP2")

  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
  test.add_sglink(webserver1.ports[0], sap1.ports[1], id=12,
                  flowclass='dl_dst=00:00:00:00:00:01')
  test.add_sglink(sap2.add_port(1), webserver1.ports[0], id=21)
  test.add_sglink(webserver1.ports[0], sap2.ports[1], id=22,
                  flowclass='dl_dst=00:00:00:00:00:02')

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=(11, 12))
  return test


def generate_etsi_req2a ():
  test = NFFG(id="ETSI-1sap-web-dpi", name="ETSI-1sap-web-dpi")
  sap1 = test.add_sap(name="SAP1", id="SAP1")

  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
                    storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
  test.add_sglink(webserver1.ports[0], dpi.add_port(1), id=12,
                  flowclass='dl_dst=00:00:00:00:00:01')
  test.add_sglink(dpi.add_port(2), sap1.ports[1], id=13)

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=(11, 12, 13))
  return test


def generate_etsi_req2b ():
  test = NFFG(id="ETSI-2sap-web-dpi", name="ETSI-2sap-web-dpi")
  sap1 = test.add_sap(name="SAP1", id="SAP1")
  sap2 = test.add_sap(name="SAP2", id="SAP2")

  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
                    storage=0)
  # fwd = test.add_nf(id="fwd", name="FORWARDER", func_type="simpleForwarder",
  #                   cpu=1, mem=1, storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
  test.add_sglink(webserver1.ports[0], dpi.add_port(1), id=12,
                  flowclass='dl_dst=00:00:00:00:00:01')
  test.add_sglink(dpi.add_port(2), sap1.ports[1], id=13)

  # test.add_sglink(sap2.add_port(1), fwd.add_port(1), id=21)
  # test.add_sglink(fwd.ports[1], webserver1.ports[0], id=22)
  # test.add_sglink(webserver1.ports[0], sap2.ports[1], id=23,
  # flowclass='dl_dst=00:00:00:00:00:02')
  test.add_sglink(sap2.add_port(1), webserver1.ports[0], id=21)
  test.add_sglink(webserver1.ports[0], sap2.ports[1], id=22,
                  flowclass='dl_dst=00:00:00:00:00:02')

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=(11, 12, 13))
  test.add_req(sap2.ports[1], sap2.ports[1], bandwidth=1, delay=100,
               sg_path=(21, 22))
  return test


def generate_etsi_req3a ():
  test = NFFG(id="ETSI-1sap-web-dpi-comp-decomp",
              name="ETSI-1sap-web-dpi-comp-decomp")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  comp = test.add_nf(id="comp", name="COMPRESSOR",
                     func_type="headerCompressor",
                     cpu=1, mem=1, storage=0)
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1,
                       storage=0)
  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
                    storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
  test.add_sglink(webserver1.ports[0], dpi.add_port(1), id=12,
                  flowclass='dl_dst=00:00:00:00:00:01')
  test.add_sglink(dpi.add_port(2), comp.add_port(1), id=13)
  test.add_sglink(comp.ports[1], decomp.add_port(1), id=14)
  test.add_sglink(decomp.ports[1], sap1.ports[1], id=15)

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=(11, 12, 13, 14, 15))
  return test


def generate_etsi_req3b ():
  test = NFFG(id="ETSI-2sap-web-dpi-comp-decomp",
              name="ETSI-2sap-web-dpi-comp-decomp")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  comp = test.add_nf(id="comp", name="COMPRESSOR",
                     func_type="headerCompressor",
                     cpu=1, mem=1, storage=0)
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1,
                       storage=0)
  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
                    storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
  test.add_sglink(webserver1.ports[0], dpi.add_port(1), id=12,
                  flowclass='dl_dst=00:00:00:00:00:01')
  test.add_sglink(dpi.add_port(2), comp.add_port(1), id=13)
  test.add_sglink(comp.ports[1], decomp.add_port(1), id=14)
  test.add_sglink(decomp.ports[1], sap1.ports[1], id=15,
                  flowclass='dl_type=0x0800,nw_dst=10.0.0.1')

  test.add_sglink(sap2.add_port(1), webserver1.ports[0], id=21)
  test.add_sglink(webserver1.ports[0], comp.ports[1], id=22,
                  flowclass='dl_dst=00:00:00:00:00:02')
  test.add_sglink(decomp.ports[1], sap2.ports[1], id=23,
                  flowclass='dl_type=0x0800,nw_dst=10.0.0.2')

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=(11, 12, 13, 14, 15))
  # test.add_req(sap2.ports[1], sap2.ports[1], bandwidth=1, delay=100,
  #              sg_path=(21, 22, 14, 23))
  return test


def generate_etsi_req3b2 ():
  test = NFFG(id="ETSI-2sap-web-dpi-comp-decomp-onlysap1",
              name="ETSI-2sap-web-dpi-comp-decomp-onlysap1")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  comp = test.add_nf(id="comp", name="COMPRESSOR",
                     func_type="headerCompressor",
                     cpu=1, mem=1, storage=0)
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1,
                       storage=0)
  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
                    storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
  test.add_sglink(webserver1.ports[0], dpi.add_port(1), id=12,
                  flowclass='dl_dst=00:00:00:00:00:01')
  test.add_sglink(dpi.add_port(2), comp.add_port(1), id=13)
  test.add_sglink(comp.ports[1], decomp.add_port(1), id=14)
  test.add_sglink(decomp.ports[1], sap1.ports[1], id=15)

  test.add_sglink(sap2.add_port(1), webserver1.ports[0], id=21)
  test.add_sglink(webserver1.ports[0], sap2.ports[1], id=22,
                  flowclass='dl_dst=00:00:00:00:00:02')

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=(11, 12, 13, 14, 15))
  # test.add_req(sap2.ports[1], sap2.ports[1], bandwidth=1, delay=100,
  #              sg_path=(21, 22, 14, 23))
  return test


def generate_etsi_req4b2a ():
  test = NFFG(id="ETSI-2sap-web-dpi-bridge-comp-decomp-onlysap1",
              name="ETSI-2sap-web-dpi-bridge-comp-decomp-onlysap1")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  comp = test.add_nf(id="comp", name="COMPRESSOR",
                     func_type="headerCompressor",
                     cpu=1, mem=1, storage=0)
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1,
                       storage=0)
  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
                    storage=0)
  bridge = test.add_nf(id="dockernf", name="dockernf", func_type="bridge",
                       cpu=1, mem=1,
                       storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
  test.add_sglink(webserver1.ports[0], dpi.add_port(1), id=12,
                  flowclass='dl_dst=00:00:00:00:00:01')
  test.add_sglink(dpi.add_port(2), bridge.add_port(1), id=13)
  test.add_sglink(bridge.add_port(2), comp.add_port(1), id=14)
  test.add_sglink(comp.ports[1], decomp.add_port(1), id=15)
  test.add_sglink(decomp.ports[1], sap1.ports[1], id=16)

  test.add_sglink(sap2.add_port(1), webserver1.ports[0], id=21)
  test.add_sglink(webserver1.ports[0], sap2.ports[1], id=22,
                  flowclass='dl_dst=00:00:00:00:00:02')

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=(11, 12, 13, 14, 15, 16))
  # test.add_req(sap2.ports[1], sap2.ports[1], bandwidth=1, delay=100,
  #              sg_path=(21, 22, 14, 23))
  return test


def generate_etsi_req4b2b ():
  test = NFFG(id="ETSI-2sap-web-dpi-bridge+-comp-decomp-onlysap1",
              name="ETSI-2sap-web-dpi-bridge+-comp-decomp-onlysap1")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  comp = test.add_nf(id="comp", name="COMPRESSOR",
                     func_type="headerCompressor",
                     cpu=1, mem=1, storage=0)
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1,
                       storage=0)
  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
                    storage=0)
  bridge = test.add_nf(id="dockernf", name="dockernf", func_type="bridge",
                       cpu=1, mem=1,
                       storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
  test.add_sglink(webserver1.ports[0], dpi.add_port(1), id=12,
                  flowclass='dl_dst=00:00:00:00:00:01')
  test.add_sglink(dpi.add_port(2), bridge.add_port(1), id=13)
  test.add_sglink(bridge.add_port(2), comp.add_port(1), id=14)
  test.add_sglink(comp.ports[1], decomp.add_port(1), id=15)
  test.add_sglink(decomp.ports[1], sap1.ports[1], id=16)

  test.add_sglink(sap2.add_port(1), webserver1.ports[0], id=21)
  test.add_sglink(webserver1.ports[0], sap2.ports[1], id=22,
                  flowclass='dl_dst=00:00:00:00:00:02')
  test.add_sglink(bridge.add_port(3), sap2.ports[1], id=23)

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=(11, 12, 13, 14, 15, 16))
  # test.add_req(sap2.ports[1], sap2.ports[1], bandwidth=1, delay=100,
  #              sg_path=(21, 22, 14, 23))
  return test


def generate_etsi_req4b2b_robot1 ():
  test = NFFG(id="ETSI-2sap-web-dpi-bridge+-comp-decomp-onlysap1+robot1",
              name="ETSI-2sap-web-dpi-bridge+-comp-decomp-onlysap1+robot1")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap2 = test.add_sap(name="SAP2", id="sap2")
  comp = test.add_nf(id="comp", name="COMPRESSOR",
                     func_type="headerCompressor",
                     cpu=1, mem=1, storage=0)
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1,
                       storage=0)
  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
                    storage=0)
  bridge = test.add_nf(id="dockernf", name="dockernf", func_type="bridge",
                       cpu=1, mem=1,
                       storage=0)
  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
  test.add_sglink(webserver1.ports[0], dpi.add_port(1), id=12,
                  flowclass='dl_dst=00:00:00:00:00:01')
  test.add_sglink(dpi.add_port(2), bridge.add_port(1), id=13)
  test.add_sglink(bridge.add_port(2), comp.add_port(1), id=14)
  test.add_sglink(comp.ports[1], decomp.add_port(1), id=15)
  test.add_sglink(decomp.ports[1], sap1.ports[1], id=16)

  test.add_sglink(sap2.add_port(1), webserver1.ports[0], id=21)
  test.add_sglink(webserver1.ports[0], sap2.ports[1], id=22,
                  flowclass='dl_dst=00:00:00:00:00:02')
  test.add_sglink(bridge.add_port(3), sap2.ports[1], id=23)

  sap54 = test.add_sap(name="SAP54", id="SAP54")
  balancer1 = test.add_nf(id="balance_server1", name="balance_server1",
                          func_type="balance_server", cpu=1, mem=1,
                          storage=0)
  balancer2 = test.add_nf(id="balance_server2", name="balance_server2",
                          func_type="balance_server", cpu=1, mem=1,
                          storage=0)
  splitter1 = test.add_nf(id="splitter", name="splitter", func_type="splitter",
                          cpu=1, mem=1, storage=0)
  test.add_sglink(sap54.add_port(1), splitter1.add_port(1), id=31,
                  flowclass='dl_src=bc:ee:7b:e6:8c:07')
  test.add_sglink(splitter1.add_port(2), balancer1.add_port(1), id=32)
  test.add_sglink(splitter1.add_port(3), balancer2.add_port(1), id=33)
  test.add_sglink(balancer1.ports[1], sap54.ports[1], id=34)
  test.add_sglink(balancer2.ports[1], sap54.ports[1], id=35)

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=(11, 12, 13, 14, 15, 16))
  # test.add_req(sap2.ports[1], sap2.ports[1], bandwidth=1, delay=100,
  #              sg_path=(21, 22, 14, 23))
  return test


# def generate_etsi_req4a ():
#   test = NFFG(id="ETSI-1sap-web-dpi-bridge-comp-decomp",
#               name="ETSI-1sap-web-dpi-bridge-comp-decomp")
#   sap1 = test.add_sap(name="SAP1", id="sap1")
#   comp = test.add_nf(id="comp", name="COMPRESSOR",
#                      func_type="headerCompressor",
#                      cpu=1, mem=1, storage=0)
#   decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
#                        func_type="headerDecompressor", cpu=1, mem=1,
#                        storage=0)
#   webserver1 = test.add_nf(id="webserver1", name="webserver1",
#                            func_type="webserver", cpu=1, mem=1, storage=0)
#   dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
#                     storage=0)
#   bridge = test.add_nf(id="dockernf", name="dockernf", func_type="bridge",
# cpu=1, mem=1,
#                     storage=0)

#   test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
#   test.add_sglink(webserver1.ports[0], dpi.add_port(1), id=12,
# flowclass='dl_dst=00:00:00:00:00:01')
#   test.add_sglink(dpi.add_port(2), bridge.add_port(1), id=13)
#   test.add_sglink(bridge.add_port(2), comp.add_port(1), id=14)
#   test.add_sglink(comp.ports[1], decomp.add_port(1), id=15)
#   test.add_sglink(decomp.ports[1], sap1.ports[1], id=16)

#   test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
#                sg_path=(11, 12, 13, 14, 15, 16))
#   return test


# def generate_etsi_req4b ():
#   test = NFFG(id="ETSI-2sap-web-dpi-bridge-comp-decomp",
#               name="ETSI-2sap-web-dpi-bridge-comp-decomp")
#   sap1 = test.add_sap(name="SAP1", id="sap1")
#   sap2 = test.add_sap(name="SAP2", id="sap2")
#   comp = test.add_nf(id="comp", name="COMPRESSOR",
#                      func_type="headerCompressor",
#                      cpu=1, mem=1, storage=0)
#   decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
#                        func_type="headerDecompressor", cpu=1, mem=1,
#                        storage=0)
#   webserver1 = test.add_nf(id="webserver1", name="webserver1",
#                            func_type="webserver", cpu=1, mem=1, storage=0)
#   dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
#                     storage=0)
#   bridge = test.add_nf(id="dockernf", name="dockernf", func_type="bridge",
# cpu=1, mem=1,
#                     storage=0)

#   test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
#   test.add_sglink(webserver1.ports[0], dpi.add_port(1), id=12,
# flowclass='dl_dst=00:00:00:00:00:01')
#   test.add_sglink(dpi.add_port(2), bridge.add_port(1), id=13)
#   test.add_sglink(bridge.add_port(2), comp.add_port(1), id=14)
#   test.add_sglink(comp.ports[1], decomp.add_port(1), id=15)
#   test.add_sglink(decomp.ports[1], sap1.ports[1], id=16)

#   test.add_sglink(sap2.add_port(1), webserver1.ports[0], id=21)
#   test.add_sglink(webserver1.ports[0], bridge.add_port(3), id=22,
# flowclass='dl_dst=00:00:00:00:00:02')
#   test.add_sglink(bridge.add_port(4), sap2.ports[1], id=23)

#   test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
#                sg_path=(11, 12, 13, 14, 15, 16))
#   test.add_req(sap2.ports[1], sap2.ports[1], bandwidth=1, delay=100,
#                sg_path=(21, 22, 23))
#   return test


def generate_etsi_req4a_robot1 ():
  test = NFFG(id="ETSI-1sap-web-dpi-bridge-comp-decomp-rob1",
              name="ETSI-1sap-web-dpi-bridge-comp-decomp-rob1")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap54 = test.add_sap(name="SAP54", id="SAP54")
  comp = test.add_nf(id="comp", name="COMPRESSOR",
                     func_type="headerCompressor",
                     cpu=1, mem=1, storage=0)
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1,
                       storage=0)
  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
                    storage=0)
  bridge = test.add_nf(id="dockernf", name="dockernf", func_type="bridge",
                       cpu=1, mem=1,
                       storage=0)
  balancer1 = test.add_nf(id="balance_server1", name="balance_server1",
                          func_type="balance_server", cpu=3, mem=1,
                          storage=0)
  balancer2 = test.add_nf(id="balance_server2", name="balance_server2",
                          func_type="balance_server", cpu=3, mem=1,
                          storage=0)
  splitter1 = test.add_nf(id="splitter", name="splitter", func_type="splitter",
                          cpu=1, mem=1, storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
  test.add_sglink(webserver1.ports[0], dpi.add_port(1), id=12,
                  flowclass='dl_dst=00:00:00:00:00:01')
  test.add_sglink(dpi.add_port(2), bridge.add_port(1), id=13)
  test.add_sglink(bridge.add_port(2), comp.add_port(1), id=14)
  test.add_sglink(comp.ports[1], decomp.add_port(1), id=15)
  test.add_sglink(decomp.ports[1], sap1.ports[1], id=16)

  test.add_sglink(sap54.add_port(1), splitter1.add_port(1), id=21,
                  flowclass='dl_src=bc:ee:7b:e6:8c:07')
  test.add_sglink(splitter1.add_port(2), balancer1.add_port(1), id=22)
  test.add_sglink(splitter1.add_port(3), balancer2.add_port(1), id=23)
  test.add_sglink(balancer1.ports[1], sap54.ports[1], id=24)
  test.add_sglink(balancer2.ports[1], sap54.ports[1], id=25)

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=(11, 12, 13, 14, 15, 16))
  test.add_req(sap54.ports[1], sap54.ports[1], bandwidth=1, delay=50,
               sg_path=(21, 22, 24))
  return test


def generate_etsi_req4a_robot12 ():
  test = NFFG(id="ETSI-1sap-web-dpi-bridge-comp-decomp-rob12",
              name="ETSI-1sap-web-dpi-bridge-comp-decomp-rob12")
  sap1 = test.add_sap(name="SAP1", id="sap1")
  sap54 = test.add_sap(name="SAP54", id="SAP54")
  comp = test.add_nf(id="comp", name="COMPRESSOR",
                     func_type="headerCompressor",
                     cpu=1, mem=1, storage=0)
  decomp = test.add_nf(id="decomp", name="DECOMPRESSOR",
                       func_type="headerDecompressor", cpu=1, mem=1,
                       storage=0)
  webserver1 = test.add_nf(id="webserver1", name="webserver1",
                           func_type="webserver", cpu=1, mem=1, storage=0)
  dpi = test.add_nf(id="dpi", name="DPI", func_type="dpi", cpu=1, mem=1,
                    storage=0)
  bridge = test.add_nf(id="dockernf", name="dockernf", func_type="bridge",
                       cpu=1, mem=1,
                       storage=0)
  balancer1 = test.add_nf(id="balance_server1", name="balance_server1",
                          func_type="balance_server", cpu=3, mem=1,
                          storage=0)
  balancer2 = test.add_nf(id="balance_server2", name="balance_server2",
                          func_type="balance_server", cpu=3, mem=1,
                          storage=0)
  splitter1 = test.add_nf(id="splitter", name="splitter", func_type="splitter",
                          cpu=1, mem=1, storage=0)
  balancer3 = test.add_nf(id="balance_server3", name="balance_server3",
                          func_type="balance_server", cpu=1, mem=1,
                          storage=0)
  balancer4 = test.add_nf(id="balance_server4", name="balance_server4",
                          func_type="balance_server", cpu=1, mem=1,
                          storage=0)
  splitter2 = test.add_nf(id="splitter2", name="splitter2",
                          func_type="splitter",
                          cpu=1, mem=1, storage=0)

  test.add_sglink(sap1.add_port(1), webserver1.add_port(0), id=11)
  test.add_sglink(webserver1.ports[0], dpi.add_port(1), id=12,
                  flowclass='dl_dst=00:00:00:00:00:01')
  test.add_sglink(dpi.add_port(2), bridge.add_port(1), id=13)
  test.add_sglink(bridge.add_port(2), comp.add_port(1), id=14)
  test.add_sglink(comp.ports[1], decomp.add_port(1), id=15)
  test.add_sglink(decomp.ports[1], sap1.ports[1], id=16)

  test.add_sglink(sap54.add_port(1), splitter1.add_port(1), id=21,
                  flowclass='dl_src=bc:ee:7b:e6:8c:07')
  test.add_sglink(splitter1.add_port(2), balancer1.add_port(1), id=22)
  test.add_sglink(splitter1.add_port(3), balancer2.add_port(1), id=23)
  test.add_sglink(balancer1.ports[1], sap54.ports[1], id=24)
  test.add_sglink(balancer2.ports[1], sap54.ports[1], id=25)

  test.add_sglink(sap54.ports[1], splitter2.add_port(1), id=31,
                  flowclass='dl_src=9c:5c:8e:af:2e:e0')
  test.add_sglink(splitter2.add_port(2), balancer3.add_port(1), id=32)
  test.add_sglink(splitter2.add_port(3), balancer4.add_port(1), id=33)
  test.add_sglink(balancer3.ports[1], sap54.ports[1], id=34)
  test.add_sglink(balancer4.ports[1], sap54.ports[1], id=35)

  test.add_req(sap1.ports[1], sap1.ports[1], bandwidth=1, delay=100,
               sg_path=(11, 12, 13, 14, 15, 16))
  test.add_req(sap54.ports[1], sap54.ports[1], bandwidth=1, delay=50,
               sg_path=(21, 22, 24))
  return test


def generate_etsi_req_robot1 ():
  test = NFFG(id="SG-robot1", name="SG-robot1")
  sap54 = test.add_sap(name="SAP54", id="SAP54")
  balancer1 = test.add_nf(id="balance_server1", name="balance_server1",
                          func_type="balance_server", cpu=3, mem=1,
                          storage=0)
  balancer2 = test.add_nf(id="balance_server2", name="balance_server2",
                          func_type="balance_server", cpu=3, mem=1,
                          storage=0)
  splitter1 = test.add_nf(id="splitter", name="splitter", func_type="splitter",
                          cpu=1, mem=1, storage=0)

  test.add_sglink(sap54.add_port(1), splitter1.add_port(1), id=11,
                  flowclass='dl_src=bc:ee:7b:e6:8c:07')
  test.add_sglink(splitter1.add_port(2), balancer1.add_port(1), id=12)
  test.add_sglink(splitter1.add_port(3), balancer2.add_port(1), id=13)

  test.add_sglink(balancer1.ports[1], sap54.ports[1], id=14)
  test.add_sglink(balancer2.ports[1], sap54.ports[1], id=15)

  test.add_req(sap54.ports[1], sap54.ports[1], bandwidth=1, delay=50,
               sg_path=(11, 12, 14))
  return test


def generate_etsi_req_robot1_simple ():
  test = NFFG(id="SG-robot1-simple", name="SG-robot1-simple")
  sap54 = test.add_sap(name="SAP54", id="SAP54")
  balancer1 = test.add_nf(id="balance_server1", name="balance_server1",
                          func_type="balance_server", cpu=1, mem=1,
                          storage=0)
  # balancer2 = test.add_nf(id="balance_server2", name="balance_server2",
  #                         func_type="balance_server", cpu=3, mem=1,
  #                         storage=0)
  splitter1 = test.add_nf(id="splitter", name="splitter", func_type="splitter",
                          cpu=1, mem=1, storage=0)

  test.add_sglink(sap54.add_port(1), splitter1.add_port(1), id=11,
                  flowclass='dl_src=bc:ee:7b:e6:8c:07')
  test.add_sglink(splitter1.add_port(2), balancer1.add_port(1), id=12)
  # test.add_sglink(splitter1.add_port(3), balancer2.add_port(1), id=13)

  test.add_sglink(balancer1.ports[1], sap54.ports[1], id=14)
  # test.add_sglink(balancer2.ports[1], sap54.ports[1], id=15)

  test.add_req(sap54.ports[1], sap54.ports[1], bandwidth=1, delay=50,
               sg_path=(11, 12))
  return test


def generate_etsi_req_robot2 ():
  test = NFFG(id="SG-robot2", name="SG-robot2")
  sap54 = test.add_sap(name="SAP54", id="SAP54")
  balancer3 = test.add_nf(id="balance_server3", name="balance_server3",
                          func_type="balance_server", cpu=1, mem=1,
                          storage=0)
  balancer4 = test.add_nf(id="balance_server4", name="balance_server4",
                          func_type="balance_server", cpu=1, mem=1,
                          storage=0)
  splitter2 = test.add_nf(id="splitter2", name="splitter2",
                          func_type="splitter",
                          cpu=1, mem=1, storage=0)

  test.add_sglink(sap54.add_port(1), splitter2.add_port(1), id=21,
                  flowclass='dl_src=9c:5c:8e:af:2e:e0')
  test.add_sglink(splitter2.add_port(2), balancer3.add_port(1), id=22)
  test.add_sglink(splitter2.add_port(3), balancer4.add_port(1), id=23)
  test.add_sglink(balancer3.ports[1], sap54.ports[1], id=24)
  test.add_sglink(balancer4.ports[1], sap54.ports[1], id=25)

  test.add_req(sap54.ports[1], sap54.ports[1], bandwidth=1, delay=50,
               sg_path=(21, 22, 24))
  return test


def generate_etsi_req_robot12 ():
  test = NFFG(id="SG-robot12", name="SG-robot12")
  sap54 = test.add_sap(name="SAP54", id="SAP54")
  balancer1 = test.add_nf(id="balance_server1", name="balance_server1",
                          func_type="balance_server", cpu=1, mem=1,
                          storage=0)
  balancer2 = test.add_nf(id="balance_server2", name="balance_server2",
                          func_type="balance_server", cpu=1, mem=1,
                          storage=0)
  splitter1 = test.add_nf(id="splitter1", name="splitter1",
                          func_type="splitter",
                          cpu=1, mem=1, storage=0)
  balancer3 = test.add_nf(id="balance_server3", name="balance_server3",
                          func_type="balance_server", cpu=1, mem=1,
                          storage=0)
  balancer4 = test.add_nf(id="balance_server4", name="balance_server4",
                          func_type="balance_server", cpu=1, mem=1,
                          storage=0)
  splitter2 = test.add_nf(id="splitter2", name="splitter2",
                          func_type="splitter",
                          cpu=1, mem=1, storage=0)

  test.add_sglink(sap54.add_port(1), splitter1.add_port(1), id=11,
                  flowclass='dl_src=bc:ee:7b:e6:8c:07')
  test.add_sglink(splitter1.add_port(2), balancer1.add_port(1), id=12)
  test.add_sglink(splitter1.add_port(3), balancer2.add_port(1), id=13)
  test.add_sglink(balancer1.ports[1], sap54.ports[1], id=14)
  test.add_sglink(balancer2.ports[1], sap54.ports[1], id=15)

  test.add_sglink(sap54.ports[1], splitter2.add_port(1), id=21,
                  flowclass='dl_src=9c:5c:8e:af:2e:e0')
  test.add_sglink(splitter2.add_port(2), balancer3.add_port(1), id=22)
  test.add_sglink(splitter2.add_port(3), balancer4.add_port(1), id=23)
  test.add_sglink(balancer3.ports[1], sap54.ports[1], id=24)
  test.add_sglink(balancer4.ports[1], sap54.ports[1], id=25)

  test.add_req(sap54.ports[1], sap54.ports[1], bandwidth=1, delay=50,
               sg_path=(11, 12, 14))
  return test


def generate_mn_topo_etsi ():
  # Create NFFG
  nffg = NFFG(id="INTERNAL", name="Internal-Mininet-Topology-ETSI")
  # Add environments
  ee11 = nffg.add_infra(id="EE11", name="ee-infra-11", domain=DOMAIN_INTERNAL,
                        infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                        delay=0.9, bandwidth=5000)
  ee12 = nffg.add_infra(id="EE12", name="ee-infra-12", domain=DOMAIN_INTERNAL,
                        infra_type=NFFG.TYPE_INFRA_EE, cpu=2, mem=2, storage=2,
                        delay=0.9, bandwidth=5000)
  ee21 = nffg.add_infra(id="EE21", name="ee-infra-21", domain=DOMAIN_INTERNAL,
                        infra_type=NFFG.TYPE_INFRA_EE, cpu=5, mem=5, storage=5,
                        delay=0.9, bandwidth=5000)
  ee22 = nffg.add_infra(id="EE22", name="ee-infra-22", domain=DOMAIN_INTERNAL,
                        infra_type=NFFG.TYPE_INFRA_EE, cpu=2, mem=2, storage=2,
                        delay=0.9, bandwidth=5000)
  # Add supported types
  ee11.add_supported_type(
    ('headerDecompressor', 'simpleForwarder'))
  ee12.add_supported_type(
    ('headerDecompressor', 'simpleForwarder'))
  ee21.add_supported_type(
    ('headerCompressor', 'simpleForwarder'))
  ee22.add_supported_type(
    ('headerCompressor', 'simpleForwarder'))
  # Add OVS switches
  sw1 = nffg.add_infra(id="SW1", name="switch-1", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.2,
                       bandwidth=10000)
  sw2 = nffg.add_infra(id="SW2", name="switch-2", domain=DOMAIN_INTERNAL,
                       infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.2,
                       bandwidth=10000)
  gw = nffg.add_infra(id="GW", name="gateway", domain=DOMAIN_INTERNAL,
                      infra_type=NFFG.TYPE_INFRA_SDN_SW, delay=0.1,
                      bandwidth=10000)
  # Add SAPs
  sap1 = nffg.add_sap(id="SAP1", name="SAP1")
  sap2 = nffg.add_sap(id="SAP2", name="SAP2")
  sap14 = nffg.add_sap(id="SAP14", name="SAP14")
  sap14.domain = "eth0"
  # Add links
  link_res = {'delay': 1.5, 'bandwidth': 10}
  nffg.add_link(sw1.add_port(1), sap1.add_port(1), id="mn-link-sw1-sap1",
                **link_res)
  nffg.add_link(sw1.add_port(2), ee11.add_port(1), id="mn-link-sw1-ee11",
                **link_res)
  nffg.add_link(sw1.add_port(3), ee12.add_port(1), id="mn-link-sw1-ee12",
                **link_res)
  nffg.add_link(sw2.add_port(1), sap2.add_port(1), id="mn-link-sw2-sap2",
                **link_res)
  nffg.add_link(sw2.add_port(2), ee21.add_port(1), id="mn-link-sw2-ee21",
                **link_res)
  nffg.add_link(sw2.add_port(3), ee22.add_port(1), id="mn-link-sw2-ee22",
                **link_res)
  nffg.add_link(sw1.add_port(4), sw2.add_port(4), id="mn-link-sw1-sw2",
                **link_res)
  nffg.add_link(sw2.add_port(5), gw.add_port(1), id="mn-link-sw2-gw",
                **link_res)
  nffg.add_link(gw.add_port(2), sap14.add_port(1), id="mn-link-gw-sap14",
                **link_res)
  # nffg.duplicate_static_links()
  return nffg


def generate_ietf_req ():
  nffg = NFFG(id="SG-etsi-req", name="SG-etsi-req")
  sap84 = nffg.add_sap(id="SAP84", name="SAP84")
  sap85 = nffg.add_sap(id="SAP85", name="SAP85")
  l2fwd = nffg.add_nf(id="L2fwdVhost", name="L2fwdVhost",
                      func_type="L2fwdVhost", cpu=2, mem=4, storage=0)
  l2fwd.add_metadata(name="bw_req", value=0)
  l2fwd.add_metadata(name="delay_req", value=100)
  l2fwd2 = nffg.add_nf(id="L2fwdVhost2", name="L2fwdVhost2",
                       func_type="L2fwdVhost2", cpu=2, mem=4, storage=0)
  l2fwd2.add_metadata(name="bw_req", value=0)
  l2fwd2.add_metadata(name="delay_req", value=100)
  nfpa = nffg.add_nf(id="NfpaVhost", name="NfpaVhost", func_type="NfpaVhost",
                     cpu=2, mem=4, storage=0)
  nfpa.add_metadata(name="bw_req", value=0)
  nfpa.add_metadata(name="delay_req", value=100)
  nfpa2 = nffg.add_nf(id="NfpaVhost2", name="NfpaVhost2",
                      func_type="NfpaVhost2",
                      cpu=2, mem=4, storage=0)
  nfpa2.add_metadata(name="bw_req", value=0)
  nfpa2.add_metadata(name="delay_req", value=100)
  # l2fdw
  nffg.add_sglink(src_port=sap84.add_port(2), dst_port=l2fwd.add_port(1),
                  id=11, flowclass="eth_type=2048,ip_proto=17,udp_dst=8900")
  nffg.add_sglink(src_port=l2fwd.ports[1], dst_port=sap84.ports[2],
                  id=12)
  # l2fdw2
  nffg.add_sglink(src_port=sap84.add_port(2), dst_port=l2fwd2.add_port(2),
                  id=17, flowclass="eth_type=2048,ip_proto=17,udp_dst=8901")
  nffg.add_sglink(src_port=l2fwd2.ports[2], dst_port=sap84.ports[2],
                  id=18)
  # nfpa
  nffg.add_sglink(src_port=sap85.add_port(2), dst_port=nfpa.add_port(1),
                  id=13, flowclass="eth_type=2048,ip_proto=17,udp_dst=8900")
  nffg.add_sglink(src_port=nfpa.ports[1], dst_port=sap85.ports[2],
                  id=14)
  # nfpa2
  nffg.add_sglink(src_port=sap85.ports[2], dst_port=nfpa2.add_port(2),
                  id=15, flowclass="eth_type=2048,ip_proto=17,udp_dst=8901")
  nffg.add_sglink(src_port=nfpa2.ports[2], dst_port=sap85.ports[2],
                  id=16)
  return nffg


if __name__ == "__main__":
  # test_parse_load()
  # test_NFFG()
  # nffg = generate_mn_topo()
  # nffg = generate_mn_test_req()
  # nffg = generate_dynamic_fallback_nffg()
  # nffg = generate_static_fallback_topo()
  # nffg = generate_one_bisbis()
  # nffg = gen()
  # nffg = generate_sdn_topo2()
  # nffg = generate_sdn_req()
  # nffg = generate_os_req()
  # nffg = generate_os_mn_req()
  # nffg = generate_dov()
  # nffg = generate_global_req()
  # nffg = generate_ewsdn_req2()
  # nffg = generate_simple_test_topo()
  # nffg = generate_simple_test_req()
  # nffg = generate_mn_topo2()
  # nffg = generate_mn_test_req2()
  # nffg = generate_mn_req_hackathon()
  # nffg = generate_hwloc2nffg_test_req()
  # nffg = generate_5gex_req1()
  # nffg = generate_etsi_req1b()
  # nffg = generate_etsi_req4b2b_robot1()
  # nffg = generate_etsi_req_robot1_simple()
  # nffg = generate_mn_topo_etsi()
  # nffg = generate_req_verification()
  nffg = generate_ietf_req()

  # pprint(nffg.network.__dict__)
  # nffg.merge_duplicated_links()
  # pprint(nffg.network.__dict__)
  print nffg.dump()
  # print generate_merged_mapped()
