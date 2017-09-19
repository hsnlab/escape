# Copyright 2017 Janos Czentye
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
from escape.adapt.callback import CallbackManager
from escape.util.conversion import NFFGConverter
from escape.util.domain import *
from escape.util.misc import get_global_parameter, schedule_as_coop_task
from pox.lib.util import dpid_to_str


class GetLocalDomainViewEvent(Event):
  """
  Event for requesting the Global View (DoV).
  """
  pass


class AbstractHookEvent(Event):
  STATUS_OK = "OK"
  STATUS_ERROR = "ERROR"
  STATUS_TIMEOUT = "TIMEOUT"

  def __init__ (self, domain, status, callback=None):
    """

    :param domain: domain name
    :type domain: str
    :param status: callback result
    :type status: str
    :param callback: callback object
    :type callback: escape.adapt.callback.Callback
    """
    super(AbstractHookEvent, self).__init__()
    self.domain = domain
    self.status = status
    self.callback = callback

  def was_error (self):
    return self.status in (self.STATUS_ERROR, self.STATUS_TIMEOUT)


class EditConfigHookEvent(AbstractHookEvent):
  """
  Event class for handling callback caused by an edit-config install request.
  """
  pass


class InfoHookEvent(AbstractHookEvent):
  """
  Event class for handling callback caused by a recursive Info request.
  """
  pass


class ResetHookEvent(AbstractHookEvent):
  """
  Event class for handling callback caused by an edit-config reset request.
  """
  pass


