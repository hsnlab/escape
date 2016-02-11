# Copyright 2015 Janos Czentye <czentye@tmit.bme.hu>
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
Contains Manager classes which contains the higher-level logic for complete
domain management. Uses Adapter classes for ensuring protocol-specific
connections with entities in the particular domain.
"""
import sys
import traceback

from ncclient.operations import RPCError

from escape.util.conversion import NFFGConverter
from escape.util.domain import *
from pox.lib.util import dpid_to_str


class InternalDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with internally emulated network.

  .. note::
    Uses :class:`InternalMininetAdapter` for managing the emulated network and
    :class:`InternalPOXAdapter` for controlling the network.
  """
  # DomainManager name
  name = "INTERNAL"
  # Default domain name
  DEFAULT_DOMAIN_NAME = "INTERNAL"
  # Set the local manager status
  IS_LOCAL_MANAGER = True

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, *args, **kwargs):
    """
    Init
    """
    super(InternalDomainManager, self).__init__(domain_name=domain_name,
                                                *args, **kwargs)
    log.debug(
      "Init InternalDomainManager with domain name: %s" % self.domain_name)
    self.controlAdapter = None  # DomainAdapter for POX-InternalPOXAdapter
    self.topoAdapter = None  # DomainAdapter for Mininet-InternalMininetAdapter
    self.remoteAdapter = None  # NETCONF communication - VNFStarterAdapter
    self.portmap = {}  # Map (unique) dynamic ports to physical ports in EEs
    self.deployed_vnfs = {}  # container for replied NETCONF messages of
    # deployNF, key: (infra_id, nf_id), value: initiated_vnf part of the
    # parsed reply in JSON
    self.sapinfos = {}

  def init (self, configurator, **kwargs):
    """
    Initialize Internal domain manager.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :param kwargs: optional parameters
    :type kwargs: dict
    :return: None
    """
    # Call abstract init to execute common operations
    super(InternalDomainManager, self).init(configurator, **kwargs)
    self._collect_SAP_infos()
    self._setup_sap_hostnames()

  def initiate_adapters (self, configurator):
    """
    Initiate adapters.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :return: None
    """
    # Initiate Adapters
    self.topoAdapter = configurator.load_component(
      component_name=AbstractESCAPEAdapter.TYPE_TOPOLOGY,
      parent=self._adapters_cfg)
    # Init adapter for internal controller: POX
    self.controlAdapter = configurator.load_component(
      component_name=AbstractESCAPEAdapter.TYPE_CONTROLLER,
      parent=self._adapters_cfg)
    log.debug("Set %s as the topology Adapter for %s" % (
      self.topoAdapter.__class__.__name__,
      self.controlAdapter.__class__.__name__))
    # Init default NETCONF adapter
    self.remoteAdapter = configurator.load_component(
      component_name=AbstractESCAPEAdapter.TYPE_MANAGEMENT,
      parent=self._adapters_cfg)

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(InternalDomainManager, self).finit()
    del self.controlAdapter
    del self.remoteAdapter

  @property
  def controller_name (self):
    return self.controlAdapter.task_name

  def _setup_sap_hostnames (self):
    """
    Setup hostnames in /etc/hosts for SAPs.

    :return: None
    """
    # Update /etc/hosts with hostname - IP address mapping
    import os
    os.system("sed '/# BEGIN ESCAPE SAPS/,/# END ESCAPE SAPS/d' "
              "/etc/hosts > /etc/hosts2")
    os.system("mv /etc/hosts2 /etc/hosts")
    hosts = "# BEGIN ESCAPE SAPS \n"
    for sap, info in self.sapinfos.iteritems():
      hosts += "%s %s \n" % (info['nw_dst'], sap)
    hosts += "# END ESCAPE SAPS \n"
    with open('/etc/hosts', 'a') as f:
      f.write(hosts)
    log.debug("Setup SAP hostnames: %s" % "; ".join(
      ["%s --> %s" % (sap, info['nw_dst']) for sap, info in
       self.sapinfos.iteritems()]))

  def _collect_SAP_infos (self):
    """
    Collect necessary information from SAPs for traffic steering.

    :return: None
    """
    log.debug("Collect SAP info...")
    mn = self.topoAdapter.get_mn_wrapper().network
    topo = self.topoAdapter.get_topology_resource()
    if topo is None or mn is None:
      log.error(
        "Missing topology description from topology Adapter! Skip SAP data "
        "discovery.")
    for sap in topo.saps:
      # skip inter-domain SAPs
      if sap.domain is not None:
        continue
      connected_node = [(v, link.dst.id) for u, v, link in
                        topo.network.out_edges_iter(sap.id, data=True)]
      if len(connected_node) > 1:
        log.warning("%s is connection to multiple nodes (%s)!" % (
          sap, [n[0] for n in connected_node]))
      for node in connected_node:
        mac = mn.getNodeByName(sap.id).MAC()
        ip = mn.getNodeByName(sap.id).IP()
        log.debug(
          "Detected IP(%s) | MAC(%s) for %s connected to Node(%s) on port: "
          "%s" %
          (ip, mac, sap, node[0], node[1]))
        if node[0] not in self.controlAdapter.saps:
          self.controlAdapter.saps[node[0]] = {}
        sapinfo = {
          'dl_src': "ff:ff:ff:ff:ff:ff",
          'dl_dst': str(mac),
          'nw_dst': str(ip)
        }
        self.controlAdapter.saps[node[0]][str(node[1])] = sapinfo
        self.sapinfos[str(sap.id)] = sapinfo

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the internal domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    try:
      log.info(">>> Install %s domain part..." % self.domain_name)
      # print nffg_part.dump()
      # self._delete_nfs()
      self._deploy_nfs(nffg_part=nffg_part)
      log.info("Perform traffic steering according to mapped tunnels/labels...")
      self._delete_flowrules(nffg_part=nffg_part)

      # def _deploy_flowrules_forever (interval=3):
      #   from pox.lib.recoco import Timer
      #
      #   def _callback (counter={'cntr': 1}):
      #     self._delete_flowrules(nffg_part=nffg_part)
      #     self._deploy_flowrules(nffg_part=nffg_part)
      #     log.debug("Deploy flowrules counter: %s" % counter['cntr'])
      #     counter['cntr'] += 1
      #
      #   Timer(timeToWake=interval, callback=_callback, recurring=True,
      #         selfStoppable=False)

      self._deploy_flowrules(nffg_part=nffg_part)
      # _deploy_flowrules_forever()
      return True
    except:
      log.exception(
        "Got exception during NFFG installation into: %s." % self.domain_name)
      return False

  def clear_domain (self):
    """
    Infrastructure Layer has already been stopped and probably cleared.

    Skip cleanup process here.

    :return: None
    """
    if not self.topoAdapter.check_domain_reachable():
      # This would be the normal behaviour if ESCAPEv2 is shutting down -->
      # Infrastructure layer has been cleared.
      log.debug("%s domain has already been cleared!" % self.domain_name)
      return
    self._delete_nfs()
    self._delete_flowrules(nffg_part=self.topoAdapter.get_topology_resource())

  def _delete_nfs (self):
    """
    Stop and delete deployed NFs.

    :return: None
    """
    topo = self.topoAdapter.get_topology_resource()
    if topo is None:
      log.warning(
        "Missing topology description from %s domain! Skip deleting NFs..." %
        self.domain_name)
      return
    log.debug("Remove deployed NFs...")
    for infra in topo.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE):
        continue
      for nf in [n for n in topo.running_nfs(infra.id)]:
        # Create connection Adapter to EE agent
        connection_params = self.topoAdapter.get_agent_connection_params(
          infra.id)
        if connection_params is None:
          log.error(
            "Missing connection params for communication with the agent of "
            "Node: %s" % infra.short_name)
        updated = self.remoteAdapter.update_connection_params(
          **connection_params)
        try:
          vnf_id = self.deployed_vnfs[(infra.id, nf.id)]['vnf_id']
          reply = self.remoteAdapter.removeNF(vnf_id=vnf_id)
          print reply
          # Delete infra ports connected to the deletable NF
          for u, v, link in topo.network.out_edges([nf.id], data=True):
            topo[v].del_port(id=link.dst.id)
          # Delete NF
          topo.del_node(nf.id)
          log.debug("Removed NF: %s" % nf)
        except KeyError:
          log.error(
            "Deployed VNF data for NF: %s is not found! Skip deletion..." % nf)
        except RPCError:
          log.error(
            "Got RPC communication error during NF: %s initiation! Skip "
            "initiation..." % nf.name)
          continue
          # print self.topoAdapter.get_topology_resource().dump()
    log.debug("Deletion of deployed NFs has been ended!")

  def _deploy_nfs (self, nffg_part):
    """
    Install the NFs mapped in the given NFFG.

    If an NF is already defined in the topology and it's state is up and
    running then the actual NF's initiation will be skipped!

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    log.info("Deploy mapped NFs into the domain: %s..." % self.domain_name)
    self.portmap.clear()
    # Remove unnecessary SG and Requirement links to avoid mess up port
    # definition of NFs
    nffg_part.clear_links(NFFG.TYPE_LINK_SG)
    nffg_part.clear_links(NFFG.TYPE_LINK_REQUIREMENT)
    # Get physical topology description from Mininet
    mn_topo = self.topoAdapter.get_topology_resource()
    if mn_topo is None:
      log.warning(
        "Missing topology description from %s domain! Skip deploying NFs..." %
        self.domain_name)
      return
    # Iter through the container INFRAs in the given mapped NFFG part
    # print mn_topo.dump()
    for infra in nffg_part.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE):
        log.debug(
          "Infrastructure Node: %s (type: %s) is not Container type! Continue "
          "to next Node..." % (infra.short_name, infra.infra_type))
        continue
      else:
        log.debug("Check NFs mapped on Node: %s" % infra.short_name)
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in self.internal_topo.infras):
        log.error(
          "Infrastructure Node: %s is not found in the %s domain! Skip NF "
          "initiation on this Node..." % (infra.short_name, self.domain_name))
        continue
      # Iter over the NFs connected the actual INFRA
      for nf in nffg_part.running_nfs(infra.id):
        # NF with id is already deployed --> change the dynamic port to
        # static and continue
        if nf.id in (nf.id for nf in self.internal_topo.nfs):
          log.debug(
            "NF: %s has already been initiated. Continue to next NF..." %
            nf.short_name)
          for u, v, link in nffg_part.network.out_edges_iter([nf.id],
                                                             data=True):
            dyn_port = nffg_part[v].ports[link.dst.id]
            for x, y, l in mn_topo.network.out_edges_iter([nf.id],
                                                          data=True):
              if l.src.id == link.src.id:
                self.portmap[dyn_port.id] = l.dst.id
                dyn_port.id = l.dst.id
                break
          continue
        # Extract the initiation params
        params = {
          'nf_type': nf.functional_type,
          'nf_ports': [link.src.id for u, v, link in
                       nffg_part.network.out_edges_iter((nf.id,),
                                                        data=True)],
          'infra_id': infra.id
        }
        # Check if every param is not None or empty
        if not all(params.values()):
          log.error(
            "Missing arguments for initiation of NF: %s. Extracted params: "
            "%s" % (nf.short_name, params))
        # Create connection Adapter to EE agent
        connection_params = self.topoAdapter.get_agent_connection_params(
          infra.id)
        if connection_params is None:
          log.error(
            "Missing connection params for communication with the agent of "
            "Node: %s" % infra.short_name)
        # Save last used adapter --> and last RPC result
        log.debug("Initiating NF: %s with params: %s" % (nf.short_name, params))
        updated = self.remoteAdapter.update_connection_params(
          **connection_params)
        if updated:
          log.debug("Update connection params in %s: %s" % (
            self.remoteAdapter.__class__.__name__, updated))
        try:
          vnf = self.remoteAdapter.deployNF(**params)
          # from pprint import pprint
          # pprint(vnf)
        except RPCError:
          log.error(
            "Got RPC communication error during NF: %s initiation! Skip "
            "initiation..." % nf.name)
          continue
        # Check if NETCONF communication was OK
        if vnf is not None and vnf['initiated_vnfs']['pid'] and \
              vnf['initiated_vnfs'][
                'status'] == VNFStarterAPI.VNFStatus.s_UP_AND_RUNNING:
          log.info("NF: %s initiation has been verified on Node: %s" % (
            nf.short_name, infra.short_name))
          log.debug("Initiated VNF id: %s, PID: %s, status: %s" % (
            vnf['initiated_vnfs']['vnf_id'], vnf['initiated_vnfs']['pid'],
            vnf['initiated_vnfs']['status']))
        else:
          log.error(
            "Initiated NF: %s is not verified. Initiation was unsuccessful!"
            % nf.short_name)
          continue
        # Store NETCONF related info of deployed NF
        self.deployed_vnfs[(infra.id, nf.id)] = vnf['initiated_vnfs']
        # Add initiated NF to topo description
        log.info("Update Infrastructure layer topology description...")
        deployed_nf = nf.copy()
        deployed_nf.ports.clear()
        mn_topo.add_nf(nf=deployed_nf)

        log.debug("Add deployed NFs to topology...")
        # Add Link between actual NF and INFRA
        for nf_id, infra_id, link in nffg_part.network.out_edges_iter((nf.id,),
                                                                      data=True):
          # Get Link's src ref to new NF's port
          # nf_port = deployed_nf.ports[link.src.id]
          # Create new Port for new NF
          # print nf.__dict__
          # print link
          nf_port = deployed_nf.ports.append(nf.ports[link.src.id].copy())

          def get_sw_port (vnf):
            """
            Return the switch port parsed from result of getVNFInfo

            :param vnf: VNF description returned by NETCONF server
            :type vnf: dict
            :return: port id
            :rtype: int
            """
            if isinstance(vnf['initiated_vnfs']['link'], list):
              for _link in vnf['initiated_vnfs']['link']:
                if str(_link['vnf_port']) == str(nf_port.id):
                  return int(_link['sw_port'])
            else:
              return int(vnf['initiated_vnfs']['link']['sw_port'])

          # Get OVS-generated physical port number
          infra_port_num = get_sw_port(vnf)
          if infra_port_num is None:
            log.warning(
              "Can't get Container port from RPC result! Set generated port "
              "number...")
          # Create INFRA side Port
          infra_port = mn_topo.network.node[infra_id].add_port(
            id=infra_port_num)
          log.debug("%s - detected physical %s" % (deployed_nf, infra_port))
          # Add Links to mn topo
          l1, l2 = mn_topo.add_undirected_link(port1=nf_port, port2=infra_port,
                                               dynamic=True, delay=link.delay,
                                               bandwidth=link.bandwidth)
          # Port mapping
          dynamic_port = nffg_part.network.node[infra_id].ports[link.dst.id].id
          self.portmap[dynamic_port] = infra_port_num
          # Update port in nffg_part
          nffg_part.network.node[infra_id].ports[
            link.dst.id].id = infra_port_num

        log.debug("%s topology description is updated with NF: %s" % (
          self.domain_name, deployed_nf.name))

    log.debug("Rewrite dynamically generated port numbers in flowrules...")
    # Update port numbers in flowrules
    for infra in nffg_part.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
         NFFG.TYPE_INFRA_SDN_SW):
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in mn_topo.infras):
        continue
      for port in infra.ports:
        for flowrule in port.flowrules:
          _match = flowrule.match.split(';')
          if not _match[0].startswith("in_port="):
            log.warning(
              "Missing 'in_port' from match field: %s" % flowrule.match)
            continue
          _action = flowrule.action.split(';')
          if not _action[0].startswith("output="):
            log.warning(
              "Missing 'output' from action field: %s" % flowrule.action)
            continue
          for dyn, phy in self.portmap.iteritems():
            _match[0] = _match[0].replace(str(dyn), str(phy))
            _action[0] = _action[0].replace(str(dyn), str(phy))
          flowrule.match = ";".join(_match)
          flowrule.action = ";".join(_action)
    log.info(
      "Initiation of NFs in NFFG part: %s has been finished!" % nffg_part)

  def _delete_flowrules (self, nffg_part):
    """
    Delete all flowrules from the first (default) table of all infras.
    """
    log.debug("Reset domain steering and delete installed flowrules...")
    topo = self.topoAdapter.get_topology_resource()
    if topo is None:
      log.warning(
        "Missing topology description from %s domain! Skip flowrule "
        "deletions..." % self.domain_name)
      return
    # Iter through the container INFRAs in the given mapped NFFG part
    for infra in nffg_part.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
         NFFG.TYPE_INFRA_SDN_SW):
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in topo.infras):
        log.error("Infrastructure Node: %s is not found in the %s domain! Skip "
                  "flowrule delete on this Node..." % (
                    infra.short_name, self.domain_name))
        continue
      try:
        dpid = self.controlAdapter.infra_to_dpid[infra.id]
      except KeyError as e:
        log.warning(
          "Missing DPID for Infra(id: %s)! Skip deletion of flowrules" % e)
        continue
      # Check the OF connection is alive
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        log.warning(
          "Skipping DELETE flowrules! Cause: connection for %s - DPID: %s is "
          "not found!" % (infra, dpid_to_str(dpid)))
        continue
      self.controlAdapter.delete_flowrules(infra.id)

  def _deploy_flowrules (self, nffg_part):
    """
    Install the flowrules given in the NFFG.

    If a flowrule is already defined it will be updated.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    log.info("Deploy flowrules into the domain: %s..." % self.domain_name)
    # Remove unnecessary SG and Requirement links to avoid mess up port
    # definition of NFs
    nffg_part.clear_links(NFFG.TYPE_LINK_SG)
    nffg_part.clear_links(NFFG.TYPE_LINK_REQUIREMENT)

    # # Get physical topology description from POX adapter
    # topo = self.controlAdapter.get_topology_resource()
    topo = self.topoAdapter.get_topology_resource()
    if topo is None:
      log.warning(
        "Missing topology description from %s domain! Skip deploying "
        "flowrules..." % self.domain_name)
      return
    # Iter through the container INFRAs in the given mapped NFFG part
    for infra in nffg_part.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
         NFFG.TYPE_INFRA_SDN_SW):
        log.debug(
          "Infrastructure Node: %s (type: %s) is not Switch or Container "
          "type! "
          "Continue to next Node..." % (infra.short_name, infra.infra_type))
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in topo.infras):
        log.error("Infrastructure Node: %s is not found in the %s domain! Skip "
                  "flowrule install on this Node..." % (
                    infra.short_name, self.domain_name))
        continue
      try:
        dpid = self.controlAdapter.infra_to_dpid[infra.id]
      except KeyError as e:
        log.warning(
          "Missing DPID for Infra(id: %s)! Skip deploying flowrules for "
          "Infra" % e)
        continue
      # Check the OF connection is alive
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        log.warning(
          "Skipping INSTALL flowrule! Cause: connection for %s - DPID: %s is "
          "not found!" % (infra, dpid_to_str(dpid)))
        continue
      for port in infra.ports:
        for flowrule in port.flowrules:
          try:
            match = NFFGConverter.field_splitter(
              type=NFFGConverter.TYPE_MATCH,
              field=flowrule.match)
            if "in_port" not in match:
              log.warning(
                "Missing in_port field from match field! Using container "
                "port number...")
              match["in_port"] = port.id
            action = NFFGConverter.field_splitter(
              type=NFFGConverter.TYPE_ACTION,
              field=flowrule.action)
          except RuntimeError as e:
            log.warning("Wrong format in match/action field: %s" % e)
            continue

          log.debug("Assemble OpenFlow flowrule from: %s" % flowrule)
          self.controlAdapter.install_flowrule(infra.id, match, action)


class SDNDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with POX-controlled SDN domain.

  .. note::
    Uses :class:`InternalPOXAdapter` for controlling the network.
  """
  # Domain name
  name = "SDN"
  # Default domain name
  DEFAULT_DOMAIN_NAME = "SDN"

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, *args, **kwargs):
    """
    Init
    """
    super(SDNDomainManager, self).__init__(domain_name=domain_name, *args,
                                           **kwargs)
    log.debug("Init SDNDomainManager with domain name: %s" % self.domain_name)
    self.controlAdapter = None  # DomainAdapter for POX - InternalPOXAdapter
    self.topoAdapter = None  # SDN topology adapter - SDNDomainTopoAdapter

  def init (self, configurator, **kwargs):
    """
    Initialize SDN domain manager.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :param kwargs: optional parameters
    :type kwargs: dict
    :return: None
    """
    # Call abstract init to execute common operations
    super(SDNDomainManager, self).init(configurator, **kwargs)

  def initiate_adapters (self, configurator):
    """
    Init Adapters.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :return: None
    """
    # Initiate adapters
    self.controlAdapter = configurator.load_component(
      component_name=AbstractESCAPEAdapter.TYPE_CONTROLLER,
      parent=self._adapters_cfg)
    # Init adapter for static domain topology
    self.topoAdapter = configurator.load_component(
      component_name=AbstractESCAPEAdapter.TYPE_TOPOLOGY,
      parent=self._adapters_cfg)

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(SDNDomainManager, self).finit()
    del self.controlAdapter

  @property
  def controller_name (self):
    return self.controlAdapter.task_name

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the SDN domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    try:
      log.info("Install %s domain part..." % self.domain_name)
      # log.info("NFFG:\n%s" % nffg_part.dump())
      log.info("NFFG: %s" % nffg_part)
      self._delete_flowrules(nffg_part=nffg_part)
      #
      # def _deploy_flowrules_forever (interval=3):
      #   from pox.lib.recoco import Timer
      #
      #   def _callback (counter={'cntr': 1}):
      #     self._delete_flowrules(nffg_part=nffg_part)
      #     self._deploy_flowrules(nffg_part=nffg_part)
      #     log.debug("Deploy flowrules counter: %s" % counter['cntr'])
      #     counter['cntr'] += 1
      #
      #   Timer(timeToWake=interval, callback=_callback, recurring=True,
      #         selfStoppable=False)
      self._deploy_flowrules(nffg_part=nffg_part)
      # _deploy_flowrules_forever()
      return True
    except:
      log.exception(
        "Got exception during NFFG installation into: %s." % self.domain_name)
      return False

  def _delete_flowrules (self, nffg_part):
    """
    Delete all flowrules from the first (default) table of all infras.

    :return: None
    """
    log.debug("Removing flowrules...")
    # Iter through the container INFRAs in the given mapped NFFG part
    for infra in nffg_part.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
         NFFG.TYPE_INFRA_SDN_SW):
        continue
      # Check the OF connection is alive
      try:
        dpid = self.controlAdapter.infra_to_dpid[infra.id]
      except KeyError as e:
        log.warning(
          "Missing DPID for Infra(id: %s)! Skip deletion of flowrules" % e)
        continue
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        log.warning(
          "Skipping DELETE flowrules! Cause: connection for %s - DPID: %s is "
          "not found!" % (infra, dpid_to_str(dpid)))
        continue
      self.controlAdapter.delete_flowrules(infra.id)

  def _deploy_flowrules (self, nffg_part):
    """
    Install the flowrules given in the NFFG.

    If a flowrule is already defined it will be updated.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    # Remove unnecessary SG and Requirement links to avoid mess up port
    # definition of NFs
    nffg_part.clear_links(NFFG.TYPE_LINK_SG)
    nffg_part.clear_links(NFFG.TYPE_LINK_REQUIREMENT)
    # Get physical topology description from POX adapter
    topo = self.topoAdapter.get_topology_resource()
    if topo is None:
      log.warning(
        "Missing topology description from %s domain! Skip deploying "
        "flowrules..." % self.domain_name)
      return
    # Iter through the container INFRAs in the given mapped NFFG part
    for infra in nffg_part.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
         NFFG.TYPE_INFRA_SDN_SW):
        log.debug(
          "Infrastructure Node: %s (type: %s) is not Switch or Container type!"
          " Continue to next Node..." % (infra.short_name, infra.infra_type))
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in topo.infras):
        log.error("Infrastructure Node: %s is not found in the %s domain! Skip"
                  " flowrule install on this Node..." % (
                    infra.short_name, self.domain_name))
        continue
      # Check the OF connection is alive
      try:
        dpid = self.controlAdapter.infra_to_dpid[infra.id]
      except KeyError as e:
        log.warning(
          "Missing DPID for Infra(id: %s)! Skip deploying flowrules for "
          "Infra" % e)
        continue
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        log.warning(
          "Skipping INSTALL flowrule! Cause: connection for %s - DPID: %s is "
          "not found!" % (infra, dpid_to_str(dpid)))
        continue
      for port in infra.ports:
        for flowrule in port.flowrules:
          try:
            match = NFFGConverter.field_splitter(type="MATCH",
                                                 field=flowrule.match)
            if "in_port" not in match:
              log.warning(
                "Missing in_port field from match field! Using container "
                "port number...")
              match["in_port"] = port.id
            action = NFFGConverter.field_splitter(type="ACTION",
                                                  field=flowrule.action)
          except RuntimeError as e:
            log.warning("Wrong format in match/action field: %s" % e)
            continue
          log.debug("Assemble OpenFlow flowrule from: %s" % flowrule)
          self.controlAdapter.install_flowrule(infra.id, match=match,
                                               action=action)

  def clear_domain (self):
    """
    Delete all flowrule in the registered SDN/OF switches.

    :return: None
    """
    log.debug("Clear all flowrules from switches registered in SDN domain...")
    # Delete all flowrules in the Infra nodes defined the topology file.
    sdn_topo = self.topoAdapter.get_topology_resource()
    if sdn_topo is not None:
      self._delete_flowrules(nffg_part=sdn_topo)
    else:
      log.warning("SDN topology is missing! Skip domain resetting...")


class RemoteESCAPEDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with other ESCAPEv2 processes started
  in agent-mode through
  a REST-API which is provided by the Resource Orchestration Sublayer.

  .. note::
    Uses :class:`RemoteESCAPEv2RESTAdapter` for communicate with the remote
    domain.
  """
  # Domain name
  name = "REMOTE-ESCAPE"
  # Default domain name
  DEFAULT_DOMAIN_NAME = "REMOTE"

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, *args, **kwargs):
    """
    Init
    """
    super(RemoteESCAPEDomainManager, self).__init__(domain_name=domain_name,
                                                    *args, **kwargs)
    log.debug(
      "Init RemoteESCAPEDomainManager with domain name: %s" % self.domain_name)

  def init (self, configurator, **kwargs):
    """
    Initialize Internal domain manager.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :param kwargs: optional parameters
    :type kwargs: dict
    :return: None
    """
    # Call abstract init to execute common operations
    super(RemoteESCAPEDomainManager, self).init(configurator, **kwargs)

  def initiate_adapters (self, configurator):
    """
    Init Adapters.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :return: None
    """
    # Init adapter for remote ESCAPEv2 domain
    self.topoAdapter = configurator.load_component(
      component_name=AbstractESCAPEAdapter.TYPE_REMOTE,
      parent=self._adapters_cfg)

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(RemoteESCAPEDomainManager, self).finit()

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the internal domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    # nffg_part = self._update_nffg(nffg_part.copy())
    log.info("Install %s domain part..." % self.domain_name)
    try:
      status = self.topoAdapter.edit_config(nffg_part)
      if status is not None:
        return True
      else:
        return False
    except:
      log.exception(
        "Got exception during NFFG installation into: %s." % self.domain_name)
      return False

  # def __update_nffg (self, nffg_part):
  #   """
  #   Update domain descriptor of infras: REMOTE -> INTERNAL
  #
  #   :param nffg_part: NF-FG need to be updated
  #   :type nffg_part: :any:`NFFG`
  #   :return: updated NFFG
  #   :rtype: :any:`NFFG`
  #   """
  #   for infra in nffg_part.infras:
  #     if infra.infra_type not in (
  #          NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
  #          NFFG.TYPE_INFRA_SDN_SW):
  #       continue
  #     if infra.domain == 'REMOTE':
  #       infra.domain = 'INTERNAL'
  #   return nffg_part

  def clear_domain (self):
    """
    Reset remote domain based on the original (first response) topology.

    :return: None
    """
    empty_cfg = self.topoAdapter.get_original_topology()
    if empty_cfg is None:
      log.warning(
        "Missing original topology in %s domain! Skip domain resetting..." %
        self.domain_name)
      return
    log.debug(
      "Reset %s domain based to original topology description..." %
      self.domain_name)
    self.topoAdapter.edit_config(data=empty_cfg)


