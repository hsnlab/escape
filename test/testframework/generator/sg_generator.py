#!/usr/bin/python -u
# Copyright 2017 Balazs Nemeth
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Generates requests that which can be used as standard test SG-s to cover 
most/all functionalities of ESCAPE.
"""
import random
import string

# noinspection PyUnresolvedReferences
from nffg_lib.nffg import NFFG


class NameGenerator(object):
  def __init__ (self):
    self.prefixes = {}

  def _get_gen_for_name (self, prefix):
    number = 0
    while True:
      yield prefix + str(number)
      number += 1

  def get_name (self, prefix):
    if prefix in self.prefixes:
      return self.prefixes[prefix].next()
    else:
      self.prefixes[prefix] = self._get_gen_for_name(prefix)
      return self.prefixes[prefix].next()

  def reset_name (self, prefix):
    if prefix in self.prefixes:
      del self.prefixes[prefix]


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
  for i in xrange(0, 20):
    saps.append("sap" + str(i))
  rnd = random.Random()
  rnd.seed(seed)
  gen = NameGenerator()
  nffg = NFFG(id="8loops-req")
  nffg.mode = NFFG.MODE_ADD
  nf_types = list(string.ascii_uppercase)[:abc_nf_types_len]
  i = 1
  for j in xrange(0, eightloops):
    sap = rnd.choice(saps)
    if sap not in nffg:
      sapo = nffg.add_sap(id=sap, name=sap + "_name")
    else:
      sapo = nffg.network.node[sap]
    if len(sapo.ports) > 0:
      for sapp in sapo.ports:
        break
    else:
      sapp = sapo.add_port(id=gen.get_name("port"))
    vnfs1 = rnd.sample(nf_types, rnd.randint(1, len(nf_types)))
    vnfs2 = rnd.sample(nf_types, rnd.randint(1, len(nf_types)))
    nfmiddle = nffg.add_nf(id="nf0" + str(j), name="nf_middle" + str(j),
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
        nf1 = nffg.add_nf(id="-".join(("nf", str(j), str(i))),
                          name="nf" + str(i) + "_" + vnf, func_type=vnf,
                          cpu=1, mem=1, storage=1)
        nffg.add_sglink(src_port=nf0.add_port(id=gen.get_name("port")),
                        dst_port=nf1.add_port(id=gen.get_name("port")),
                        flowclass="HTTP", id=i)
        nf0 = nf1
        i += 1
      if once:
        nffg.add_sglink(src_port=nf0.add_port(id=gen.get_name("port")),
                        dst_port=nfmiddle.add_port(id=gen.get_name("port")),
                        flowclass="HTTP", id=i)
        once = False
      i += 1
    nffg.add_sglink(src_port=nf1.add_port(id=gen.get_name("port")),
                    dst_port=sapp,
                    flowclass="HTTP", id=i)
    nffg.add_sglink(src_port=sapp,
                    dst_port=nfmiddle.add_port(id=gen.get_name("port")),
                    flowclass="HTTP", id=i + 1)
    i += 2
  return nffg


def get_balanced_tree (r=2, h=3, seed=0, max_cpu=4, max_mem=1600,
                       max_storage=3, max_link_bw=5, min_link_delay=2,
                       abc_nf_types_len=10, max_link_delay=4):
  """
  Gets a balanced tree which has SAPs in the root and the leaves, directed
  from the root to the leaves.

  :param r: branching factor of the tree
  :param h: height of the tree
  :return: NFFG
  """
  nf_types = list(string.ascii_uppercase)[:abc_nf_types_len]
  nffg = NFFG(id="req-tree-branching-" + str(r) + "-height-" + str(h))
  nffg.mode = NFFG.MODE_ADD

  rnd = random.Random()
  rnd.seed(seed)
  gen = NameGenerator()
  sap_obj = nffg.add_sap(id=gen.get_name("sap"))

  prev_level_nf_ports = [sap_obj.add_port(id=gen.get_name("port"))]
  for level in xrange(0, h):
    curr_level_nf_ports = []
    for prev_level_port in prev_level_nf_ports:
      for j in xrange(0, r):
        nf = nffg.add_nf(id=gen.get_name("nf"), func_type=rnd.choice(nf_types),
                         cpu=rnd.random() * max_cpu,
                         mem=rnd.random() * max_mem,
                         storage=rnd.random() * max_storage)
        nffg.add_sglink(prev_level_port, nf.add_port(gen.get_name("port")),
                        id=gen.get_name("sghop"))
        curr_level_nf_ports.append(nf.add_port(gen.get_name("port")))
    prev_level_nf_ports = curr_level_nf_ports

  for port in prev_level_nf_ports:
    sap = nffg.add_sap(id=gen.get_name("sap"))
    nffg.add_sglink(port, sap.add_port(id=gen.get_name("port")),
                    id=gen.get_name("delay_sghop"),
                    delay=rnd.uniform(min_link_delay, max_link_delay),
                    bandwidth=rnd.random() * max_link_bw)

  return nffg


if __name__ == '__main__':
  # nffg = get_8loop_request(eightloops=3)
  nffg = get_balanced_tree(r=2, h=2)
  print nffg.dump()