class BasicDomainManager(AbstractDomainManager):
  """
  Simple Manager class to provide topology information read from file.

  .. note::
    Uses :class:`InternalPOXAdapter` for controlling the network.
  """
  # Domain name
  name = "SIMPLE-TOPO"
  # Default domain name
  DEFAULT_DOMAIN_NAME = "SIMPLE-TOPO"

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, *args, **kwargs):
    """
    Init.

    :param domain_name: the domain name
    :type domain_name: str
    :param args: optional param list
    :type args: list
    :param kwargs: optional keywords
    :type kwargs: dict
    :return: None
    """
    log.debug("Create SimpleTopologyManager with domain name: %s" % domain_name)
    super(BasicDomainManager, self).__init__(domain_name=domain_name, *args,
                                             **kwargs)
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
    super(BasicDomainManager, self).init(configurator, **kwargs)
    self.log.info(
      "DomainManager for %s domain has been initialized!" % self.domain_name)

  def initiate_adapters (self, configurator):
    """
    Init Adapters.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :return: None
    """
    # Init adapter for static domain topology
    self.topoAdapter = configurator.load_component(
      component_name=AbstractESCAPEAdapter.TYPE_TOPOLOGY,
      parent=self._adapters_cfg)

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(BasicDomainManager, self).finit()
    self.topoAdapter.finit()

  def install_nffg (self, nffg_part):
    """
    Install domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :class:`NFFG`
    :return: successful installation step: True
    :rtype: bool
    """
    self.log.debug("%s domain has received install_nffg invoke! "
                   % self.domain_name)
    if get_global_parameter(name='TEST_MODE'):
      self.topoAdapter.dump_to_file(nffg=nffg_part)
    else:
      self.log.debug("SimpleTopologyManager skip the step by default...")
    # Return with successful result by default
    return True

  def reset_domain (self):
    """
    Clear domain.

    :return: cleanup result
    :rtype: bool
    """
    self.clear_domain()

  def clear_domain (self):
    """
    Clear domain.

    :return: cleanup result
    :rtype: bool
    """
    self.log.debug("%s domain has received clear_domain invoke! "
                   "SimpleTopologyManager skip the step by default..."
                   % self.domain_name)


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
    Init.

    :param domain_name: the domain name
    :type domain_name: str
    :param args: optional param list
    :type args: list
    :param kwargs: optional keywords
    :type kwargs: dict
    :return: None
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
    self.log.info(
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
    """
    :return: Return with the adapter name
    :rtype: str
    """
    return self.controlAdapter.task_name

  def install_nffg (self, nffg_part):
    """
    Install an :class:`NFFG` related to the SDN domain.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :class:`NFFG`
    :return: installation was success or not
    :rtype: bool
    """
    self.log.info(">>> Install %s domain part..." % self.domain_name)
    try:
      result = (self._delete_flowrules(nffg_part=nffg_part),
                self._deploy_flowrules(nffg_part=nffg_part))
      return all(result)
    except:
      self.log.exception(
        "Got exception during NFFG installation into: %s!" % self.domain_name)
      return False

  def _delete_flowrules (self, nffg_part):
    """
    Delete all flowrules from the first (default) table of all infras.

    :param nffg_part: last mapped NFFG part
    :type nffg_part: :class:`NFFG`
    :return: deletion was successful or not
    :rtype: bool
    """
    self.log.debug("Removing flowrules...")
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
        self.log.warning("Missing DPID for Infra(id: %s)! "
                         "Skip deletion of flowrules" % e)
        result = False
        continue
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        self.log.warning(
          "Skipping DELETE flowrules! Cause: connection for %s - "
          "DPID: %s is not found!" % (infra, dpid_to_str(dpid)))
        result = False
        continue
      self.controlAdapter.delete_flowrules(infra.id)
    self.log.debug("Flowrule deletion result: %s" %
                   ("SUCCESS" if result else "FAILURE"))
    return result

  def _deploy_flowrules (self, nffg_part):
    """
    Install the flowrules given in the NFFG.

    If a flowrule is already defined it will be updated.

    :param nffg_part: NF-FG need to be deployed
    :type nffg_part: :class:`NFFG`
    :return: deploy was successful or not
    :rtype: bool
    """
    self.log.debug("Deploy flowrules into the domain: %s..." % self.domain_name)
    result = True
    # Remove unnecessary SG and Requirement links to avoid mess up port
    # definition of NFs
    nffg_part.clear_links(NFFG.TYPE_LINK_SG)
    nffg_part.clear_links(NFFG.TYPE_LINK_REQUIREMENT)
    # Get physical topology description from POX adapter
    topo = self.topoAdapter.get_topology_resource()
    if topo is None:
      self.log.warning("Missing topology description from %s domain! "
                       "Skip deploying flowrules..." % self.domain_name)
      return False
    # Iter through the container INFRAs in the given mapped NFFG part
    for infra in nffg_part.infras:
      if infra.infra_type not in (
         NFFG.TYPE_INFRA_EE, NFFG.TYPE_INFRA_STATIC_EE,
         NFFG.TYPE_INFRA_SDN_SW):
        self.log.debug("Infrastructure Node: %s (type: %s) is not Switch or "
                       "Container type! Continue to next Node..." %
                       (infra.id, infra.infra_type))
        continue
      # If the actual INFRA isn't in the topology(NFFG) of this domain -> skip
      if infra.id not in (n.id for n in topo.infras):
        self.log.error("Infrastructure Node: %s is not found in the %s domain! "
                       "Skip flowrule install on this Node..." %
                       (infra.id, self.domain_name))
        result = False
        continue
      # Check the OF connection is alive
      try:
        dpid = self.controlAdapter.infra_to_dpid[infra.id]
      except KeyError as e:
        self.log.warning("Missing DPID for Infra(id: %s)! "
                         "Skip deploying flowrules for Infra" % e)
        result = False
        continue
      if self.controlAdapter.openflow.getConnection(dpid) is None:
        self.log.warning(
          "Skipping INSTALL flowrule! Cause: connection for %s - "
          "DPID: %s is not found!" % (infra, dpid_to_str(dpid)))
        result = False
        continue
      for port in infra.ports:
        for flowrule in port.flowrules:
          try:
            match = NFFGConverter.field_splitter(type="MATCH",
                                                 field=flowrule.match)
            if "in_port" not in match:
              self.log.warning("Missing in_port field from match field! "
                               "Using container port number...")
              match["in_port"] = port.id
            action = NFFGConverter.field_splitter(type="ACTION",
                                                  field=flowrule.action)
          except RuntimeError as e:
            self.log.warning("Wrong format in match/action field: %s" % e)
            result = False
            continue
          self.log.debug("Assemble OpenFlow flowrule from: %s" % flowrule)
          self.controlAdapter.install_flowrule(infra.id, match=match,
                                               action=action)
    self.log.info("Flowrule deploy result: %s" %
                  ("SUCCESS" if result else "FAILURE"))
    return result

  def clear_domain (self):
    """
    Delete all flowrule in the registered SDN/OF switches.

    :return: cleanup result
    :rtype: bool
    """
    self.log.debug(
      "Clear all flowrules from switches registered in SDN domain...")
    # Delete all flowrules in the Infra nodes defined the topology file.
    sdn_topo = self.topoAdapter.get_topology_resource()
    if sdn_topo is None:
      self.log.warning("SDN topology is missing! Skip domain resetting...")
      return
    # Remove flowrules
    return self._delete_flowrules(nffg_part=sdn_topo)

  def reset_domain (self):
    """
    Reset domain to the fisrt received state.

    :return: None
    """
    self.clear_domain()


class UnifyDomainManager(AbstractRemoteDomainManager):
  """
  Manager class for unified handling of different domains using the Unify
  domain.

  The communication between ESCAPEv2 and domain agent relies on pre-defined
  REST-API functions and the Virtualizer format.

  .. note::
    Uses :class:`UnifyDomainAdapter` for communicate with the remote domain.
  """
  # Events raised by this class
  _eventMixin_events = {DomainChangedEvent, EditConfigHookEvent, InfoHookEvent,
                        ResetHookEvent}
  # DomainManager name
  name = "UNIFY"
  # Default domain name - Must override child classes to define the domain
  DEFAULT_DOMAIN_NAME = "UNIFY"
  CALLBACK_CONFIG_NAME = "CALLBACK"
  CALLBACK_ENABLED_NAME = "enabled"
  CALLBACK_HOST = "explicit_address"
  CALLBACK_PORT = "explicit_port"
  CALLBACK_EXPLICIT_DOMAIN_UPDATE = "explicit_update"
  CALLBACK_TYPE_INSTALL = "INSTALL"
  CALLBACK_TYPE_INFO = "INFO"
  CALLBACK_TYPE_RESET = "RESET"

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, *args, **kwargs):
    """
    Init.

    :param domain_name: the domain name
    :type domain_name: str
    :param args: optional param list
    :type args: list
    :param kwargs: optional keywords
    :type kwargs: dict
    :return: None
    """
    log.debug("Create UnifyDomainManager with domain name: %s" % domain_name)
    super(UnifyDomainManager, self).__init__(domain_name=domain_name, *args,
                                             **kwargs)
    self.callback_manager = None
    """:type: CallbackManager"""
    self.__reset_mode = False
    self.__last_success_state = None

  def enable_reset_mode (self):
    """
    Set RESET mode.

    :return: None
    """
    self.log.debug("Enable reset mode for: %s" % self)
    self.__reset_mode = True

  def disable_reset_mode (self):
    """
    Disable reset mode.

    :return: None
    """
    self.log.debug("Disable reset mode for: %s" % self)
    self.__reset_mode = False

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
    cb_cfg = self._adapters_cfg.get(self.CALLBACK_CONFIG_NAME, None)
    if cb_cfg and cb_cfg.get(self.CALLBACK_ENABLED_NAME, None):
      self.callback_manager = CallbackManager.initialize_on_demand()
      explicit_host = cb_cfg.get(self.CALLBACK_HOST)
      explicit_port = cb_cfg.get(self.CALLBACK_PORT)
      if explicit_host or explicit_port:
        self.callback_manager.register_url(domain=self.domain_name,
                                           host=explicit_host,
                                           port=explicit_port)
    self.log.info("DomainManager for %s domain has been initialized!" %
                  self.domain_name)

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
    if self.callback_manager:
      try:
        self.callback_manager.shutdown()
      except KeyboardInterrupt:
        pass

  def get_last_request (self):
    """
    :return: Return with the last sent request.
    :rtype: :class:`Virtualizer` or :class:`NFFG`
    """
    return self.topoAdapter.last_request

  def _setup_callback (self, hook, type, req_id, msg_id=None, data=None,
                       timeout=None):
    """
    Initiate and register callback manager for callbacks.

    :param hook: hook function
    :type hook: callable
    :param type: callback type
    :type type: str
    :param req_id: original request ID (optional)
    :type req_id: str or int
    :param data: optional callback data (optional)
    :type data: object
    :param timeout: explicit timeout value (optional)
    :type timeout: float
    :return: created callback object
    :rtype: :class:`Callback`
    """
    if self.callback_manager is not None:
      if msg_id is None:
        msg_id = self.topoAdapter.get_last_message_id()
      if msg_id is None:
        log.warning("message-id is missing from 'edit-config' response "
                    "for callback registration!")
        return
      self.log.debug("Used message-id for callback: %s"
                     % msg_id)
      return self.callback_manager.subscribe_callback(hook=hook,
                                                      cb_id=msg_id,
                                                      domain=self.domain_name,
                                                      req_id=req_id,
                                                      type=type,
                                                      data=data,
                                                      timeout=timeout)

  def request_info_from_domain (self, info_part, req_id):
    """
    Send Info request to domain and setup callback for response.

    :param info_part: related part of original Info request
    :type info_part: :class:`Info`
    :param req_id: request ID
    :type req_id: str or int
    :return: status if the RPC call was success
    :rtype: bool
    """
    self.log.debug("Request monitoring info from domain: %s" % self.domain_name)
    try:
      request_params = {"message_id": "info-%s" % req_id}
      if self.callback_manager is not None:
        cb_url = self.callback_manager.get_url(domain=self.domain_name)
        log.debug("Set callback URL: %s" % cb_url)
        request_params["callback"] = cb_url
        self._setup_callback(hook=self.info_hook,
                             req_id=req_id,
                             msg_id=request_params.get('message_id'),
                             type=self.CALLBACK_TYPE_INFO)
      status = self.topoAdapter.info(info_part, **request_params)
      return True if status is not None else False
    except:
      self.log.exception("Got exception during NFFG installation into: %s." %
                         self.domain_name)
      return False

  def install_nffg (self, nffg_part):
    """
    Install :class:`NFFG` part into the domain using the specific REST-API
    function and Virtualizer format.

    :param nffg_part: domain related part of the mapped :class:`NFFG`
    :type nffg_part: :class:`NFFG`
    :return: status if the installation was success
    :rtype: bool
    """
    # if nffg_part.is_bare():
    #   self.log.info(">>> Splitted part is a bare NFFG! Skip domain deploy...")
    #   return True
    self.log.info(">>> Install %s domain part..." % self.domain_name)
    try:
      log.debug("Request and store the most recent domain topology....")
      topo = self.topoAdapter.get_config()
      if topo:
        self.__last_success_state = topo
        log.log(VERBOSE,
                "Last successful state:\n%s" % self.__last_success_state.xml())
      request_params = {"diff": self._diff,
                        "message_id": "edit-config-%s" % nffg_part.id}
      cb = None
      if self.callback_manager is not None:
        cb_url = self.callback_manager.get_url(domain=self.domain_name)
        log.debug("Set callback URL: %s" % cb_url)
        request_params["callback"] = cb_url
        cb = self._setup_callback(hook=self.edit_config_hook,
                                  req_id=nffg_part.id,
                                  msg_id=request_params.get('message_id'),
                                  type=self.CALLBACK_TYPE_INSTALL,
                                  data=nffg_part)
      status = self.topoAdapter.edit_config(nffg_part, **request_params)
      if status and self.callback_manager and cb:
        self.callback_manager.unsubscribe_callback(cb_id=cb.callback_id,
                                                   domain=self.domain_name)
        return False
      else:
        return True
    except:
      self.log.exception("Got exception during NFFG installation into: %s." %
                         self.domain_name)
      return False

  def rollback_install (self, request_id):
    """
    Perform the rollback by sending the backup state to domain and setup
    callback handler if needed.

    :param request_id: request ID
    :type request_id: str or int
    :return: status if the Info call was success
    :rtype: bool
    """
    self.log.info(">>> Rollback domain: %s" % self.domain_name)
    self.enable_reset_mode()
    try:
      log.debug("Request for the most recent domain topology....")
      self.topoAdapter.get_config()
      reset_state = self.__last_success_state
      log.log(VERBOSE,
              "Full RESET topology:\n%s" % reset_state)
      request_params = {"diff": self._diff,
                        "message_id": "rollback-%s" % request_id}
      cb = None
      if self.callback_manager is not None:
        cb_url = self.callback_manager.get_url(domain=self.domain_name)
        log.debug("Set callback URL: %s" % cb_url)
        request_params["callback"] = cb_url
        cb = self._setup_callback(hook=self.edit_config_hook,
                                  req_id=request_id,
                                  msg_id=request_params.get('message_id'),
                                  type=self.CALLBACK_TYPE_RESET)
      status = self.topoAdapter.edit_config(reset_state, **request_params)
      if status and self.callback_manager:
        self.callback_manager.unsubscribe_callback(cb_id=cb.callback_id,
                                                   domain=self.domain_name)
        self.disable_reset_mode()
        return False
      else:
        return True
    except:
      self.log.exception("Got exception during NFFG installation into: %s." %
                         self.domain_name)
      return False

  @staticmethod
  def _strip_virtualizer_topology (virtualizer):
    """
    Remove NFs and Flowrules from given topology.

    :param virtualizer: topology
    :type virtualizer: :class:`Virtualizer`
    :return: stripped Virtualizer
    :rtype: :class:`Virtualizer`
    """
    for node in virtualizer.nodes:
      # Remove NFs
      node.NF_instances.node._data.clear()
      # Remove flowrules
      node.flowtable.flowentry._data.clear()
    return virtualizer

  def clear_domain (self):
    """
    Reset remote domain based on the original (first response) topology.

    :return: cleanup result
    :rtype: bool
    """
    if not self._detected:
      self.log.warning("Domain: %s is not detected! Skip domain cleanup..."
                       % self.domain_name)
      return True
    empty_cfg = self.topoAdapter.get_original_topology()
    if empty_cfg is None:
      self.log.warning("Missing original topology in %s domain! "
                       "Skip domain resetting..." % self.domain_name)
      return
    self.log.info("Clear %s domain based on original topology description..." %
                  self.domain_name)
    # If poll is enabled then the last requested topo is most likely the most
    # recent topo else request the topology for the most recent one and compute
    # diff if it is necessary
    if not self.polling and self._diff:
      self.log.debug("Polling is disabled. Requesting the most recent topology "
                     "from domain: %s for domain clearing..." %
                     self.domain_name)
      recent_topo = self.topoAdapter.get_config()
      if recent_topo is not None:
        self.log.debug("Strip original topology...")
        empty_cfg = self._strip_virtualizer_topology(virtualizer=empty_cfg)
        self.log.debug("Explicitly calculating diff for domain clearing...")
        diff = recent_topo.diff(empty_cfg)
        status = self.topoAdapter.edit_config(data=diff, diff=False)
      else:
        self.log.error("Skip domain resetting: %s! "
                       "Requested topology is missing!" % self.domain_name)
        return False
    else:
      status = self.topoAdapter.edit_config(data=empty_cfg, diff=self._diff)
    return True if status is not None else False

  def reset_domain (self):
    """
    Reset remote domain based on the original (first response) topology.

    :return: cleanup result
    :rtype: bool
    """
    if not self._detected:
      self.log.warning("Domain: %s is not detected! Skip domain reset..."
                       % self.domain_name)
      return True
    empty_cfg = self.topoAdapter.get_original_topology()
    if empty_cfg is None:
      self.log.warning("Missing original topology in %s domain! "
                       "Skip domain resetting..." % self.domain_name)
      return
    self.log.info("Reset %s domain based on original topology description..." %
                  self.domain_name)
    # If poll is enabled then the last requested topo is most likely the most
    # recent topo else request the topology for the most recent one and compute
    # diff if it is necessary
    if not self.polling and self._diff:
      self.log.debug("Polling is disabled. Requesting the most recent topology "
                     "from domain: %s for domain clearing..." %
                     self.domain_name)
      recent_topo = self.topoAdapter.get_config()
      if recent_topo is not None:
        self.log.debug("Explicitly calculating diff for domain clearing...")
        diff = recent_topo.diff(empty_cfg)
        status = self.topoAdapter.edit_config(data=diff, diff=False)
      else:
        self.log.error("Skip domain resetting: %s! "
                       "Requested topology is missing!" % self.domain_name)
        return False
    else:
      status = self.topoAdapter.edit_config(data=empty_cfg, diff=self._diff)
    return True if status is not None else False

  @schedule_as_coop_task
  def edit_config_hook (self, callback):
    """
    Handle callback caused by an edit-config install call and process
    callback data.

    :param callback: callback object
    :type callback: :class:`Callback`
    :return: None
    """
    self.log.debug("Callback hook (%s) invoked with callback id: %s" %
                   (callback.type, callback.callback_id))
    self.callback_manager.unsubscribe_callback(cb_id=callback.callback_id,
                                               domain=self.domain_name)
    if callback.type == self.CALLBACK_TYPE_INSTALL:
      event_class = EditConfigHookEvent
    elif callback.type == self.CALLBACK_TYPE_RESET:
      event_class = ResetHookEvent
    else:
      log.error("Unexpected callback type: %s" % callback.type)
      return
    if self.__reset_mode:
      if callback.type != self.CALLBACK_TYPE_RESET:
        log.debug("RESET mode is enabled! Skip %s" % callback.short())
        return
      else:
        self.disable_reset_mode()
    # Process result code
    if callback.result_code == 0:
      self.log.warning("Registered %scallback for request: %s, domain: %s "
                       "exceeded timeout(%s)!" % (
                         "RESET " if self.__reset_mode else "",
                         callback.callback_id, self.domain_name,
                         self.callback_manager.wait_timeout))
      self.raiseEventNoErrors(event=event_class,
                              domain=self.domain_name,
                              status=event_class.STATUS_TIMEOUT,
                              callback=callback)
      return
    elif 300 <= callback.result_code or callback.result_code is None:
      self.log.error("Received %scallback with error result from domain: %s" % (
        "RESET " if self.__reset_mode else "", self.domain_name))
      self.raiseEventNoErrors(event=event_class,
                              domain=self.domain_name,
                              status=event_class.STATUS_ERROR,
                              callback=callback)
      return
    else:
      self.log.info("Received %scallback with success result from domain: %s"
                    % ("RESET " if self.__reset_mode else "", self.domain_name))
    # Get topology for domain update
    if self._adapters_cfg.get(self.CALLBACK_CONFIG_NAME, {}).get(
       self.CALLBACK_EXPLICIT_DOMAIN_UPDATE, False):
      self.log.debug("Request updated topology from domain...")
      callback.data = self.topoAdapter.get_topology_resource()
    else:
      self.log.debug("Use splitted NFFG part to update DoV...")
    self.raiseEventNoErrors(event=event_class,
                            domain=self.domain_name,
                            status=event_class.STATUS_OK,
                            callback=callback)
    self.log.debug("Callback hook (edit-config) ended with callback id: %s" %
                   callback.callback_id)

  @schedule_as_coop_task
  def info_hook (self, callback):
    """
    Handle callback caused by an Info call and process callback data.

    :param callback: callback object
    :type callback: :class:`Callback`
    :return: None
    """
    self.log.debug("Callback hook (%s) invoked with callback id: %s" %
                   (callback.type, callback.callback_id))
    self.callback_manager.unsubscribe_callback(cb_id=callback.callback_id,
                                               domain=self.domain_name)
    if callback.result_code == 0:
      self.log.warning(
        "Registered callback for request: %s, domain: %s exceeded timeout(%s)!"
        % (callback.callback_id, self.domain_name,
           self.callback_manager.wait_timeout))
      self.raiseEventNoErrors(InfoHookEvent,
                              domain=self.domain_name,
                              status=EditConfigHookEvent.STATUS_TIMEOUT,
                              callback=callback)
      return
    elif 300 <= callback.result_code or callback.result_code is None:
      self.log.warning("Received callback with error result from domain: %s"
                       % self.domain_name)
      self.raiseEventNoErrors(InfoHookEvent,
                              domain=self.domain_name,
                              status=EditConfigHookEvent.STATUS_ERROR,
                              callback=callback)
    else:
      self.log.info("Received callback with success result from domain: %s"
                    % self.domain_name)
      self.raiseEventNoErrors(InfoHookEvent,
                              domain=self.domain_name,
                              status=EditConfigHookEvent.STATUS_OK,
                              callback=callback)
    self.log.debug("Callback hook (info) ended with callback id: %s" %
                   callback.callback_id)


