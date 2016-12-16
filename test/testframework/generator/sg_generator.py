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
import networkx as nx

def getGenForName(prefix):
   number = 0
   while True:
     yield prefix+str(number)
     number += 1
 
prefixes = {}
def getName(prefix):
  # WARNING! this function is not thread safe!!
  global prefixes
  while True:
    if prefix in prefixes:
      return prefixes[prefix].next()
    else:
      prefixes[prefix] = getGenForName(prefix)
      return prefixes[prefix].next()

def get_8loop_request (abc_nf_types_len=10, seed=0, eightloops=1):
  """
  Generates simple request NFFGs in all combinations of sap1-->vnf1-->...-->
  vnfn-->sap1. Creates the requests for augmented-dfn-gwin.nffg
  
  :param abc_nf_types_len: list of VNF **Types** which should be instantiated
  :type abc_nf_types_len: list
  :param seed: seed for random generator
  :type seed: int
  :param eightloops: the number of eight loops
  :type eightloops: int
  :return: an 8loop NFFG
  :rtype: :any:`NFFG`
  """
  saps = []
  for i in xrange(0,20):
    saps.append("sap"+str(i))
  rnd = random.Random()
  rnd.seed(seed)
  nffg = NFFG(id="8loops-req")
  nffg.mode = NFFG.MODE_ADD
  nf_types = list(string.ascii_uppercase)[:abc_nf_types_len]
  i = 1
  for j in xrange(0,eightloops):
    sap = rnd.choice(saps)
    if sap not in nffg:
      sapo = nffg.add_sap(id=sap, name=sap+"_name")
    else:
      sapo = nffg.network.node[sap]
    sapp = sapo.add_port(id = getName("port"))
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
    once = True
    for vnf_list in (vnfs1, vnfs2):
      nf0 = nfmiddle
      for vnf in vnf_list:
        nf1 = nffg.add_nf(id="-".join(("nf",str(j),str(i))), 
                          name="nf"+str(i)+"_"+vnf, func_type=vnf, 
                          cpu=1, mem=1, storage=1)
        nffg.add_sglink(src_port=nf0.add_port(id=getName("port")), 
                        dst_port=nf1.add_port(id=getName("port")), 
                        flowclass="HTTP", id=i)
        nf0 = nf1
        i+=1
      if once:
        nffg.add_sglink(src_port=nf0.add_port(id=getName("port")), 
                        dst_port=nfmiddle.add_port(id=getName("port")), 
                        flowclass="HTTP", id=i)
        once = False
      i+=1 
    nffg.add_sglink(src_port=nf1.add_port(id = getName("port")), dst_port=sapp, 
                    flowclass="HTTP", id=i)
    nffg.add_sglink(src_port=sapp, dst_port=nfmiddle.add_port(id = getName("port")), 
                    flowclass="HTTP", id=i+1)
    i+=2
  return nffg


if __name__ == '__main__':
  nffg = get_8loop_request(eightloops=3)
  print nffg.dump()
