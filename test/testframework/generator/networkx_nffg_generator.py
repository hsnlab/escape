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


import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             "../../../escape/escape/nffg_lib/")))
from nffg import NFFG

import importlib
import networkx as nx
import string
import random


def get_networkx_func (func_name, seed=0, **kwargs):
  """
  Uses 'func_name' graph generator of NetworkX library to create a NetworkX 
  graph which can be used as topology.
  """
  nx_func = getattr(importlib.import_module(nx), func_name)
  generated_graph = nx_func(seed=seed, **kwargs)
  return generated_graph


def networkx_request_generator (func_name, seed=0, max_cpu=4, max_mem=1600,
                                max_storage=3, max_bw=7, abc_nf_types_len=10,
                                **kwargs):
  """
  Uses a NetworkX graph to create a request NFFG.
  """
  rnd = random.Random()
  rnd.seed(seed)
  nx_graph = get_networkx_func(func_name, seed=seed, **kwargs)

  nf_types = list(string.ascii_uppercase)[:abc_nf_types_len]

  nffg = NFFG(id="req-" + func_name + "-seed" + str(seed))
  nffg.mode = NFFG.MODE_ADD
  for nf_id in nx_graph.nodes_iter():
    nf = nffg.add_nf(id=nf_id,
                     func_type=rnd.choice(nf_types),
                     cpu=rnd.random() * max_cpu,
                     mem=rnd.random() * max_mem,
                     storage=rnd.random() * max_storage)

  for i, j, k in nx_graph.edges_iter(keys=True):
    pass

  return nffg