class UnifyDomainManager(AbstractDomainManager):
  """
  Manager class for unified handling of different domains using the Unify
  domain.

  The communication between ESCAPEv2 and domain agent relies on pre-defined
  REST-API functions and the Virtualizer format.

  .. note::
    Uses :class:`UnifyDomainAdapter` for communicate with the remote domain.
  """
  # DomainManager name
  name = "UNIFY"
  # Default domain name - Must override child classes to define the domain
  DEFAULT_DOMAIN_NAME = "UNIFY"

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, *args, **kwargs):
    """
    Init.
    """
    super(UnifyDomainManager, self).__init__(domain_name=domain_name, *args,
                                             **kwargs)

  def init (self, configurator, **kwargs):
    """
    Initialize the DomainManager.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :param kwargs: optional parameters
    :type kwargs: dict
    :return: None
    """
    super(UnifyDomainManager, self).init(configurator, **kwargs)

  def initiate_adapters (self, configurator):
    """
    Init Adapters.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :return: None
    """
    self.topoAdapter = configurator.load_component(
      component_name=AbstractESCAPEAdapter.TYPE_REMOTE,
      parent=self._adapters_cfg)

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(UnifyDomainManager, self).finit()

  def install_nffg (self, nffg_part):
    """
    Install :any:`NFFG` part into the domain using the specific REST-API
    function and Virtualizer format.
    :param nffg_part: domain related part of the mapped :any:`NFFG`
    :type nffg_part: :any:`NFFG`
    :return: status if the installation was success
    :rtype: bool
    """
    log.info("Install %s domain part..." % self.domain_name)
    try:
      status = self.topoAdapter.edit_config(nffg_part)
      return True if status is not None else False
    except:
      log.exception(
        "Got exception during NFFG installation into: %s." % self.domain_name)
      return False

  def clear_domain (self):
    """
    Reset remote domain based on the original (first response) topology.

    :return: None
    """
    empty_cfg = self.topoAdapter._original_virtualizer
    if empty_cfg is None:
      log.warning(
        "Missing original topology in %s domain! Skip domain resetting..." %
        self.domain_name)
      return
    log.debug(
      "Reset %s domain config based on stored empty config..." %
      self.domain_name)
    return self.topoAdapter.edit_config(data=empty_cfg)


