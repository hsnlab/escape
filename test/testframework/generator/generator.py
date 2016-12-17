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
import networkx_nffg_generator as nrg
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
                           max_e2e_lat_multiplier=20)


def networkx_request_generator (gen_func, seed=0, **kwargs):
  """
  Chooses a built-in NetworkX topology generator which creates 
  request graph NFFG.
  """
  return nrg.networkx_request_generator(gen_func, seed=0, **kwargs)
