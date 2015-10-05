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

from escape.adapt.adapters import *
from escape.util.domain import *
from pox.lib.util import dpid_to_str


class InternalDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with internally emulated network.

  .. note::
    Uses :class:`InternalMininetAdapter` for managing the emulated network and
    :class:`InternalPOXAdapter` for controlling the network.
  """
  # Domain name
  name = "INTERNAL"

  def __init__ (self, **kwargs):
    """
    Init
    """
    log.debug("Init InternalDomainManager - params: %s" % kwargs)
    super(InternalDomainManager, self).__init__(**kwargs)
    self.controlAdapter = None  # DomainAdapter for POX - InternalPOXAdapter
    self.remoteAdapter = None  # NETCONF communication - VNFStarterAdapter
    self.portmap = {}  # Map (unique) dynamic ports to physical ports in EEs
    self.topo = None  # Store topology description

  def init (self, configurator, **kwargs):
    """
    Initialize Internal domain manager.

    :return: None
    """
    # Init adapter for internal topo emulation: Mininet
    self.topoAdapter = configurator.load_component(InternalMininetAdapter.name)
    # Init adapter for internal controller: POX
    self.controlAdapter = configurator.load_component(InternalPOXAdapter.name)
    # Init default NETCONF adapter
    self.remoteAdapter = configurator.load_component(VNFStarterAdapter.name)
    super(InternalDomainManager, self).init(configurator, **kwargs)

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

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the internal domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    try:
      log.info("Install %s domain part..." % self.name)
      self._deploy_nfs(nffg_part=nffg_part)
      self._delete_flowrules(nffg_part=nffg_part)
      self._deploy_flowrules(nffg_part=nffg_part)
      return True
    except:
      log.error(
        "Got exception during NFFG installation into: %s. Cause:\n%s" % (
          self.name, sys.exc_info()[0]))
      return False

  def clear_domain (self):
    pass

  def _deploy_nfs (self, nffg_part):
    """
    Install the NFs mapped in the given NFFG.

    If an NF is already defined in the topology and it's state is up and
    running then the actual NF's initiation will be skipped!

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: None
    """
    # FIXME - SIGCOMM
    self.portmap.clear()
    # Remove unnecessary SG and Requirement links to avoid mess up port
    # definition of NFs
    nffg_part.clear_links(NFFG.TYPE_LINK_SG)
    nffg_part.clear_links(NFFG.TYPE_LINK_REQUIREMENT)
    # Get physical topology description from Mininet
    mn_topo = self.topoAdapter.get_topology_resource()
    # Iter through the container INFRAs in the given mapped NFFG part
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
          "initiation on this Node..." % (infra.short_name, self.name))
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
        params = {'nf_type': nf.functional_type,
                  'nf_ports': [link.src.id for u, v, link in
                               nffg_part.network.out_edges_iter((nf.id,),
                                                                data=True)],
                  'infra_id': infra.id}
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
        else:
          log.error(
            "Initiated NF: %s is not verified. Initiation was unsuccessful!"
            % nf.short_name)
          continue
        # Add initiated NF to topo description
        log.info("Update Infrastructure layer topology description...")
        deployed_nf = nf.copy()
        deployed_nf.ports.clear()
        mn_topo.add_nf(nf=deployed_nf)
        # Add Link between actual NF and INFRA
        for nf_id, infra_id, link in nffg_part.network.out_edges_iter((nf.id,),
                                                                      data=True):
          # Get Link's src ref to new NF's port
          # nf_port = deployed_nf.ports[link.src.id]
          # Create new Port for new NF
          nf_port = deployed_nf.ports.append(nf.ports[link.src.id].copy())

          def get_sw_port (vnf):
            """
            Return the switch port parsed from result of getVNFInfo
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
          self.name, deployed_nf.name))
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
          for dyn, phy in self.portmap.iteritems():
            match = flowrule.match.replace(str(dyn), str(phy))
            flowrule.match = match
            action = flowrule.action.replace(str(dyn), str(phy))
            flowrule.action = action

    log.info("Initiation of NFs in NFFG part: %s is finished!" % nffg_part)

  def _delete_flowrules (self, nffg_part):
    """
    Delete all flowrules from the first (default) table of all infras.
    """
    topo = self.topoAdapter.get_topology_resource()
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
                    infra.short_name, self.name))
        continue
      # Check the OF connection is alive
      dpid = self.controlAdapter.infra_to_dpid[infra.id]
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        log.warning(
          "Skipping DELETE flowrules. Cause: connection for %s - DPID: %s is "
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

    # # Get physical topology description from POX adapter
    # topo = self.controlAdapter.get_topology_resource()
    topo = self.topoAdapter.get_topology_resource()

    import re  # regular expressions
    # Iter through the container INFRAs in the given mapped NFFG part
    for infra in nffg_part.infras:
      if infra.infra_type not in (
           NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
           NFFG.TYPE_INFRA_SDN_SW):
        log.debug(
          "Infrastructure Node: %s (type: %s) is not Switch or Container type! "
          "Continue to next Node..." % (infra.short_name, infra.infra_type))
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in topo.infras):
        log.error("Infrastructure Node: %s is not found in the %s domain! Skip "
                  "flowrule install on this Node..." % (
                    infra.short_name, self.name))
        continue
      # Check the OF connection is alive
      dpid = self.controlAdapter.infra_to_dpid[infra.id]
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        log.warning(
          "Skipping INSTALL flowrule. Cause: connection for %s - DPID: %s is "
          "not found!" % (infra, dpid_to_str(dpid)))
        continue
      for port in infra.ports:
        for flowrule in port.flowrules:
          match = {}
          action = {}
          # if re.search(r';', flowrule.match):
          #   # multiple elements in match field
          #   in_port = re.sub(r'.*in_port=(.*);.*', r'\1', flowrule.match)
          # else:
          #   # single element in match field
          #   in_port = re.sub(r'.*in_port=(.*)', r'\1', flowrule.match)
          match['in_port'] = port.id
          # Check match fields - currently only vlan_id
          # TODO: add further match fields
          if re.search(r'TAG', flowrule.match):
            tag = re.sub(r'.*TAG=.*-(.*);?', r'\1', flowrule.match)
            match['vlan_id'] = tag

          if re.search(r';', flowrule.action):
            # multiple elements in action field
            out = re.sub(r'.*output=(.*);.*', r'\1', flowrule.action)
          else:
            # single element in action field
            out = re.sub(r'.*output=(.*)', r'\1', flowrule.action)
          action['out'] = out

          if re.search(r'TAG', flowrule.action):
            if re.search(r'UNTAG', flowrule.action):
              action['vlan_pop'] = True
            else:
              push_tag = re.sub(r'.*TAG=.*-(.*);?', r'\1', flowrule.action)
              action['vlan_push'] = push_tag

          self.controlAdapter.install_flowrule(infra.id, match=match,
                                               action=action)


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

  def __init__ (self, **kwargs):
    """
    Init
    """
    log.debug("Init RemoteESCAPEDomainManager - params: %s" % kwargs)
    super(RemoteESCAPEDomainManager, self).__init__(**kwargs)

  def init (self, configurator, **kwargs):
    """
    Initialize Internal domain manager.

    :return: None
    """
    # Init adapter for remote ESCAPEv2 domain
    self.topoAdapter = configurator.load_component(
      RemoteESCAPEv2RESTAdapter.name)
    super(RemoteESCAPEDomainManager, self).init(configurator, **kwargs)

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
    nffg_part = self._update_nffg(nffg_part.copy())
    try:
      status_code = self.topoAdapter.edit_config(nffg_part)
      if status_code is not None:
        return True
      else:
        return False
    except:
      log.error(
        "Got exception during NFFG installation into: %s. Cause:\n%s" % (
          self.name, sys.exc_info()[0]))

  def _update_nffg (self, nffg_part):
    """
    Update domain descriptor of infras: REMOTE -> INTERNAL

    :param nffg_part: NF-FG need to be updated
    :type nffg_part: :any:`NFFG`
    :return: updated NFFG
    :rtype: :any:`NFFG`
    """
    for infra in nffg_part.infras:
      if infra.infra_type not in (
           NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
           NFFG.TYPE_INFRA_SDN_SW):
        log.debug(
          "Infrastructure Node: %s (type: %s) is not Switch or Container type! "
          "Continue to next Node..." % (infra.short_name, infra.infra_type))
        continue
      if infra.domain == 'REMOTE':
        infra.domain = 'INTERNAL'
    return nffg_part

  def clear_domain (self):
    pass


class OpenStackDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with OpenStack domain.

  .. note::
    Uses :class:`OpenStackRESTAdapter` for communicate with the remote domain.
  """
  # Domain name
  name = "OPENSTACK"

  def __init__ (self, **kwargs):
    """
    Init.
    """
    log.debug("Init OpenStackDomainManager - params: %s" % kwargs)
    super(OpenStackDomainManager, self).__init__(**kwargs)

  def init (self, configurator, **kwargs):
    """
    Initialize OpenStack domain manager.

    :return: None
    """
    self.topoAdapter = configurator.load_component(OpenStackRESTAdapter.name)
    super(OpenStackDomainManager, self).init(configurator, **kwargs)

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(OpenStackDomainManager, self).finit()

  def install_nffg (self, nffg_part):
    log.info("Install %s domain part..." % self.name)
    # TODO - implement just convert NFFG to appropriate format and send out
    # FIXME - SIGCOMM
    # config = nffg_part.dump()
    # with open('pox/global-mapped-os-nffg.xml', 'r') as f:
    #   nffg_part = f.read()
    try:
      status_code = self.topoAdapter.edit_config(nffg_part)
      if status_code is not None:
        return True
      else:
        return False
    except:
      log.error(
        "Got exception during NFFG installation into: %s. Cause:\n%s" % (
          self.name, sys.exc_info()[0]))
      raise

  def clear_domain (self):
    empty_cfg = self.topoAdapter.original_virtualizer
    if empty_cfg is None:
      log.error(
        "Missing original topology in %s domain! Skip domain resetting..." %
        self.name)
      return
    log.debug("Reset %s domain config based on stored empty config" % self.name)
    self.topoAdapter.edit_config(data=empty_cfg.xml())


class UniversalNodeDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with Universal Node (UN) domain.

  .. note::
    Uses :class:`UniversalNodeRESTAdapter` for communicate with the remote
    domain.
  """
  # Domain name
  name = "UN"

  def __init__ (self, **kwargs):
    """
    Init.
    """
    log.debug("Init UniversalNodeDomainManager - params: %s" % kwargs)
    super(UniversalNodeDomainManager, self).__init__(**kwargs)

  def init (self, configurator, **kwargs):
    """
    Initialize OpenStack domain manager.

    :return: None
    """
    self.topoAdapter = configurator.load_component(
      UniversalNodeRESTAdapter.name)
    super(UniversalNodeDomainManager, self).init(configurator, **kwargs)

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(UniversalNodeDomainManager, self).finit()

  def install_nffg (self, nffg_part):
    log.info("Install %s domain part..." % self.name)
    # TODO - implement just convert NFFG to appropriate format and send out
    # FIXME - SIGCOMM
    # print nffg_part.dump()
    # with open('pox/global-mapped-un.nffg', 'r') as f:
    #   nffg_part = f.read()
    try:
      status_code = self.topoAdapter.edit_config(nffg_part)
      if status_code is not None:
        return True
      else:
        return False
    except:
      log.error(
        "Got exception during NFFG installation into: %s. Cause:\n%s" % (
          self.name, sys.exc_info()[0]))

  def clear_domain (self):
    empty_cfg = self.topoAdapter.original_virtualizer
    if empty_cfg is None:
      log.error(
        "Missing original topology in %s domain! Skip domain resetting..." %
        self.name)
      return
    log.debug("Reset %s domain config based on stored empty config" % self.name)
    self.topoAdapter.edit_config(data=empty_cfg.xml())