class ExternalDomainManager(AbstractRemoteDomainManager):
  """
  Main Abstract class for handling external domains.

  This base class gives the capability of detecting external domains through
  various ways and initiate dedicated DomainManagers to that domains on-the-fly.

  This class has also the special roles of accessing/notifying the container
  class, a.k.a. the ComponentConfigurator and the global domain view,
  a.k.a. the DoV through events.
  """
  # Events raised by this class
  _eventMixin_events = {DomainChangedEvent, GetLocalDomainViewEvent}
  # DomainManager name
  name = "EXTERNAL"
  # Default domain name
  DEFAULT_DOMAIN_NAME = "EXTERNAL"
  # Set External Manager status
  IS_EXTERNAL_MANAGER = True

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, *args, **kwargs):
    """
    Init.

    :param domain_name: the domain name
    :type domain_name: str
    :param args: optional param list
    :type args: list
    :param kwargs: optional keywords
    :type kwargs: dict
    :return: None
    """
    super(ExternalDomainManager, self).__init__(domain_name=domain_name, *args,
                                                **kwargs)

  def init (self, configurator, **kwargs):
    """
    Initialize the ExternalDomainManager.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :param kwargs: optional parameters
    :type kwargs: dict
    :return: None
    """
    super(ExternalDomainManager, self).init(configurator=configurator, **kwargs)

  def initiate_adapters (self, configurator):
    """
    Initiate Adapters for DomainManager.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :return: None
    """
    raise NotImplementedError(
      "Managers must override this function to initiate Adapters!")

  def finit (self):
    """
    Stop polling and release dependent components.

    :return: None
    """
    super(ExternalDomainManager, self).finit()

  def reset_domain (self):
    """
    External DomainManager should not receive cleanup NFFGs.
    Return with success cleanup result by default for avoiding running errors.

    :return: cleanup success
    :rtype: bool
    """
    self.log.warning("External DomainManager: %s received reset call! "
                     "Skip processing..." % self.name)
    return True

  def clear_domain (self):
    """
    External DomainManager should not receive cleanup NFFGs.
    Return with success cleanup result by default for avoiding running errors.

    :return: cleanup success
    :rtype: bool
    """
    self.log.warning("External DomainManager: %s received clear call! "
                     "Skip processing..." % self.name)
    return True

  def install_nffg (self, nffg_part):
    """
    External DomainManager should not receive install NFFGs.
    Return with success install result by default for avoiding running errors.

    :return: installation success
    :rtype: bool
    """
    self.log.warning("External DomainManager: %s received install call! "
                     "Skip processing..." % self.name)
    return True


