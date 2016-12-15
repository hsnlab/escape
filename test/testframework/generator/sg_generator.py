#!/usr/bin/python -u
#
# Copyright (c) 2016 Balazs Nemeth
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
Generates requests that which can be used as standard test SG-s to cover 
most/all functionalities of ESCAPE.
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                "../../../escape/escape/nffg_lib/")))
from nffg import NFFG, NFFGToolBox
import random
import string
import NetworkX as nx

def get_8loop_request (gml_path, abc_nf_types_len=5, seed=0, eightloops=1):
  """
  Generates simple request NFFGs in all combinations of sap1-->vnf1-->...-->
  vnfn-->sap1. 

  :param saps: list of sap ID-s from the network
  :type saps: list
  :param nf_types: list of VNF **Types** which should be instantiated
  :type nf_types: list
  :param seed: seed for random generator
  :type seed: int
  :param eightloops: the number of eight loops
  :type eightloops: int
  :return: an 8loop NFFG
  :rtype: :any:`NFFG`
  """
  gml_graph = nx.read_gml(gml_path)
  saps = []
  # TODO: solve SAP name convention!
  rnd = random.Random()
  rnd.seed(seed)
  nffg = NFFG(id=gml_path+"req")
  nf_types = list(string.ascii_uppercase)[:abc_nf_types_len]
  for j in xrange(0,eightloops):
    sap = saps[j%len(saps)]
    if sap not in nffg:
      sapo = nffg.add_sap(id=sap, name=sap+"_name")
    else:
      sapo = nffg.network.node[sap]
    sapp = sapo.add_port()
    vnfs1 = rnd.sample(nf_types, rnd.randint(1,len(nf_types)))
    vnfs2 = rnd.sample(nf_types, rnd.randint(1,len(nf_types)))
    nfmiddle = nffg.add_nf(id="nf0"+str(j), name="nf_middle"+str(j), 
                           func_type=rnd.choice(vnfs1), 
                           cpu=1, mem=1, storage=1)
    try:
      vnfs1.remove(nfmiddle.functional_type)
    except ValueError:
      pass
    try:
      vnfs2.remove(nfmiddle.functional_type)
    except ValueError:
      pass
    i = 1
    once = True
    for vnf_list in (vnfs1, vnfs2):
      nf0 = nfmiddle
      for vnf in vnf_list:
        nf1 = nffg.add_nf(id="-".join("nf",str(j),str(i)), 
                          name="nf"+str(i)+"_"+vnf, func_type=vnf, 
                          cpu=1, mem=1, storage=1)
        nffg.add_sglink(src_port=nf0.add_port(), dst_port=nf1.add_port(), 
                        flowclass="HTTP", id=i)
        nf0 = nf1
        i+=1
      if once:
        nffg.add_sglink(src_port=nf0.add_port(), dst_port=nfmiddle.add_port(), 
                        flowclass="HTTP", id=i)
        once = False
      i+=1 
    nffg.add_sglink(src_port=nf1.add_port(), dst_port=sapp, 
                    flowclass="HTTP", id=i)
    nffg.add_sglink(src_port=sapp, dst_port=nfmiddle.add_port(), 
                    flowclass="HTTP", id=i+1)
  return nffg

def gen_simple_oneloop_tests (saps, vnfs):
  """
  Generates simple request NFFGs in all combinations of sap1-->vnf1-->sap1.
  With a loop requirement

  :param saps: list of sap ID-s from the network
  :type saps: list
  :param vnfs: list of VNF **Types** which should be instantiated
  :type vnfs: list
  :return: a generator over :any:`NFFG`
  :rtype: generator
  """
  for sap in saps:
    for vnf in vnfs:
      nffg = NFFG()
      sapo = nffg.add_sap(id=sap, name=sap+"_name")
      nfo = nffg.add_nf(id="nf", name="nf_"+vnf, func_type=vnf,
                        cpu=1, mem=1, storage=1)
      sapp = sapo.add_port()
      nffg.add_sglink(src_port=sapp, dst_port=nfo.add_port(), 
                      flowclass="HTTP", id=1)
      nffg.add_sglink(src_port=nfo.add_port(), dst_port=sapp, 
                      flowclass="HTTP", id=2)

      nffg.add_req(src_port=sapp, dst_port=sapp, delay=50, bandwidth=1, 
                   sg_path=[1,2])
      yield nffg

