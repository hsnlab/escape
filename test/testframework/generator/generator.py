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
