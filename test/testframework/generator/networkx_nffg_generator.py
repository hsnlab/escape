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


import importlib
import os
import random
import string
import sys

from sg_generator import getName

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             "../../../escape/escape/nffg_lib/")))
from nffg import NFFG


def get_networkx_func (func_name, seed=0, **kwargs):
  """
  Uses 'func_name' graph generator of NetworkX library to create a NetworkX 
  graph which can be used as topology.
  """
  nx_func = getattr(importlib.import_module("networkx"), func_name)
  generated_graph = nx_func(seed=seed, **kwargs)
  return generated_graph


def networkx_resource_generator (func_name, seed=0, max_cpu=4, max_mem=1600,
                                 max_storage=3, max_link_bw=7,
                                 abc_nf_types_len=10,
                                 supported_nf_cnt=6, max_link_delay=2,
                                 sap_cnt=10,
                                 **kwargs):
  """
  Uses a NetworkX graph to create a request NFFG.

  :param func_name: string of NetworkX lib's random graph generator function
  name
  :param seed:
  :param max_cpu:
  :param max_mem:
  :param max_storage:
  :param max_link_bw:
  :param abc_nf_types_len:
  :param supported_nf_cnt:
  :param max_link_delay:
  :param sap_cnt:
  :param kwargs:
  :return:
  """
  rnd = random.Random()
  rnd.seed(seed)
  nx_graph = get_networkx_func(func_name, seed=seed, **kwargs)

  nf_types = list(string.ascii_uppercase)[:abc_nf_types_len]
  nffg = NFFG(id="req-" + func_name + "-seed" + str(seed))
  nffg.mode = NFFG.MODE_ADD

  for infra_id in nx_graph.nodes_iter():
    infra = nffg.add_infra(id=infra_id,
                           bandwidth=rnd.random() * max_link_bw * 1000,
                           cpu=rnd.random() * max_cpu,
                           mem=rnd.random() * max_mem,
                           storage=rnd.random() * max_storage)
    infra.add_supported_type(rnd.sample(nf_types, supported_nf_cnt))

  for i, j in nx_graph.edges_iter():
    infra1 = nffg.network.node[i]
    infra2 = nffg.network.node[j]
    nffg.add_undirected_link(port1=infra1.add_port(id=getName("port")),
                             port2=infra2.add_port(id=getName("port")),
                             p1p2id=getName("link"), p2p1id=getName("link"),
                             dynamic=False,
                             delay=rnd.random() * max_link_delay,
                             bandwidth=rnd.random() * max_link_bw)

  infra_ids = [i.id for i in nffg.infras]
  for s in xrange(0, sap_cnt):
    sap_obj = nffg.add_sap(id=getName("sap"))
    sap_port = sap_obj.add_port(id=getName("port"))
    infra_id = rnd.choice(infra_ids)
    infra = nffg.network.node[infra_id]
    nffg.add_undirected_link(port1=sap_port,
                             port2=infra.add_port(id=getName("port")),
                             p1p2id=getName("link"), p2p1id=getName("link"),
                             dynamic=False,
                             delay=rnd.random() * max_link_delay,
                             bandwidth=rnd.random() * max_link_bw)

  return nffg

if __name__ == "__main__":
  print networkx_resource_generator("erdos_renyi_graph", seed=5, n=6, p=0.3, sap_cnt=15).dump()

