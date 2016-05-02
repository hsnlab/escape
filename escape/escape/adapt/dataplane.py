# Copyright 2016 Janos Czentye <czentye@tmit.bme.hu>
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
Domain Manager and Adapter class for dataplane project:
ESCAPEv2 used as a local orchestrator with resource information come from
CPU/hardware specialities
"""
import os

from escape import CONFIG, __version__
from escape.util.domain import *
from escape.util.misc import run_cmd


class DataplaneDomainManager(AbstractDomainManager):
  """
  Manager class to handle communication with internally emulated network.

  .. note::
    Uses :class:`InternalMininetAdapter` for managing the emulated network and
    :class:`InternalPOXAdapter` for controlling the network.
  """
  # DomainManager name
  name = "DATAPLANE"
  # Default domain name
  DEFAULT_DOMAIN_NAME = "DATAPLANE"
  # Set the local manager status
  IS_LOCAL_MANAGER = True

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, *args, **kwargs):
    """
    Init
    """
    log.debug("Create DataplaneDomainManager with domain name: %s" %
              domain_name)
    super(DataplaneDomainManager, self).__init__(domain_name=domain_name,
                                                 *args, **kwargs)
    # self.controlAdapter = None  # DomainAdapter for POX-InternalPOXAdapter
    self.topoAdapter = None  # DomainAdapter for Dataplane
    self.remoteAdapter = None  # REST management communication

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
    super(DataplaneDomainManager, self).init(configurator, **kwargs)
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
    # Init default NETCONF adapter
    self.remoteAdapter = configurator.load_component(
      component_name=AbstractESCAPEAdapter.TYPE_REMOTE,
      parent=self._adapters_cfg)
    # Init adapter for internal controller: POX
    # self.controlAdapter = configurator.load_component(
    #   component_name=AbstractESCAPEAdapter.TYPE_CONTROLLER,
    #   parent=self._adapters_cfg)
    log.debug("Set %s as the topology Adapter for %s" %
              (self.topoAdapter.__class__.__name__, self.domain_name))

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(DataplaneDomainManager, self).finit()
    # self.controlAdapter.finit()
    self.topoAdapter.finit()
    self.remoteAdapter.finit()

  # @property
  # def controller_name (self):
  #   return self.controlAdapter.task_name

  def install_nffg (self, nffg_part):
    """
    Install an :any:`NFFG` related to the dataplane domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :any:`NFFG`
    :return: installation was success or not
    :rtype: bool
    """
    log.info(">>> Install %s domain part..." % self.domain_name)
    try:
      # Mininet domain does not support NF migration directly -->
      # Remove unnecessary and moved NFs first
      # TODO
      # log.debug("Generated mapped NFFG:\n%s" % nffg_part.dump())
      return True
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
    # something went wrong ??
    return False


class DataplaneTopologyAdapter(AbstractESCAPEAdapter):
  """
  Adapter class to handle communication with Mininet domain.

  Implement VNF managing API using direct access to the
  :class:`mininet.net.Mininet` object.
  """
  # Events raised by this class
  _eventMixin_events = {DomainChangedEvent}
  name = "DATAPLANE-COMPUTE"
  type = AbstractESCAPEAdapter.TYPE_TOPOLOGY

  def __init__ (self, **kwargs):
    """
    Init.

    :param net: set pre-defined network (optional)
    :type net: :class:`ESCAPENetworkBridge`
    """
    # Call base constructors directly to avoid super() and MRO traps
    AbstractESCAPEAdapter.__init__(self, **kwargs)
    log.debug("Init DataplaneComputeCtrlAdapter - type: %s" % self.type)

  def check_domain_reachable (self):
    """
    Checker function for domain polling and first time domain detection.

    :return: the domain is detected or not
    :rtype: bool
    """
    # Direct access to IL's Mininet wrapper <-- Internal Domain
    return True

  def get_topology_resource (self):
    """
    Return with the topology description as an :any:`NFFG`.

    :return: the emulated topology description
    :rtype: :any:`NFFG`
    """
    # Assemble shell command
    cmd_hwloc2nffg = os.path.normpath(os.path.join(
      CONFIG.get_project_root_dir(), "hwloc2nffg/build/bin/hwloc2nffg"))
    # Run command
    raw_data = run_cmd(cmd_hwloc2nffg)
    # Basic validation
    if not raw_data.startswith('{'):
      if "not found" in raw_data:
        # hwloc2nffg binary not found
        raise RuntimeError(
          "hwloc2nffg binary was not found under the path: %s" % cmd_hwloc2nffg)
      elif "No such file" in raw_data:
        # Shared library not found
        raise RuntimeError(
          "dependent package of hwloc2nffg is missing: %s" % raw_data)
      else:
        # unexpected error
        raise RuntimeError(raw_data)
    # Parse raw data
    topo = NFFG.parse(raw_data)
    # Duplicate links for bidirectional connections
    topo.duplicate_static_links()
    # Rewrite infra domains
    return self.rewrite_domain(nffg=topo)


class DefaultDataplaneDomainAPI(object):
  """
  Define unified interface for managing Dataplane domains with REST-API.

  Follows the MixIn design pattern approach.
  """

  def ovsports (self):
    """
    """
    raise NotImplementedError("Not implemented yet!")

  def ovsflows (self):
    """
    """
    raise NotImplementedError("Not implemented yet!")

  def running (self):
    """
    """
    raise NotImplementedError("Not implemented yet!")

  def start (self, cmask=None, mem=None):
    """
    """
    raise NotImplementedError("Not implemented yet!")

  def stop (self, containerID=None):
    """
    """
    raise NotImplementedError("Not implemented yet!")


class DataplaneRESTAdapter(AbstractRESTAdapter, AbstractESCAPEAdapter,
                           DefaultDataplaneDomainAPI):
  """
  Implement the unified way to communicate with "Dataplane" domain which are
  using REST-API.
  """
  # Set custom header
  custom_headers = {
    'User-Agent': "ESCAPE/" + __version__,
    # XML-based Virtualizer format
    'Accept': "application/xml"
  }
  # Adapter name used in CONFIG and ControllerAdapter class
  name = "DATAPLANE-REST"
  # type of the Adapter class - use this name for searching Adapter config
  type = AbstractESCAPEAdapter.TYPE_MANAGEMENT

  def __init__ (self, url, prefix="", **kwargs):
    """
    Init.

    :param url: url of RESTful API
    :type url: str
    """
    AbstractRESTAdapter.__init__(self, base_url=url, prefix=prefix, **kwargs)
    AbstractESCAPEAdapter.__init__(self, **kwargs)
    log.debug("Init %s - type: %s, domain: %s, URL: %s" % (
      self.__class__.__name__, self.type, self.domain_name, url))

  def ovsflows (self):
    # TODO
    pass

  def start (self, cmask=None, mem=None):
    # TODO
    pass

  def ovsports (self):
    # TODO
    pass

  def running (self):
    # TODO
    pass

  def stop (self, containerID=None):
    # TODO
    pass

  def check_domain_reachable (self):
    """
    Checker function for domain polling. Check the remote domain agent is
    reachable.

    :return: the remote domain is detected or not
    :rtype: bool
    """
    return True

  def get_topology_resource (self):
    """
    Return with the topology description as an :any:`NFFG`.

    :return: the topology description of the remote domain
    :rtype: :any:`NFFG`
    """
    # This function should not be called by ESCAPE
    raise RuntimeError("DataplaneRESTAdapter does not support this function: "
                       "get_topology_resource()!")