class DockerDomainManager(AbstractDomainManager):
  """
  Adapter class to handle communication component in a Docker domain.

  .. warning::
    Not implemented yet!
  """
  # Domain name
  name = "DOCKER"

  def __init__ (self, **kwargs):
    """
    Init
    """
    log.debug("Init DockerDomainManager - params %s" % kwargs)
    super(DockerDomainManager, self).__init__()

  def install_nffg (self, nffg_part):
    log.info("Install Docker domain part...")
    # TODO - implement
    pass

  def clear_domain (self):
    pass


class SDNDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with POX-controlled SDN domain.

  .. note::
    Uses :class:`InternalPOXAdapter` for controlling the network.
  """
  # Domain name
  name = "SDN"

  def __init__ (self, **kwargs):
    """
    Init
    """
    log.debug("Init SDNDomainManager - params: %s" % kwargs)
    super(SDNDomainManager, self).__init__(**kwargs)
    self.controlAdapter = None  # DomainAdapter for POX - InternalPOXAdapter
    self.topo = None  # SDN domain topology stored in NFFG

  def init (self, configurator, **kwargs):
    """
    Initialize SDN domain manager.

    :return: None
    """
    # Init adapter for internal controller: POX
    self.controlAdapter = configurator.load_component(SDNDomainPOXAdapter.name)
    # Use the same adapter for checking resources
    self.topoAdapter = self.controlAdapter
    super(SDNDomainManager, self).init(configurator, **kwargs)

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
      log.info("Install %s domain part..." % self.name)
      # log.info("NFFG:\n%s" % nffg_part.dump())
      log.info("NFFG: %s" % nffg_part)
      self._delete_flowrules(nffg_part=nffg_part)
      self._deploy_flowrules(nffg_part=nffg_part)
      return True
    except:
      log.error(
        "Got exception during NFFG installation into: %s. Cause:\n%s" % (
          self.name, sys.exc_info()[0]))
      return False

  def clear_domain (self):
    pass

  def _delete_flowrules (self, nffg_part):
    """
    Delete all flowrules from the first (default) table of all infras.
    """
    topo = self.controlAdapter.get_topology_resource()
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
                    infra.short_name, self.name))
        continue
      # Check the OF connection is alive
      dpid = self.controlAdapter.infra_to_dpid[infra.id]
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        log.warning(
          "Skipping DELETE flowrules. Cause: connection for %s - DPID: %s is "
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
    topo = self.controlAdapter.get_topology_resource()
    import re  # regular expressions
    # Iter through the container INFRAs in the given mapped NFFG part
    for infra in nffg_part.infras:
      if infra.infra_type not in (
           NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
           NFFG.TYPE_INFRA_SDN_SW):
        log.debug(
          "Infrastructure Node: %s (type: %s) is not Switch or Container type! "
          "Continue to next Node..." % (infra.short_name, infra.infra_type))
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in topo.infras):
        log.error("Infrastructure Node: %s is not found in the %s domain! Skip "
                  "flowrule install on this Node..." % (
                    infra.short_name, self.name))
        continue
      # Check the OF connection is alive
      dpid = self.controlAdapter.infra_to_dpid[infra.id]
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        log.warning(
          "Skipping INSTALL flowrule. Cause: connection for %s - DPID: %s is "
          "not found!" % (infra, dpid_to_str(dpid)))
        continue
      for port in infra.ports:
        for flowrule in port.flowrules:
          match = {}
          action = {}
          # if re.search(r';', flowrule.match):
          #   # multiple elements in match field
          #   in_port = re.sub(r'.*in_port=(.*);.*', r'\1', flowrule.match)
          # else:
          #   # single element in match field
          #   in_port = re.sub(r'.*in_port=(.*)', r'\1', flowrule.match)
          match['in_port'] = port.id
          # Check match fields - currently only vlan_id
          # TODO: add further match fields
          if re.search(r'TAG', flowrule.match):
            tag = re.sub(r'.*TAG=.*-(.*);?', r'\1', flowrule.match)
            match['vlan_id'] = tag

          if re.search(r';', flowrule.action):
            # multiple elements in action field
            out = re.sub(r'.*output=(.*);.*', r'\1', flowrule.action)
          else:
            # single element in action field
            out = re.sub(r'.*output=(.*)', r'\1', flowrule.action)
          action['out'] = out

          if re.search(r'TAG', flowrule.action):
            if re.search(r'UNTAG', flowrule.action):
              action['vlan_pop'] = True
            else:
              push_tag = re.sub(r'.*TAG=.*-(.*);?', r'\1', flowrule.action)
              action['vlan_push'] = push_tag

          self.controlAdapter.install_flowrule(infra.id, match=match,
                                               action=action)
