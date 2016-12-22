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
from functools import partial

import e2e_reqs_for_testframework
import networkx_nffg_generator
import sg_generator

DEFAULT_SEED = 0

eight_loop_requests = partial(sg_generator.get_8loop_request,
                              abc_nf_types_len=10,
                              seed=DEFAULT_SEED,
                              eightloops=1)

complex_e2e_reqs = partial(e2e_reqs_for_testframework.main,
                           loops=False,
                           vnf_sharing=0.0,
                           seed=DEFAULT_SEED,
                           multiple_scs=False,
                           use_saps_once=False,
                           max_sc_count=2,
                           chain_maxlen=8,
                           max_cpu=4,
                           max_mem=1600,
                           max_storage=3,
                           max_bw=7,
                           max_e2e_lat_multiplier=20,
                           min_e2e_lat_multiplier=1.1)

networkx_resource_generator = partial(networkx_nffg_generator
                                      .networkx_resource_generator,
                                      seed=DEFAULT_SEED,
                                      max_cpu=40, max_mem=16000,
                                      max_storage=30, max_link_bw=70,
                                      abc_nf_types_len=10,
                                      supported_nf_cnt=6, max_link_delay=1,
                                      sap_cnt=10)

balanced_tree_request = partial(sg_generator.get_balanced_tree, r=2, h=3,
                                seed=DEFAULT_SEED,
                                max_cpu=4, max_mem=1600,
                                max_storage=3,
                                max_link_bw=5,
                                min_link_delay=2,
                                abc_nf_types_len=10,
                                max_link_delay=4)

def networkx_request_generator (gen_func, seed=0, **kwargs):
  """
  Chooses a built-in NetworkX topology generator which creates 
  request graph NFFG.
  """
  return networkx_nffg_generator.networkx_request_generator(gen_func, seed=0,
                                                            **kwargs)
