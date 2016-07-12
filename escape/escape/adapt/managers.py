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
import pprint

import re
from ncclient import NCClientError

from escape.adapt.adapters import RemoteESCAPEv2RESTAdapter, UnifyRESTAdapter
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
    log.debug("Create InternalDomainManager with domain name: %s" % domain_name)
    super(InternalDomainManager, self).__init__(domain_name=domain_name,
                                                *args, **kwargs)
    self.controlAdapter = None  # DomainAdapter for POX-InternalPOXAdapter
    self.topoAdapter = None  # DomainAdapter for Mininet-InternalMininetAdapter
    self.remoteAdapter = None  # NETCONF communication - VNFStarterAdapter
    self.portmap = {}  # Map (unique) dynamic ports to physical ports in EEs
    self.deployed_vnfs = {}  # container for replied NETCONF messages of
    # deployNF, key: (infra_id, nf_id), value: initiated_vnf part of the
    # parsed reply in JSON
    self.sapinfos = {}
    # Mapper structure for non-integer link id
    self.vlan_register = {}

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
    log.info("DomainManager for %s domain has been initialized!" %
             self.domain_name)

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
    self.remoteAdapter.finit()
    self.controlAdapter.finit()
    self.topoAdapter.finit()

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
      log.error("Missing topology description from topology Adapter! "
                "Skip SAP data discovery.")
    for sap in topo.saps:
      # skip inter-domain SAPs
      if sap.binding is not None:
        continue
      connected_node = [(v, link.dst.id) for u, v, link in
                        topo.real_out_edges_iter(sap.id)]
      if len(connected_node) > 1:
        log.warning("%s is connection to multiple nodes (%s)!" % (
          sap, [n[0] for n in connected_node]))
      for node in connected_node:
        mac = mn.getNodeByName(sap.id).MAC()
        ip = mn.getNodeByName(sap.id).IP()
        log.debug("Detected IP(%s) | MAC(%s) for %s connected to Node(%s) on "
                  "port: %s" % (ip, mac, sap, node[0], node[1]))
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
    :return: installation was success or not
    :rtype: bool
    """
    log.info(">>> Install %s domain part..." % self.domain_name)
    try:
      # Mininet domain does not support NF migration directly -->
      # Remove unnecessary and moved NFs first
      result = [
        self._delete_running_nfs(nffg=nffg_part),
        # then (re)initiate mapped NFs
        self._deploy_new_nfs(nffg=nffg_part)
      ]
      log.info("Perform traffic steering according to mapped tunnels/labels...")
      # OpenFlow flowrule deletion/addition is fairly cheap operations
      # The most robust solution is to delete every flowrule
      result.extend((
        self._delete_flowrules(nffg=nffg_part),
        # and (re)add the new ones
        self._deploy_flowrules(nffg_part=nffg_part))
      )
      return all(result)
    except:
      log.exception("Got exception during NFFG installation into: %s." %
                    self.domain_name)
      return False

  def clear_domain (self):
    """
    Infrastructure Layer has already been stopped and probably cleared.

    Skip cleanup process here.

    :return: cleanup result
    :rtype: bool
    """
    if not self.topoAdapter.check_domain_reachable():
      # This would be the normal behaviour if ESCAPEv2 is shutting down -->
      # Infrastructure layer has been cleared.
      log.debug("%s domain has already been cleared!" % self.domain_name)
      return True
    result = (
      # Just for sure remove NFs
      self._delete_running_nfs(),
      # and flowrules
      self._delete_flowrules()
    )
    return all(result)

  def _delete_running_nfs (self, nffg=None):
    """
    Stop and delete deployed NFs which are not existed the new mapped request.
    Mininet domain does not support NF migration and assume stateless network
    functions.

    Detect if an NF was moved during the previous mapping and
    remove that gracefully.

    If the ``nffg`` parameter is not given, skip the NF migration detection
    and remove all non-existent NF by default.

    :param nffg: the last mapped NFFG part
    :type nffg: :any:`NFFG`
    :return: deletion was successful or not
    :rtype: bool
    """
    result = True
    topo = self.topoAdapter.get_topology_resource()
    if topo is None:
      log.warning("Missing topology description from %s domain! "
                  "Skip deleting NFs..." % self.domain_name)
      return False
    log.debug("Check for removable NFs...")
    # Skip non-execution environments
    infras = [i.id for i in topo.infras if
              i.infra_type in (NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE)]
    for infra_id in infras:
      # Generate list of newly mapped NF on the infra
      old_running_nfs = [n.id for n in topo.running_nfs(infra_id)]
      # Detect non-moved NF if new mapping was given and skip deletion
      for nf_id in old_running_nfs:
        # If NF exist in the new mapping
        if nffg is not None and nf_id in nffg:
          new_running_nfs = [n.id for n in nffg.running_nfs(infra_id)]
          # And connected to the same infra
          if nf_id in new_running_nfs:
            # NF was not moved, Skip deletion
            log.debug('Unchanged NF: %s' % nf_id)
            continue
          # If the NF exists in the new mapping, but moved to another infra
          else:
            log.info("Found moved NF: %s")
            log.debug("NF migration is not supported! Stop and remove already "
                      "deployed NF and reinitialize later...")
        else:
          log.debug("Found removable NF: %s" % nf_id)
        # Create connection Adapter to EE agent
        connection_params = self.topoAdapter.get_agent_connection_params(
          infra_id)
        if connection_params is None:
          log.error("Missing connection params for communication with the "
                    "agent of Node: %s" % infra_id)
          result = False
          continue
        updated = self.remoteAdapter.update_connection_params(
          **connection_params)
        if updated:
          log.debug("Update connection params in %s: %s" % (
            self.remoteAdapter.__class__.__name__, updated))
        log.debug("Stop deployed NF: %s" % nf_id)
        try:
          vnf_id = self.deployed_vnfs[(infra_id, nf_id)]['vnf_id']
          reply = self.remoteAdapter.removeNF(vnf_id=vnf_id)
          log.log(VERBOSE, "Removed NF status:\n%s" % pprint.pformat(reply))
          # Remove NF from deployed cache
          del self.deployed_vnfs[(infra_id, nf_id)]
          # Delete infra ports connected to the deletable NF
          for u, v, link in topo.network.out_edges([nf_id], data=True):
            topo[v].del_port(id=link.dst.id)
          # Delete NF
          topo.del_node(nf_id)
        except KeyError:
          log.error("Deployed VNF data for NF: %s is not found! "
                    "Skip deletion..." % nf_id)
          result = False
          continue
        except NCClientError:
          log.error("Got NETCONF RPC communication error during NF: %s "
                    "deletion! Skip deletion..." % nf_id)
          result = False
          continue
    log.debug("NF deletion result: %s" % ("SUCCESS" if result else "FAILURE"))
    return result

  def _deploy_new_nfs (self, nffg):
    """
    Install the NFs mapped in the given NFFG.

    If an NF is already defined in the topology and it's state is up and
    running then the actual NF's initiation will be skipped!

    :param nffg: container NF-FG part need to be deployed
    :type nffg: :any:`NFFG`
    :return: deploy was successful or not
    :rtype: bool
    """
    log.info("Deploy mapped NFs into the domain: %s..." % self.domain_name)
    result = True
    self.portmap.clear()
    # Remove unnecessary SG and Requirement links to avoid mess up port
    # definition of NFs
    nffg.clear_links(NFFG.TYPE_LINK_SG)
    nffg.clear_links(NFFG.TYPE_LINK_REQUIREMENT)
    # Get physical topology description from Mininet
    mn_topo = self.topoAdapter.get_topology_resource()
    if mn_topo is None:
      log.warning("Missing topology description from %s domain! "
                  "Skip deploying NFs..." % self.domain_name)
      return False
    # Iter through the container INFRAs in the given mapped NFFG part
    # print mn_topo.dump()
    for infra in nffg.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE):
        log.debug("Infrastructure Node: %s (type: %s) is not Container type! "
                  "Continue to next Node..." %
                  (infra.id, infra.infra_type))
        continue
      else:
        log.debug("Check NFs mapped on Node: %s" % infra.id)
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in self.internal_topo.infras):
        log.error("Infrastructure Node: %s is not found in the %s domain! "
                  "Skip NF initiation on this Node..." %
                  (infra.id, self.domain_name))
        result = False
        continue
      # Iter over the NFs connected the actual INFRA
      for nf in nffg.running_nfs(infra.id):
        # NF with id is already deployed --> change the dynamic port to
        # static and continue
        if nf.id in (nf.id for nf in self.internal_topo.nfs):
          log.debug("NF: %s has already been initiated. Continue to next NF..."
                    % nf.id)
          for u, v, link in nffg.real_out_edges_iter(nf.id):
            dyn_port = nffg[v].ports[link.dst.id]
            for x, y, l in mn_topo.real_out_edges_iter(nf.id):
              if l.src.id == link.src.id:
                self.portmap[dyn_port.id] = l.dst.id
                dyn_port.id = l.dst.id
                break
          continue
        # Extract the initiation params
        params = {'nf_type': nf.functional_type,
                  'nf_ports': [link.src.id for u, v, link in
                               nffg.real_out_edges_iter(nf.id)],
                  'infra_id': infra.id}
        # Check if every param is not None or empty
        if not all(params.values()):
          log.error("Missing arguments for initiation of NF: %s. Extracted "
                    "params: %s" % (nf.id, params))
          result = False
          continue
        # Create connection Adapter to EE agent
        connection_params = self.topoAdapter.get_agent_connection_params(
          infra.id)
        if connection_params is None:
          log.error("Missing connection params for communication with the "
                    "agent of Node: %s" % infra.id)
          result = False
          continue
        # Save last used adapter --> and last RPC result
        log.debug("Initiating NF: %s with params: %s" % (nf.id, params))
        updated = self.remoteAdapter.update_connection_params(
          **connection_params)
        if updated:
          log.debug("Update connection params in %s: %s" % (
            self.remoteAdapter.__class__.__name__, updated))
        try:
          vnf = self.remoteAdapter.deployNF(**params)
        except NCClientError:
          log.error("Got NETCONF RPC communication error during NF: %s "
                    "deploy! Skip deploy..." % nf.id)
          result = False
          continue
        except BaseException:
          log.error("Got unexpected error during NF: %s "
                    "initiation! Skip initiation..." % nf.name)
          result = False
          continue
        log.log(VERBOSE, "Initiated VNF:\n%s" % pprint.pformat(vnf))
        # Check if NETCONF communication was OK
        if vnf and 'initiated_vnfs' in vnf and vnf['initiated_vnfs']['pid'] \
           and vnf['initiated_vnfs']['status'] == \
              VNFStarterAPI.VNFStatus.s_UP_AND_RUNNING:
          log.info("NF: %s initiation has been verified on Node: %s" % (
            nf.id, infra.id))
          log.debug("Initiated VNF id: %s, PID: %s, status: %s" % (
            vnf['initiated_vnfs']['vnf_id'], vnf['initiated_vnfs']['pid'],
            vnf['initiated_vnfs']['status']))
        else:
          log.error("Initiated NF: %s is not verified. Initiation was "
                    "unsuccessful!" % nf.id)
          result = False
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
        for nf_id, infra_id, link in nffg.real_out_edges_iter(nf.id):
          # Get Link's src ref to new NF's port
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
            log.warning("Can't get Container port from RPC result! Set "
                        "generated port number...")
          # Create INFRA side Port
          infra_port = mn_topo.network.node[infra_id].add_port(
            id=infra_port_num)
          log.debug("%s - detected physical %s" % (deployed_nf, infra_port))
          # Add Links to mn topo
          mn_topo.add_undirected_link(port1=nf_port, port2=infra_port,
                                      dynamic=True, delay=link.delay,
                                      bandwidth=link.bandwidth)
          # Port mapping
          dynamic_port = nffg.network.node[infra_id].ports[link.dst.id].id
          self.portmap[dynamic_port] = infra_port_num
          # Update port in nffg_part
          nffg.network.node[infra_id].ports[
            link.dst.id].id = infra_port_num

        log.debug("%s topology description is updated with NF: %s" % (
          self.domain_name, deployed_nf.name))

    log.debug("Rewrite dynamically generated port numbers in flowrules...")
    # Update port numbers in flowrules
    for infra in nffg.infras:
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
            log.warning("Missing 'in_port' from match field: %s" %
                        flowrule.match)
            continue
          _action = flowrule.action.split(';')
          if not _action[0].startswith("output="):
            log.warning("Missing 'output' from action field: %s" %
                        flowrule.action)
            continue
          for dyn, phy in self.portmap.iteritems():
            _match[0] = _match[0].replace(str(dyn), str(phy))
            _action[0] = _action[0].replace(str(dyn), str(phy))
          flowrule.match = ";".join(_match)
          flowrule.action = ";".join(_action)
    log.info("Initiation of NFs in NFFG part: %s has been finished! Result: %s"
             % (nffg, "SUCCESS" if result else "FAILURE"))
    return result

  def _delete_flowrules (self, nffg=None):
    """
    Delete all flowrules from the first (default) table of all infras.

    :param nffg: last mapped NFFG part
    :type nffg: :any:`NFFG`
    :return: deletion was successful or not
    :rtype: bool
    """
    log.debug("Reset domain steering and delete installed flowrules...")
    result = True
    # Get topology NFFG to detect corresponding infras and skip needless infras
    topo = self.topoAdapter.get_topology_resource()
    if topo is None:
      log.warning("Missing topology description from %s domain! Skip flowrule "
                  "deletions..." % self.domain_name)
      return False
    # If nffg is not given or is a bare topology, which is probably a cleanup
    # topo, all the flowrules in physical topology will be removed
    if nffg is None or nffg.is_bare():
      log.debug(
        "Detected empty request NFFG! Remove all the installed flowrules...")
      nffg = topo
    topo_infras = [n.id for n in topo.infras]
    # Iter through the container INFRAs in the given mapped NFFG part
    log.debug("Managed topo infras: %s" % topo_infras)
    for infra in nffg.infras:
      log.debug("Process flowrules in infra: %s" % infra.id)
      if infra.infra_type not in (NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
                                  NFFG.TYPE_INFRA_SDN_SW):
        log.warning(
          "Detected virtual Infrastructure Node type: %s! Skip infra node "
          "processing..." % infra.infra_type)
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in topo_infras:
        log.error("Infrastructure Node: %s is not found in the %s domain! Skip "
                  "flowrule deletion on this Node..." % (
                    infra.id, self.domain_name))
        result = False
        continue
      try:
        dpid = self.controlAdapter.infra_to_dpid[infra.id]
      except KeyError as e:
        log.warning("Missing DPID for Infra(id: %s)! Skip deletion of "
                    "flowrules" % e)
        result = False
        continue
      # Check the OF connection is alive
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        log.warning("Skipping DELETE flowrules! Cause: connection for %s - "
                    "DPID: %s is not found!" % (infra, dpid_to_str(dpid)))
        result = False
        continue
      self.controlAdapter.delete_flowrules(infra.id)
    log.debug("Flowrule deletion result: %s" %
              ("SUCCESS" if result else "FAILURE"))
    return result

  def _deploy_flowrules (self, nffg_part):
    """
    Install the flowrules given in the NFFG.

    If a flowrule is already defined it will be updated.

    :param nffg_part: NF-FG part need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: deploy was successful or not
    :rtype: bool
    """
    log.debug("Deploy flowrules into the domain: %s..." % self.domain_name)
    result = True
    # Remove unnecessary SG and Requirement links to avoid mess up port
    # definition of NFs
    nffg_part.clear_links(NFFG.TYPE_LINK_SG)
    nffg_part.clear_links(NFFG.TYPE_LINK_REQUIREMENT)

    # # Get physical topology description from POX adapter
    # topo = self.controlAdapter.get_topology_resource()
    topo = self.topoAdapter.get_topology_resource()
    if topo is None:
      log.warning("Missing topology description from %s domain! Skip deploying "
                  "flowrules..." % self.domain_name)
      return False
    # Iter through the container INFRAs in the given mapped NFFG part
    for infra in nffg_part.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
         NFFG.TYPE_INFRA_SDN_SW):
        log.debug("Infrastructure Node: %s (type: %s) is not Switch or "
                  "Container type! Continue to next Node..." %
                  (infra.id, infra.infra_type))
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in topo.infras):
        log.error("Infrastructure Node: %s is not found in the %s domain! Skip "
                  "flowrule install on this Node..." % (
                    infra.id, self.domain_name))
        result = False
        continue
      try:
        dpid = self.controlAdapter.infra_to_dpid[infra.id]
      except KeyError as e:
        log.warning("Missing DPID for Infra(id: %s)! Skip deploying flowrules "
                    "for Infra" % e)
        result = False
        continue
      # Check the OF connection is alive
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        log.warning("Skipping INSTALL flowrule! Cause: connection for %s - "
                    "DPID: %s is not found!" % (infra, dpid_to_str(dpid)))
        result = False
        continue
      for port in infra.ports:
        for flowrule in port.flowrules:
          try:
            match = NFFGConverter.field_splitter(
              type=NFFGConverter.TYPE_MATCH,
              field=flowrule.match)
            if "in_port" not in match:
              log.warning("Missing in_port field from match field! "
                          "Using container port number...")
              match["in_port"] = port.id
            action = NFFGConverter.field_splitter(
              type=NFFGConverter.TYPE_ACTION,
              field=flowrule.action)
          except RuntimeError as e:
            log.warning("Wrong format in match/action field: %s" % e)
            result = False
            continue
          # Process the abstract TAG in match
          if 'vlan_id' in match:
            log.debug("Process TAG: %s in match field" % match['vlan_id'])
            vlan = self.__process_tag(abstract_id=match['vlan_id'])
            if vlan is not None:
              match['vlan_id'] = vlan
            else:
              log.error("Abort Flowrule deployment...")
              return
          # Process the abstract TAG in action
          if 'vlan_push' in action:
            log.debug("Process TAG: %s in action field" % action['vlan_push'])
            vlan = self.__process_tag(abstract_id=action['vlan_push'])
            if vlan is not None:
              action['vlan_push'] = vlan
            else:
              log.error("Abort Flowrule deployment...")
              return
          log.debug("Assemble OpenFlow flowrule from: %s" % flowrule)
          self.controlAdapter.install_flowrule(infra.id, match, action)
    log.debug("Flowrule deploy result: %s" %
              ("SUCCESS" if result else "FAILURE"))
    log.log(VERBOSE,
            "Registered VLAN IDs: %s" % pprint.pformat(self.vlan_register))
    return result

  def __process_tag (self, abstract_id):
    """
    Generate a valid VLAN id from the raw_id data which derived from directly
    an SG hop link id.

    :param abstract_id: raw link id
    :type abstract_id: str or int
    :return: valid VLAN id
    :rtype: int
    """
    # Check if the abstract tag has already processed
    if abstract_id in self.vlan_register:
      log.debug("Found already register TAG ID: %s ==> %s" % (
        abstract_id, self.vlan_register[abstract_id]))
      return self.vlan_register[abstract_id]
    # Check if the raw_id is a valid number
    try:
      vlan_id = int(abstract_id)
      # Check if the raw_id is free
      if 0 < vlan_id < 4095 and vlan_id not in self.vlan_register.itervalues():
        self.vlan_register[abstract_id] = vlan_id
        log.debug(
          "Abstract ID a valid not-taken VLAN ID! Register %s ==> %s" % (
            abstract_id, vlan_id))
        return vlan_id
    except ValueError:
      # Cant be converted to int, continue with raw_id processing
      pass
    trailer_num = re.search(r'\d+$', abstract_id)
    # If the raw_id ends with number
    if trailer_num is not None:
      # Check if the trailing number is a valid VLAN id (0 and 4095 are
      # reserved)
      trailer_num = int(trailer_num.group())  # Get matched data from Match obj
      # Check if the VLAN candidate is free
      if 0 < trailer_num < 4095 and \
            trailer_num not in self.vlan_register.itervalues():
        self.vlan_register[abstract_id] = trailer_num
        log.debug(
          "Trailing number is a valid non-taken VLAN ID! Register %s ==> "
          "%s..." % (abstract_id, trailer_num))
        return trailer_num
        # else Try to find a free VLAN
      else:
        log.debug(
          "Detected trailing number: %s is not a valid VLAN or already "
          "taken!" % trailer_num)
    # No valid VLAN number has found from abstract_id, try to find a free VLAN
    for vlan in xrange(1, 4094):
      if vlan not in self.vlan_register.itervalues():
        self.vlan_register[abstract_id] = vlan
        log.debug(
          "Generated and registered VLAN id %s ==> %s" % (abstract_id, vlan))
        return vlan
    # For loop is exhausted
    else:
      log.error("No available VLAN id found!")
      return None


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
    log.debug("Create SDNDomainManager with domain name: %s" % domain_name)
    super(SDNDomainManager, self).__init__(domain_name=domain_name, *args,
                                           **kwargs)
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
    log.info(
      "DomainManager for %s domain has been initialized!" % self.domain_name)

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
    self.topoAdapter.finit()
    self.controlAdapter.finit()

  @property
  def controller_name (self):
    return self.controlAdapter.task_name

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the SDN domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: installation was success or not
    :rtype: bool
    """
    log.info("Install %s domain part..." % self.domain_name)
    try:
      result = (
        self._delete_flowrules(nffg_part=nffg_part),
        self._deploy_flowrules(nffg_part=nffg_part)
      )
      return all(result)
    except:
      log.exception(
        "Got exception during NFFG installation into: %s." % self.domain_name)
      return False

  def _delete_flowrules (self, nffg_part):
    """
    Delete all flowrules from the first (default) table of all infras.

    :param nffg_part: last mapped NFFG part
    :type nffg_part: :any:`NFFG`
    :return: deletion was successful or not
    :rtype: bool
    """
    log.debug("Removing flowrules...")
    # Iter through the container INFRAs in the given mapped NFFG part
    result = True
    for infra in nffg_part.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
         NFFG.TYPE_INFRA_SDN_SW):
        continue
      # Check the OF connection is alive
      try:
        dpid = self.controlAdapter.infra_to_dpid[infra.id]
      except KeyError as e:
        log.warning("Missing DPID for Infra(id: %s)! Skip deletion of flowrules"
                    % e)
        result = False
        continue
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        log.warning("Skipping DELETE flowrules! Cause: connection for %s - "
                    "DPID: %s is not found!" % (infra, dpid_to_str(dpid)))
        result = False
        continue
      self.controlAdapter.delete_flowrules(infra.id)
    log.debug("Flowrule deletion result: %s" %
              ("SUCCESS" if result else "FAILURE"))
    return result

  def _deploy_flowrules (self, nffg_part):
    """
    Install the flowrules given in the NFFG.

    If a flowrule is already defined it will be updated.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: deploy was successful or not
    :rtype: bool
    """
    log.debug("Deploy flowrules into the domain: %s..." % self.domain_name)
    result = True
    # Remove unnecessary SG and Requirement links to avoid mess up port
    # definition of NFs
    nffg_part.clear_links(NFFG.TYPE_LINK_SG)
    nffg_part.clear_links(NFFG.TYPE_LINK_REQUIREMENT)
    # Get physical topology description from POX adapter
    topo = self.topoAdapter.get_topology_resource()
    if topo is None:
      log.warning("Missing topology description from %s domain! "
                  "Skip deploying flowrules..." % self.domain_name)
      return False
    # Iter through the container INFRAs in the given mapped NFFG part
    for infra in nffg_part.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
         NFFG.TYPE_INFRA_SDN_SW):
        log.debug("Infrastructure Node: %s (type: %s) is not Switch or "
                  "Container type! Continue to next Node..." %
                  (infra.id, infra.infra_type))
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in topo.infras):
        log.error("Infrastructure Node: %s is not found in the %s domain! Skip "
                  "flowrule install on this Node..." %
                  (infra.id, self.domain_name))
        result = False
        continue
      # Check the OF connection is alive
      try:
        dpid = self.controlAdapter.infra_to_dpid[infra.id]
      except KeyError as e:
        log.warning("Missing DPID for Infra(id: %s)! "
                    "Skip deploying flowrules for Infra" % e)
        result = False
        continue
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        log.warning("Skipping INSTALL flowrule! Cause: connection for %s - "
                    "DPID: %s is not found!" % (infra, dpid_to_str(dpid)))
        result = False
        continue
      for port in infra.ports:
        for flowrule in port.flowrules:
          try:
            match = NFFGConverter.field_splitter(type="MATCH",
                                                 field=flowrule.match)
            if "in_port" not in match:
              log.warning("Missing in_port field from match field! "
                          "Using container port number...")
              match["in_port"] = port.id
            action = NFFGConverter.field_splitter(type="ACTION",
                                                  field=flowrule.action)
          except RuntimeError as e:
            log.warning("Wrong format in match/action field: %s" % e)
            result = False
            continue
          log.debug("Assemble OpenFlow flowrule from: %s" % flowrule)
          self.controlAdapter.install_flowrule(infra.id, match=match,
                                               action=action)
    log.debug("Flowrule deploy result: %s" %
              ("SUCCESS" if result else "FAILURE"))
    return result

  def clear_domain (self):
    """
    Delete all flowrule in the registered SDN/OF switches.

    :return: cleanup result
    :rtype: bool
    """
    log.debug("Clear all flowrules from switches registered in SDN domain...")
    # Delete all flowrules in the Infra nodes defined the topology file.
    sdn_topo = self.topoAdapter.get_topology_resource()
    if sdn_topo is None:
      log.warning("SDN topology is missing! Skip domain resetting...")
      return
    # Remove flowrules
    return self._delete_flowrules(nffg_part=sdn_topo)