class BGPLSBasedExternalDomainManager(ExternalDomainManager):
  """
  External DomainManager using BGP-LS TM component to detect external domains.
  """
  # DomainManager name
  name = "BGP-LS-SPEAKER"
  # Default domain name
  DEFAULT_DOMAIN_NAME = "EXTERNAL"
  # Default DomainManager config
  DEFAULT_DOMAIN_MANAGER_CFG = "EXTERNAL"

  def __init__ (self, domain_name=DEFAULT_DOMAIN_NAME, bgp_domain_id=None,
                prototype=None, *args, **kwargs):
    """
    Init.

    :param domain_name: the domain name
    :type domain_name: str
    :param bgp_domain_id: domain name used for BGP-LS speaker
    :type bgp_domain_id: str
    :param prototype: DomainManager name initialized for new detected domains
    :type prototype: str
    :param args: optional param list
    :type args: list
    :param kwargs: optional keywords
    :type kwargs: dict
    :return: None
    """
    log.debug("Create BGP-LS-based ExternalDomainManager with domain name: %s, "
              "BGP domain ID: %s" % (domain_name, bgp_domain_id))
    super(BGPLSBasedExternalDomainManager, self).__init__(
      domain_name=domain_name, *args, **kwargs)
    # Own BGP domain ID
    self.bgp_domain_id = bgp_domain_id
    if prototype:
      self.log.debug(
        "Set default DomainManager config: %s for external domains!" %
        prototype)
      self.prototype = prototype
    else:
      self.log.warning("No default DomainManager was given! "
                       "Using default config: %s"
                       % self.DEFAULT_DOMAIN_MANAGER_CFG)
      self.prototype = self.DEFAULT_DOMAIN_MANAGER_CFG
    # Keep tracking the IDs of the discovered external domains
    self.managed_domain_ids = set()

  def init (self, configurator, **kwargs):
    """
    Initialize the ExternalDomainManager.

    :param configurator: component configurator for configuring adapters
    :type configurator: :any:`ComponentConfigurator`
    :param kwargs: optional parameters
    :type kwargs: dict
    :return: Nones
    """
    super(BGPLSBasedExternalDomainManager, self).init(configurator, **kwargs)
    self.log.debug("BGP-LS-based ExternalDomainManager has been initialized!")

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
    super(BGPLSBasedExternalDomainManager, self).finit()
    self.topoAdapter.finit()
