# Copyright 2015 Felician Nemeth <nemethf@tmit.bme.hu>
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
Extends the Service Graph with a management network.

This module shows a example to handle the PreMapEvent.  It searches
the Service Graph for an unconnected SAP, then connects this SAP with
every VNF.  The management port of the VNFs are from the 10.0.10.0/8
domain.  The first interface of SAP should have an address of
10.0.10.1/8.  The number of VNFs must be smaller than 255.

Start this module as:

$ ./escape.py -d -f escape.service.mgmt_net

Unfortunately, seeing the following warnings are expected:
[core                   ] ManagementNetwork still waiting for: service
[core                   ] Still waiting on 1 component(s)
"""
from pox.core import core

log = core.getLogger()

class ManagementNetwork (object):
  def __init__ (self):
    core.listen_to_dependencies(self)
    self.small_uniq_num = 1000
    self.ip = 1

  def uniq_num (self):
    ## There's a bug in the infrastructure layer that uses id as port
    ## numbers, vlan tags, etc in flow_mod messages.  And the
    ## auto-generated id might be too large for these port_ids, etc.
    ## So, we use here predefined "small" ids.
    self.small_uniq_num += 1
    return self.small_uniq_num

  def uniq_ip (self):
    self.ip += 1
    return '10.0.10.%d/24' % self.ip

  def _get_mgmt_sap (self, sg):

    mgmt_sap = None
    seen = {}
    saps = [sap.id for sap in sg.saps] # node ids
    for hop in sg.sg_hops:
      for id in [hop.src.node.id, hop.dst.node.id]:
        if id in saps:
          seen[id] = 1
          break
    for sap in sg.saps:
      if sap.id not in seen:
        log.info("mgmt_sap: %s" % sap.id)
        return sap
    
    log.warn("Found no candidate for mgmt_sap")
    return None

  def _handle_service_PreMapEvent (self, event):
    sg = event.sg

    mgmt_sap = self._get_mgmt_sap(sg)
    if mgmt_sap is None:
      return

    src_port = mgmt_sap.ports[1]
    for nf in sg.nfs:
      dst_port = nf.add_port(self.uniq_num())
      dst_port.add_property('ip', self.uniq_ip())
      link_forw = sg.add_sglink(src_port, dst_port, id=self.uniq_num())
      link_back = sg.add_sglink(dst_port, src_port, id=self.uniq_num())
      self.small_uniq_num += 1
      sg.add_req(src_port, src_port, id=self.uniq_num(),
                 bandwidth=0, delay=10000000,
                 sg_path=(link_forw.id, link_back.id))


def launch ():
  core.registerNew(ManagementNetwork)