class OpenStackDomainManager(UnifyDomainManager):
  """
  Manager class to handle communication with OpenStack domain.
  """
  # DomainManager name
  name = "OPENSTACK"
  # Default domain name
  DEFAULT_DOMAIN_NAME = "OPENSTACK"

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, *args, **kwargs):
    """
    Init.
    """
    super(OpenStackDomainManager, self).__init__(domain_name=domain_name,
                                                 *args, **kwargs)
    log.debug(
      "Init OpenStackDomainManager with domain name: %s" % self.domain_name)


class UniversalNodeDomainManager(UnifyDomainManager):
  """
  Manager class to handle communication with Universal Node (UN) domain.
  """
  # DomainManager name
  name = "UN"
  # Default domain name
  DEFAULT_DOMAIN_NAME = "UNIVERSAL_NODE"

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, *args, **kwargs):
    """
    Init.
    """
    super(UniversalNodeDomainManager, self).__init__(domain_name=domain_name,
                                                     *args, **kwargs)
    log.debug(
      "Init UniversalNodeDomainManager with domain name: %s" %
      self.domain_name)


class DockerDomainManager(AbstractDomainManager):
  """
  Adapter class to handle communication component in a Docker domain.

  .. warning::
    Not implemented yet!
  """
  # Domain name
  name = "DOCKER"
  # Default domain name
  DEFAULT_DOMAIN_NAME = "DOCKER"

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, *args, **kwargs):
    """
    Init
    """
    super(DockerDomainManager, self).__init__(domain_name=domain_name, *args,
                                              **kwargs)
    log.debug(
      "Init DockerDomainManager with domain name: %s" % self.domain_name)

  def initiate_adapters (self, configurator):
    pass

  def install_nffg (self, nffg_part):
    log.info("Install Docker domain part...")
    # TODO - implement
    pass

  def clear_domain (self):
    pass