class RemoteESCAPEDomainManager(AbstractRemoteDomainManager):
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
    log.debug(
      "Create RemoteESCAPEDomainManager with domain name: %s" % domain_name)
    super(RemoteESCAPEDomainManager, self).__init__(domain_name=domain_name,
                                                    *args, **kwargs)

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
    log.info(
      "DomainManager for %s domain has been initialized!" % self.domain_name)

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
    self.topoAdapter.finit()

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the internal domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: installation was success or not
    :rtype: bool
    """
    log.info("Install %s domain part..." % self.domain_name)
    try:
      if not self._poll and self._diff:
        log.debug("Polling is disabled. Requesting the most recent topology "
                  "from domain: %s for installation..." % self.domain_name)
        # Request the most recent topo, which will update the cached
        # last_virtualizer for the diff calculation
        self.topoAdapter.get_config()
      status = self.topoAdapter.edit_config(nffg_part, diff=self._diff)
      return True if status is not None else False
    except:
      log.exception("Got exception during NFFG installation into: %s." %
                    self.domain_name)
      return False

  def clear_domain (self):
    """
    Reset remote domain based on the original (first response) topology.

    :return: cleanup result
    :rtype: bool
    """
    empty_cfg = self.topoAdapter.get_original_topology()
    if empty_cfg is None:
      log.error("Missing original topology in %s domain! "
                "Skip domain resetting..." % self.domain_name)
      return
    log.info("Reset %s domain based on original topology description..." %
             self.domain_name)
    # If poll is enabled then the last requested topo is most likely the most
    # recent topo else request the topology for the most recent one and compute
    # diff if it is necessary
    if not self._poll and self._diff:
      log.debug("Polling is disabled. Requesting the most recent topology "
                "from domain: %s for domain clearing..." % self.domain_name)
      if (isinstance(self.topoAdapter, RemoteESCAPEv2RESTAdapter) and
            self.topoAdapter._unify_interface) or \
         isinstance(self.topoAdapter, UnifyRESTAdapter):
        recent_topo = self.topoAdapter.get_config()
        if recent_topo is not None:
          log.debug("Explicitly calculating diff for domain clearing...")
          diff = recent_topo.diff(empty_cfg)
          status = self.topoAdapter.edit_config(data=diff)
        else:
          log.error("Skip domain resetting: %s! "
                    "Requested topology is missing!" % self.domain_name)
          return False
      else:
        status = False
    else:
      status = self.topoAdapter.edit_config(data=empty_cfg, diff=self._diff)
    return True if status is not None else False


class UnifyDomainManager(AbstractRemoteDomainManager):
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
    log.debug(
      "Create UnifyDomainManager with domain name: %s" % domain_name)
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
    log.info(
      "DomainManager for %s domain has been initialized!" % self.domain_name)

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
    self.topoAdapter.finit()

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
      if not self._poll and self._diff:
        log.debug("Polling is disabled. Requesting the most recent topology "
                  "from domain: %s for installation..." % self.domain_name)
        # Request the most recent topo, which will update the cached
        # last_virtualizer for the diff calculation
        self.topoAdapter.get_config()
      status = self.topoAdapter.edit_config(nffg_part, diff=self._diff)
      return True if status is not None else False
    except:
      log.exception("Got exception during NFFG installation into: %s." %
                    self.domain_name)
      return False

  def clear_domain (self):
    """
    Reset remote domain based on the original (first response) topology.

    :return: cleanup result
    :rtype: bool
    """
    empty_cfg = self.topoAdapter.get_original_topology()
    if empty_cfg is None:
      log.error("Missing original topology in %s domain! "
                "Skip domain resetting..." % self.domain_name)
      return
    log.info("Reset %s domain based on original topology description..." %
             self.domain_name)
    # If poll is enabled then the last requested topo is most likely the most
    # recent topo else request the topology for the most recent one and compute
    # diff if it is necessary
    if not self._poll and self._diff:
      log.debug("Polling is disabled. Requesting the most recent topology "
                "from domain: %s for domain clearing..." % self.domain_name)
      recent_topo = self.topoAdapter.get_config()
      if recent_topo is not None:
        log.debug("Explicitly calculating diff for domain clearing...")
        diff = recent_topo.diff(empty_cfg)
        status = self.topoAdapter.edit_config(data=diff, diff=False)
      else:
        log.error("Skip domain resetting: %s! "
                  "Requested topology is missing!" % self.domain_name)
        return False
    else:
      status = self.topoAdapter.edit_config(data=empty_cfg, diff=self._diff)
    return True if status is not None else False


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
    log.debug(
      "Create OpenStackDomainManager wrapper for domain: %s" % domain_name)
    super(OpenStackDomainManager, self).__init__(domain_name=domain_name,
                                                 *args, **kwargs)


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
    log.debug(
      "Create UniversalNodeDomainManager wrapper for domain: %s" % domain_name)
    super(UniversalNodeDomainManager, self).__init__(domain_name=domain_name,
                                                     *args, **kwargs)
