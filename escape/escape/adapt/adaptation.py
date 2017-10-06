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
Contains classes relevant to the main adaptation function of the Controller
Adaptation Sublayer
"""
import pprint
import time
import urlparse
import weakref

from escape.adapt import log as log
from escape.adapt.adapters import UnifyRESTAdapter
from escape.adapt.managers import UnifyDomainManager, BaseResultEvent
from escape.adapt.virtualization import DomainVirtualizer
from escape.nffg_lib.nffg import NFFG, NFFGToolBox
from escape.util.com_logger import MessageDumper
from escape.util.config import CONFIG
from escape.util.config import ConfigurationError
from escape.util.conversion import NFFGConverter
from escape.util.domain import DomainChangedEvent, AbstractDomainManager, \
  AbstractRemoteDomainManager
from escape.util.misc import notify_remote_visualizer, VERBOSE
from escape.util.stat import stats
from escape.util.virtualizer_helper import get_nfs_from_info, \
  strip_info_by_nfs, get_bb_nf_from_path
from pox.lib.recoco import Timer
from virtualizer_info import Info


class InstallationFinishedEvent(BaseResultEvent):
  """
  Event for signalling end of mapping process.
  """

  def __init__ (self, id, result):
    """
    Init.

    :param result: result of the installation
    :type: result: str
    """
    super(InstallationFinishedEvent, self).__init__()
    self.id = id
    self.result = result
    stats.add_measurement_end_entry(type=stats.TYPE_DEPLOY,
                                    info=log.name)

  @classmethod
  def get_result_from_status (cls, deploy_status):
    """
    Convert deploy status to overall result.

    :param deploy_status: deploy status object
    :type deploy_status: :any:`DomainRequestStatus`
    :return: overall service status
    :type: str
    """
    if deploy_status.success:
      return cls.DEPLOYED
    elif deploy_status.still_pending:
      return cls.IN_PROGRESS
    elif deploy_status.failed:
      return cls.DEPLOY_ERROR
    elif deploy_status.reset_failed:
      return cls.RESET_ERROR
    elif deploy_status.reset:
      return cls.RESET
    else:
      return cls.UNKNOWN


class InfoRequestFinishedEvent(BaseResultEvent):
  """
  Event for signalling end of Info request processing.
  """

  def __init__ (self, result, status=None):
    """
    Init.

    :param result: overall result
    :type result: str
    :param status: deploy status
    :type status: :any:`DomainRequestStatus`
    """
    super(InfoRequestFinishedEvent, self).__init__()
    self.result = result
    self.status = status

  @classmethod
  def get_result_from_status (cls, req_status):
    """
    Convert request status to overall result.

    :param req_status: deploy status
    :type req_status: :any:`DomainRequestStatus`
    :return: overall result
    :rtype: str
    """
    if req_status.success:
      return cls.SUCCESS
    elif req_status.still_pending:
      return cls.IN_PROGRESS
    elif req_status.failed:
      return cls.ERROR
    else:
      return cls.UNKNOWN


class ComponentConfigurator(object):
  """
  Initialize, configure and store DomainManager objects.
  Use global config to create managers and adapters.

  Follows Component Configurator design pattern.
  """

  def __init__ (self, ca, lazy_load=True):
    """
    For domain adapters the configurator checks the CONFIG first.

    .. warning::
      Adapter classes must be subclass of AbstractESCAPEAdapter!

    .. note::
      Arbitrary domain adapters is searched in
      :mod:`escape.adapt.domain_adapters`

    :param ca: ControllerAdapter instance
    :type ca: :any:`ControllerAdapter`
    :param lazy_load: load adapters only at first reference (default: True)
    :type lazy_load: bool
    """
    log.debug("Init DomainConfigurator - lazy load: %s" % lazy_load)
    super(ComponentConfigurator, self).__init__()
    self.__repository = dict()
    self._lazy_load = lazy_load
    self._ca = ca
    if not lazy_load:
      # Initiate adapters from CONFIG
      self.load_default_mgrs()

  @property
  def components (self):
    """
    Return the dict of initiated Domain managers.

    :return: container of initiated DomainManagers
    :rtype: dict
    """
    return self.__repository

  @property
  def domains (self):
    """
    Return the list of domain_names which have been managed by DomainManagers.

    :return: list of already managed domains
    :rtype: list
    """
    return [mgr.domain_name for mgr in self.__repository.itervalues()]

  @property
  def initiated (self):
    return self.__repository.iterkeys()

  def __len__ (self):
    """
    Return the number of initiated components.

    :return: number of initiated components:
    :rtype: int
    """
    return len(self.__repository)

  def __iter__ (self):
    """
    Return with an iterator over the (name, DomainManager) items.
    """
    return self.__repository.iteritems()

  def __getitem__ (self, item):
    """
    Return with the DomainManager given by name: ``item``.

    :param item: component name
    :type item: str
    :return: component
    :rtype: :any:`AbstractDomainManager`
    """
    return self.get_mgr(item)

  ##############################################################################
  # General DomainManager handling functions: create/start/stop/get
  ##############################################################################

  def get_mgr (self, name):
    """
    Return the DomainManager with given name and create+start if needed.

    :param name: name of domain manager
    :type name: str
    :return: None
    """
    try:
      return self.__repository[name]
    except KeyError:
      if self._lazy_load:
        return self.start_mgr(name)
      else:
        raise AttributeError(
          "No component is registered with the name: %s" % name)

  def start_mgr (self, name, mgr_params=None, autostart=True):
    """
    Create, initialize and start a DomainManager with given name and start
    the manager by default.

    :param name: name of domain manager
    :type name: str
    :param mgr_params: mgr parameters
    :type mgr_params: dict
    :param autostart: also start the domain manager (default: True)
    :type autostart: bool
    :return: domain manager
    :rtype: :any:`AbstractDomainManager`
    """
    # If not started
    if not self.is_started(name):
      # Load from CONFIG
      mgr = self.load_component(name, params=mgr_params)
      if mgr is not None:
        # Call init - give self for the DomainManager to initiate the
        # necessary DomainAdapters itself
        mgr.init(self)
        # Autostart if needed
        if autostart:
          mgr.run()
        # Save into repository
        log.debug("Register DomainManager: %s into repository..." % name)
        self.__repository[name] = mgr
    else:
      log.warning("%s domain component has been already started! Skip "
                  "reinitialization..." % name)
    # Return with manager
    return self.__repository[name]

  def register_mgr (self, name, mgr, autostart=False):
    """
    Initialize the given manager object and with init() call and store it in
    the ComponentConfigurator with the given name.

    :param name: name of the component, must be unique
    :type name: str
    :param mgr: created DomainManager object
    :type mgr: :any:`AbstractDomainManager`
    :param autostart: also start the DomainManager (default: False)
    :type autostart: bool
    :return: None
    """
    if self.is_started(name=name):
      log.warning("DomainManager with name: %s has already exist! Skip init...")
      return
    # Call init - give self for the DomainManager to initiate the
    # necessary DomainAdapters itself
    mgr.init(self)
    # Autostart if needed
    if autostart:
      mgr.run()
    # Save into repository
    self.__repository[name] = mgr

  def stop_mgr (self, name):
    """
    Stop DomainManager with given name and remove from the
    repository also.

    :param name: name of domain manager
    :type name: str
    :return: None
    """
    # If started
    if self.is_started(name):
      # Call finalize
      self.__repository[name].finit()
    else:
      log.warning(
        "Missing domain component: %s! Skipping stop task..." % name)

  def remove_mgr (self, name):
    """
    Stop and derefer a DomainManager with given name and remove from the
    repository also.

    :param name: name of domain manager
    :type name: str
    :return: None
    """
    # If started
    if self.is_started(name):
      # Call finalize
      self.__repository[name].finit()
      # Remove from repository
      log.debug("Remove DomainManager: %s from repository..." % name)
      del self.__repository[name]
    else:
      log.warning(
        "Missing domain component: %s! Skipping stop task..." % name)

  def is_started (self, name):
    """
    Return with the value the given domain manager is started or not.

    :param name: name of domain manager
    :type name: str
    :return: is loaded or not
    :rtype: bool
    """
    return name in self.__repository

  def get_component_by_domain (self, domain_name):
    """
    Return with the initiated Domain Manager configured with the given
    domain_name.

    :param domain_name: name of the domain used in :class:`NFFG` descriptions
    :type domain_name: str
    :return: the initiated domain Manager
    :rtype: AbstractDomainManager
    """
    for component in self.__repository.itervalues():
      if component.domain_name == domain_name:
        return component

  def get_component_name_by_domain (self, domain_name):
    """
    Return with the initiated Domain Manager name configured with the given
    domain_name.

    :param domain_name: name of the domain used in :class:`NFFG` descriptions
    :type domain_name: str
    :return: the initiated domain Manager name
    :rtype: str
    """
    for name, component in self.__repository.iteritems():
      if component.domain_name == domain_name:
        return name

  ##############################################################################
  # High-level configuration-related functions
  ##############################################################################

  def load_component (self, component_name, params=None, parent=None):
    """
    Load given component (DomainAdapter/DomainManager) from config.
    Initiate the given component class, pass the additional attributes,
    register the event listeners and return with the newly created object.

    :param component_name: component's config name
    :type component_name: str
    :param params: component parameters
    :type params: dict
    :param parent: define the parent of the actual component's configuration
    :type parent: dict
    :return: initiated component
    :rtype: :any:`AbstractESCAPEAdapter` or :any:`AbstractDomainManager`
    """
    try:
      # Get component class
      component_class = CONFIG.get_component(component=component_name,
                                             parent=parent)
      # If it's found
      if component_class is not None:
        # Get optional parameters of this component
        if not params:
          params = CONFIG.get_component_params(component=component_name,
                                               parent=parent)
        # Initialize component
        component = component_class(**params)
        # Set up listeners for e.g. DomainChangedEvents
        component.addListeners(self._ca)
        # Set up listeners for DeployNFFGEvent
        component.addListeners(self._ca._layer_API)
        # Return the newly created object
        return component
      else:
        log.error("Configuration of '%s' is missing. Skip initialization!" %
                  component_name)
        raise ConfigurationError("Missing component configuration!")
    except TypeError as e:
      if "takes at least" in e.message:
        log.error("Mandatory configuration field is missing from:\n%s" %
                  pprint.pformat(params))
      raise
    except AttributeError:
      log.error("%s is not found. Skip component initialization!" %
                component_name)
      raise
    except ImportError:
      log.error("Could not import module: %s. Skip component initialization!" %
                component_name)
      raise

  def load_default_mgrs (self):
    """
    Initiate and start default DomainManagers defined in CONFIG.

    :return: None
    """
    log.info("Initialize additional DomainManagers from config...")
    # very dummy initialization
    enabled_mgrs = CONFIG.get_managers()
    if not enabled_mgrs:
      log.info("No DomainManager has been configured!")
      return
    for mgr_name in enabled_mgrs:
      # Get manager parameters from config
      mgr_cfg = CONFIG.get_component_params(component=mgr_name)
      if 'domain_name' in mgr_cfg:
        if mgr_cfg['domain_name'] in self.domains:
          log.warning("Domain name collision! Domain Manager: %s has already "
                      "initiated with the domain name: %s" % (
                        self.get_component_by_domain(
                          domain_name=mgr_cfg['domain_name']),
                        mgr_cfg['domain_name']))
      else:
        # If no domain name was given, use the manager config name by default
        mgr_cfg['domain_name'] = mgr_name
      # Get manager class
      mgr_class = CONFIG.get_component(component=mgr_name)
      if mgr_class is None:
        log.fatal("Missing DomainManager config: %s" % mgr_name)
        raise ConfigurationError(
          "Missing configuration for added DomainManager: %s" % mgr_name)
      if mgr_class.IS_INTERNAL_MANAGER:
        loaded_local_mgr = [name for name, mgr in self.__repository.iteritems()
                            if mgr.IS_INTERNAL_MANAGER]
        if loaded_local_mgr:
          log.warning("A local DomainManager has already been initiated with "
                      "the name: %s! Skip initiating DomainManager: %s" %
                      (loaded_local_mgr, mgr_name))
          return
      log.debug("Load DomainManager based on config: %s" % mgr_name)
      # Start domain manager
      self.start_mgr(name=mgr_name, mgr_params=mgr_cfg, autostart=True)

  def load_local_domain_mgr (self):
    """
    Initiate the DomainManager for the internal domain.

    :return: None
    """
    from escape.infr.topo_manager import InternalDomainManager
    loaded_local_mgr = [name for name, mgr in self.__repository.iteritems() if
                        mgr.IS_INTERNAL_MANAGER]
    if loaded_local_mgr:
      log.warning("A local DomainManager has already been initiated with the "
                  "name: %s! Skip initiation of default local DomainManager: %s"
                  % (loaded_local_mgr, InternalDomainManager.name))
      return
    log.debug("Init DomainManager for local domain based on config: %s" %
              InternalDomainManager.name)
    # Internal domain is hard coded with the name: INTERNAL
    self.start_mgr(name=InternalDomainManager.name)

  def reset_initiated_mgrs (self):
    """
    Reset initiated DomainManagers based on the first received config.

    :return: None
    """
    log.info("Resetting detected domains before shutdown...")
    for name, mgr in self:
      if not mgr.IS_EXTERNAL_MANAGER:
        try:
          mgr.reset_domain()
        except:
          log.exception("Got exception during domain resetting!")

  def clear_initiated_mgrs (self):
    """
    Clear initiated DomainManagers based on the first received config.

    :return: None
    """
    log.info("Cleanup detected domains before shutdown...")
    for name, mgr in self:
      if not mgr.IS_EXTERNAL_MANAGER:
        try:
          mgr.clear_domain()
        except:
          log.exception("Got exception during domain cleanup!")

  def stop_initiated_mgrs (self):
    """
    Stop initiated DomainManagers.

    :return: None
    """
    log.info("Shutdown initiated DomainManagers...")
    for name, mgr in self:
      try:
        self.stop_mgr(name=name)
      except:
        log.exception("Got exception during domain resetting!")
    # Do not del mgr in for loop because of the iterator use
    self.__repository.clear()


class ControllerAdapter(object):
  """
  Higher-level class for :class:`NFFG` adaptation between multiple domains.
  """
  EXTERNAL_MDO_META_NAME = 'unify-slor'
  """Attribute name used topology from TADS to identify external MdO URL"""
  EXTERNAL_DOMAIN_NAME_JOINER = '-'

  def __init__ (self, layer_API, with_infr=False):
    """
    Initialize Controller adapter.

    For domain components the ControllerAdapter checks the CONFIG first.

    :param layer_API: layer API instance
    :type layer_API: :any:`ControllerAdaptationAPI`
    :param with_infr: using emulated infrastructure (default: False)
    :type with_infr: bool
    """
    log.debug("Init ControllerAdapter - with IL: %s" % with_infr)
    super(ControllerAdapter, self).__init__()
    # Set a weak reference to avoid circular dependencies
    self._layer_API = weakref.proxy(layer_API)
    self._with_infr = with_infr
    # Timer for VNFM
    self.__vnfm_timer = None
    # Set virtualizer-related components
    self.DoVManager = GlobalResourceManager()
    self.domains = ComponentConfigurator(self)
    self.status_mgr = DomainRequestManager()
    self.init_managers(with_infr=with_infr)
    # Here every domainManager is up and running
    # Notify the remote visualizer about collected data if it's needed
    notify_remote_visualizer(data=self.DoVManager.dov.get_resource_info(),
                             unique_id="DOV",
                             params={"event": "create"})

  def init_managers (self, with_infr=False):
    """
    :param with_infr: using emulated infrastructure (default: False)
    :type with_infr: bool
    :return: None
    """
    try:
      if with_infr:
        # Init internal domain manager if Infrastructure Layer is started
        self.domains.load_local_domain_mgr()
      # Init default domain managers
      self.domains.load_default_mgrs()
    except (ImportError, AttributeError, ConfigurationError) as e:
      from escape.util.misc import quit_with_error
      quit_with_error(msg="Shutting down ESCAPEv2 due to an unexpected error!",
                      logger=log, exception=e)

  def shutdown (self):
    """
    Shutdown ControllerAdapter, related components and stop DomainManagers.

    :return: None
    """
    # Clear DomainManagers config if needed
    if CONFIG.reset_domains_after_shutdown():
      self.domains.reset_initiated_mgrs()
    elif CONFIG.clear_domains_after_shutdown():
      self.domains.clear_initiated_mgrs()
    # Stop initiated DomainManagers
    self.domains.stop_initiated_mgrs()

  def install_nffg (self, mapped_nffg, original_request=None,
                    direct_deploy=False):
    """
    Start NF-FG installation.

    Process given :class:`NFFG`, slice information self.__global_nffg on
    domains and invoke DomainManagers to install domain specific parts.

    :param mapped_nffg: mapped NF-FG instance which need to be installed
    :type mapped_nffg: :class:`NFFG`
    :param original_request: top level, original :class:`NFFG` request
    :type original_request: :class:`NFFG`
    :param direct_deploy: skip external hook call before deploy (default: False)
    :type direct_deploy: bool
    :return: deploy result
    :rtype: DomainRequestStatus
    """
    log.debug("Invoke %s to install NF-FG(%s)" % (
      self.__class__.__name__, mapped_nffg.name))
    self.collate_deploy_request(request=mapped_nffg)
    # Register mapped NFFG for managing statuses of install steps

    log.debug("Store mapped NFFG for domain status tracking...")
    deploy_status = self.status_mgr.register_service(nffg=mapped_nffg)
    if deploy_status is None:
      log.error("Missing deploy status for request: %s. Skip deployment..."
                % mapped_nffg.id)
      return
    if not direct_deploy:
      if CONFIG.get_vnfm_enabled():
        log.info("VNFM is enabled! Skip deploy process and call external "
                 "component...")
        if self.forward_to_vnfm(nffg=mapped_nffg, deploy_status=deploy_status):
          log.info("Waiting for external component...")
          deploy_status.set_standby()
        else:
          log.debug("Clear deploy status...")
          deploy_status.clear()
        log.debug("Deploy status: %s" % deploy_status)
        return deploy_status
      else:
        log.debug("VNFM is disabled! Proceed with deploy...")
    else:
      log.debug("Direct deploy is set! "
                "Bypass external VNFM and proceed with deploy...")
    self.DoVManager.backup_dov_state()
    # If DoV update is based on status updates, rewrite the whole DoV as the
    # first step
    if self.DoVManager.status_updates:
      log.debug("Status-based update is enabled! "
                "Rewrite DoV with mapping result...")
      self.DoVManager.rewrite_global_view_with_status(nffg=mapped_nffg)
    notify_remote_visualizer(data=mapped_nffg,
                             unique_id="DOV",
                             params={"event": "datastore"})
    # Split the mapped NFFG into slices based on domains
    slices = NFFGToolBox.split_into_domains(nffg=mapped_nffg, log=log)
    # If no Infranode in the NFFG, no domain can be detected and slicing by it
    if slices is None:
      log.warning("Given mapped NFFG: %s can not be sliced! "
                  "Skip domain notification steps" % mapped_nffg)
      # Return with deploy result: fail
      return deploy_status
    NFFGToolBox.rewrite_interdomain_tags(slices)
    log.info("Notify initiated domains: %s" %
             [d for d in self.domains.initiated])
    # Perform domain installations
    for domain, part in slices:
      stats.add_measurement_start_entry(type=stats.TYPE_DEPLOY_DOMAIN,
                                        info=domain)
      log.debug("Search DomainManager for domain: %s" % domain)
      # Get Domain Manager
      domain_mgr = self.domains.get_component_by_domain(domain_name=domain)
      if domain_mgr is None:
        log.warning("No DomainManager has been initialized for domain: %s! "
                    "Skip install domain part..." % domain)
        deploy_status.set_domain_failed(domain=domain)
        continue
      log.log(VERBOSE, "Splitted domain: %s part:\n%s" % (domain, part.dump()))
      # Check if need to reset domain before install
      if CONFIG.reset_domains_before_install():
        log.debug("Reset %s domain before deploying mapped NFFG..." %
                  domain_mgr.domain_name)
        domain_mgr.reset_domain()
      log.info("Delegate splitted part: %s to %s" % (part, domain_mgr))
      # Invoke DomainAdapter's install
      domain_install_result = domain_mgr.install_nffg(part)
      # Update the DoV based on the mapping result covering some corner case
      if domain_install_result:
        log.info("Installation of %s in %s was successful!" % (part, domain))
        if self.DoVManager.status_updates:
          log.debug("Update installed part with collective result: %s" %
                    NFFG.STATUS_DEPLOY)
          # Update successful status info of mapped elements in NFFG part for
          # DoV update
          NFFGToolBox.update_status_info(nffg=part, status=NFFG.STATUS_DEPLOY,
                                         log=log)
      else:
        log.error("Installation of %s in %s was unsuccessful!" % (part, domain))
        log.debug("Update installed part with collective result: %s" %
                  NFFG.STATUS_FAIL)
        deploy_status.set_domain_failed(domain=domain)
        log.debug("Installation status: %s" % deploy_status)
        if CONFIG.rollback_on_failure():
          # Stop deploying remained nffg_parts and initiate delayed rollback
          log.info("Rollback mode is enabled! Skip installation process...")
          break
        # Update failed status info of mapped elements in NFFG part for DoV
        # update
        if self.DoVManager.status_updates:
          NFFGToolBox.update_status_info(nffg=part, status=NFFG.STATUS_FAIL,
                                         log=log)
        else:
          log.warning("Skip DoV update with domain: %s! Cause: "
                      "Domain installation was unsuccessful!" % domain)
          continue
      # If the domain manager does not poll the domain update here
      # else polling takes care of domain updating
      if isinstance(domain_mgr,
                    AbstractRemoteDomainManager) and domain_mgr.polling:
        log.info("Skip explicit DoV update for domain: %s. "
                 "Cause: polling enabled!" % domain)
        if isinstance(domain_mgr,
                      UnifyDomainManager) and domain_mgr.callback_manager:
          log.debug("Callback is enabled for domain: %s!")
        else:
          log.debug("Consider deploy into a polled domain OK...")
          deploy_status.set_domain_ok(domain=domain)
          log.debug("Installation status: %s" % deploy_status)
          continue

      if isinstance(domain_mgr,
                    UnifyDomainManager) and domain_mgr.callback_manager:
        log.info("Skip explicit DoV update for domain: %s. "
                 "Cause: callback registered!" % domain)
        deploy_status.set_domain_waiting(domain=domain)
        log.debug("Installation status: %s" % deploy_status)
        continue

      if domain_mgr.IS_INTERNAL_MANAGER:
        self.__perform_internal_mgr_update(mapped_nffg=mapped_nffg,
                                           domain=domain)
        # In case of Local manager skip the rest of the update
        continue

      if CONFIG.one_step_update():
        log.debug("One-step-update is enabled. Skip explicit domain update!")
      else:
        # Explicit domain update
        self.DoVManager.update_domain(domain=domain, nffg=part)
      # self.status_mgr.get_status(mapped_nffg.id).set_domain_ok(domain)
      deploy_status.set_domain_ok(domain=domain)
      log.debug("Installation status: %s" % deploy_status)
      if CONFIG.domain_deploy_delay():
        log.warning("Delay next deploy with %ss" % CONFIG.domain_deploy_delay())
        time.sleep(CONFIG.domain_deploy_delay())
    # END of domain deploy loop
    log.info("NF-FG installation is finished by %s" % self.__class__.__name__)
    log.debug("Overall installation status: %s" % deploy_status)
    # Post-mapping steps
    if deploy_status.success:
      log.info("All installation processes have been finished with success!")
      if CONFIG.one_step_update():
        log.debug("One-step-update is enabled. Update DoV now...")
        self.DoVManager.set_global_view(nffg=deploy_status.data)
    elif deploy_status.still_pending:
      log.warning("Installation process is still pending! "
                  "Waiting for results...")
    elif deploy_status.failed:
      log.error("%s installation was not successful!" % mapped_nffg)
      # No pending install part here
      if CONFIG.rollback_on_failure():
        self.__do_rollback(status=deploy_status,
                           previous_state=self.DoVManager.get_backup_state())
    else:
      log.info("All installation processes have been finished!")
    return deploy_status

  def collate_deploy_request (self, request):
    """
    Collate request BiSBiS node IDs to the existent nodes in DoV and correct
    domain name in request.

    :param request: service request
    :type request: :class:`NFFG`
    :return: corrected request
    :rtype: :class:`NFFG`
    """
    log.debug("Collate deploy request node IDs...")
    dov = self.DoVManager.dov.get_resource_info()
    for node in request.infras:
      if node.id not in dov.network:
        log.warning("Found non-existent infra node: %s in deploy request: %s!"
                    % (node.id, request))
        continue
      domain_name = dov[node.id].domain
      if node.domain != domain_name:
        log.debug("Collating domain id for node: %s --> %s" % (node.id,
                                                               domain_name))
        node.domain = domain_name
    return request

  def forward_to_vnfm (self, nffg, deploy_status):
    """
    Send given NFFG to an external component using its REST-API.

    :param nffg: un-deployed request
    :type nffg: :class:`NFFG`
    :param deploy_status: deploy status
    :type deploy_status: :any:`DomainRequestStatus`
    :return: result of REST call
    :rtype: bool
    """
    try:
      vnfm_config = CONFIG.get_vnfm_config()
      log.debug("Acquired external component config: %s" % vnfm_config)
      rest_adapter = UnifyRESTAdapter(url=vnfm_config.get('url'),
                                      prefix=vnfm_config.get('prefix'),
                                      domain_name="VNFM")
      # Skip removing domain name from ids
      rest_adapter.converter.ensure_unique_bisbis_id = False
      if 'timeout' in vnfm_config:
        log.debug("Set explicit timeout: %s" % vnfm_config['timeout'])
        rest_adapter.CONNECTION_TIMEOUT = vnfm_config['timeout']
      log.debug("Convert deploy request to Virtualizer...")
      virtualizer = rest_adapter.converter.dump_to_Virtualizer(nffg=nffg)
      status = rest_adapter.edit_config(data=virtualizer,
                                        diff=vnfm_config.get('diff', False))
      if status is None:
        log.error("External VNFM component call was unsuccessful!")
        return False
      else:
        timeout = vnfm_config.get('timeout', 30)
        log.debug("Using timeout for external VNFM: %ss!" % timeout)
        self.__vnfm_timer = Timer(timeout,
                                  self._vnfm_timeout_expired,
                                  kw=dict(deploy_id=deploy_status.id,
                                          timeout=timeout),
                                  started=True)
        return True
    except:
      log.error("Something went wrong during external VNFM component call!")

  def _vnfm_timeout_expired (self, deploy_id, timeout):
    """
    Handle expired timeout of external VNFM call and raise event.

    :param deploy_id: deploy status ID
    :type deploy_id: str or int
    :param timeout: timeout value in sec
    :type timeout: int
    :return: None
    """
    log.warning("External VNFM timeout: %ss has expired!" % timeout)
    self._layer_API.raiseEventNoErrors(InstallationFinishedEvent,
                                       id=deploy_id,
                                       result=InstallationFinishedEvent.DEPLOY_ERROR)

  def cancel_vnfm_timer (self):
    """
    Cancel timer defined for external VNFM call.

    :return: None
    """
    if self.__vnfm_timer:
      self.__vnfm_timer.cancel()

  def __perform_internal_mgr_update (self, mapped_nffg, domain):
    """
    Update DoV state if ESCAPE is a local Domain Orchestrator.

    :param mapped_nffg: mapped NFFG
    :type mapped_nffg: :class:`NFFG`
    :param domain: domain name
    :type domain: str
    :return: None
    """
    # If the internalDM is the only initiated mgr, we can override the
    # whole DoV
    if mapped_nffg.is_SBB():
      # If the request was a cleanup request, we can simply clean the DOV
      if mapped_nffg.is_bare():
        log.debug("Detected cleanup topology (no NF/Flowrule/SG_hop)! "
                  "Clean DoV...")
        self.DoVManager.clean_domain(domain=domain)
        self.status_mgr.get_status(mapped_nffg.id).set_domain_ok(domain)
      # If the reset contains some VNF, cannot clean or override
      else:
        log.warning(
          "Detected SingleBiSBiS topology! Local domain has been already "
          "cleared, skip DoV update...")
    # If the the topology was a GLOBAL view
    elif not mapped_nffg.is_virtualized():
      if self.DoVManager.status_updates:
        # In case of status updates, the DOV update has been done
        # In role of Local Orchestrator each element is up and running
        # update DoV with status RUNNING
        if mapped_nffg.is_bare():
          log.debug("Detected cleanup topology! "
                    "No need for status update...")
        else:
          log.debug("Detected new deployment!")
          self.DoVManager.update_global_view_status(status=NFFG.STATUS_RUN)
          self.status_mgr.get_status(mapped_nffg.id).set_domain_ok(domain)
      else:
        # Override the whole DoV by default
        self.DoVManager.set_global_view(nffg=mapped_nffg)
        self.status_mgr.get_status(mapped_nffg.id).set_domain_ok(domain)
    else:
      log.warning("Detected virtualized Infrastructure node in mapped NFFG!"
                  " Skip DoV update...")

  def __do_rollback (self, status, previous_state):
    """
    Initiate and perform the rollback feature.

    :param status: deploy status object
    :type status: :class:`DomainRequestStatus`
    :param previous_state: previous state stored before deploy
    :type previous_state: :class:`NFFG`
    :return: None
    """
    if not CONFIG.rollback_on_failure():
      return
    log.info("Rollback mode is enabled! Resetting previous state....")
    status.set_mapping_result(data=previous_state)
    log.debug("Current status: %s" % status)
    for domain in status.domains:
      domain_mgr = self.domains.get_component_by_domain(domain_name=domain)
      if domain_mgr is None:
        log.error("DomainManager for domain: %s is not found!" % domain)
        continue
      if isinstance(domain_mgr, UnifyDomainManager):
        ds = status.get_domain_status(domain=domain)
        # Skip rollback if the domain skipped by rollback interrupt
        if ds != status.INITIALIZED:
          result = domain_mgr.rollback_install(request_id=status.id)
          if not result:
            log.debug("RESET request has been failed!")
            status.set_domain_failed(domain=domain)
            continue
          if isinstance(domain_mgr,
                        AbstractRemoteDomainManager) and domain_mgr.polling:
            log.debug("Polling in domain: %s is enabled! "
                      "Set rollback status to RESET" % domain)
            status.set_domain_reset(domain=domain)
          elif isinstance(domain_mgr,
                          UnifyDomainManager) and domain_mgr.callback_manager:
            status.set_domain_waiting(domain=domain)
          else:
            status.set_domain_reset(domain=domain)
            if not CONFIG.one_step_update():
              log.debug("Extract domain state from previous state...")
              reset_state = NFFGToolBox.extract_domain(domain=domain,
                                                       nffg=previous_state)
              self.DoVManager.update_domain(domain=domain,
                                            nffg=reset_state)
        else:
          log.debug("Domain: %s is not affected. Skip rollback..." % domain)
      else:
        log.warning("%s does not support rollback! Skip rollback step...")
      log.debug("Installation status: %s" % status)
    if status.reset and CONFIG.one_step_update():
      log.debug("One-step-update is enabled. Restore DoV state now...")
      self.DoVManager.set_global_view(nffg=previous_state)
    log.info("Rollback process has been finished!")

  def _handle_DomainChangedEvent (self, event):
    """
    Handle DomainChangedEvents, dispatch event according to the cause to
    store and enforce changes into DoV.

    :param event: event object
    :type event: :class:`DomainChangedEvent`
    :return: None
    """
    if isinstance(event.source, AbstractDomainManager) \
       and event.source.IS_EXTERNAL_MANAGER:
      log.debug("Received DomainChanged event from ExternalDomainManager with "
                "cause: %s! Skip implicit domain update from domain: %s" %
                (DomainChangedEvent.TYPE.reversed[event.cause], event.domain))
      # Handle external domains
      return self._manage_external_domain_changes(event)
    log.debug("Received DomainChange event from domain: %s, cause: %s"
              % (event.domain, DomainChangedEvent.TYPE.reversed[event.cause]))
    # If new domain detected
    if event.cause == DomainChangedEvent.TYPE.DOMAIN_UP:
      self.DoVManager.add_domain(domain=event.domain,
                                 nffg=event.data)
    # If domain has got down
    elif event.cause == DomainChangedEvent.TYPE.DOMAIN_DOWN:
      self.DoVManager.remove_domain(domain=event.domain)
    # If domain has changed
    elif event.cause == DomainChangedEvent.TYPE.DOMAIN_CHANGED:
      if isinstance(event.data, NFFG):
        log.log(VERBOSE, "Changed topology:\n%s" % event.data.dump())
      self.DoVManager.update_domain(domain=event.domain,
                                    nffg=event.data)
      # Handle install status in case the DomainManager is polling the domain
      if isinstance(event.source,
                    AbstractRemoteDomainManager) and not event.source.polling:
        return
      deploy_status = self.status_mgr.get_last_status()
      if deploy_status:
        if deploy_status.get_domain_status(event.domain) == deploy_status.OK:
          log.debug("Domain: %s is already set OK. "
                    "Skip overall status check...")
          return
        deploy_status.set_domain_ok(event.domain)
        if not deploy_status.still_pending:
          if deploy_status.success:
            log.info("All installation process has been finished for request:"
                     " %s! Result: %s" % (deploy_status.id,
                                          deploy_status.status))
          else:
            log.error("All installation process has been finished for request: "
                      "%s! Result: %s" % (deploy_status.id,
                                          deploy_status.status))
          if CONFIG.one_step_update():
            log.warning("One-step-update is enabled with domain polling! "
                        "Skip update...")
          elif deploy_status.failed and CONFIG.rollback_on_failure():
            self.__do_rollback(status=deploy_status,
                               previous_state=self.DoVManager.get_backup_state())
          result = InstallationFinishedEvent.get_result_from_status(
            deploy_status)
          log.info("Overall installation result: %s" % result)
          self._layer_API.raiseEventNoErrors(InstallationFinishedEvent,
                                             id=deploy_status.id,
                                             result=result)
      else:
        log.warning("No deploy-status could be retrieved from manager!")

  def _handle_EditConfigHookEvent (self, event):
    """
    Handle event raised by received callback of a standard edit-config request.

    :param event: raised event
    :type event: :class:`EditConfigHookEvent`
    :return: None
    """
    log.debug("Received %s event..." % event.__class__.__name__)
    request_id = event.callback.request_id
    deploy_status = self.status_mgr.get_status(id=request_id)
    if event.was_error():
      log.debug("Update failed status for service request: %s..." %
                request_id)
      deploy_status.set_domain_failed(domain=event.domain)
    else:
      log.debug("Update success status for service request: %s..." % request_id)
      deploy_status.set_domain_ok(domain=event.domain)
      if isinstance(event.callback.data, NFFG):
        log.log(VERBOSE, "Changed topology:\n%s" % event.callback.data.dump())
      domain_mgr = self.domains.get_component_by_domain(event.domain)
      if domain_mgr is None:
        log.error("DomainManager for domain: %s is not found!" % event.domain)
        return
      if isinstance(domain_mgr,
                    AbstractRemoteDomainManager) and domain_mgr.polling:
        log.debug("Polling in domain: %s is enabled! Skip explicit update..."
                  % event.domain)
      else:
        if CONFIG.one_step_update():
          log.debug("One-step-update is enabled. Skip explicit domain update!")
        else:
          self.DoVManager.update_domain(domain=event.domain,
                                        nffg=event.callback.data)
    log.debug("Installation status: %s" % deploy_status)
    if not deploy_status.still_pending:
      if deploy_status.success:
        log.info("All installation process has been finished for request: %s! "
                 "Result: %s" % (deploy_status.id, deploy_status.status))
        if CONFIG.one_step_update():
          log.info("One-step-update is enabled. Update DoV now...")
          self.DoVManager.set_global_view(nffg=deploy_status.data)
      elif deploy_status.failed:
        log.error("All installation process has been finished for request: %s! "
                  "Result: %s" % (deploy_status.id, deploy_status.status))
        if CONFIG.one_step_update():
          log.warning("One-step-update is enabled. "
                      "Skip update due to failed request...")
        if CONFIG.rollback_on_failure():
          self.__do_rollback(status=deploy_status,
                             previous_state=self.DoVManager.get_backup_state())
      result = InstallationFinishedEvent.get_result_from_status(deploy_status)
      log.info("Overall installation result: %s" % result)
      # Rollback set back the domains to WAITING status
      if not deploy_status.still_pending:
        is_fail = InstallationFinishedEvent.is_error(result)
        self._layer_API._process_mapping_result(nffg_id=request_id,
                                                fail=is_fail)
        self._layer_API.raiseEventNoErrors(InstallationFinishedEvent,
                                           id=request_id,
                                           result=result)
    else:
      log.debug("Installation process is still pending! Waiting for results...")

  def _handle_ResetHookEvent (self, event):
    """
    Handle event raised by received callback of a rollback request.

    :param event: raised event
    :type event: :class:`ResetHookEvent`
    :return: None
    """
    log.debug("Received %s event..." % event.__class__.__name__)
    request_id = event.callback.request_id
    deploy_status = self.status_mgr.get_status(id=request_id)
    if event.was_error():
      log.error("ROLLBACK request: %s has been failed!" % request_id)
      deploy_status.set_domain_reset_failed(domain=event.domain)
    else:
      log.debug("Update success status for ROLLBACK request: %s..."
                % request_id)
      deploy_status.set_domain_reset(domain=event.domain)
      if CONFIG.one_step_update():
        log.debug("One-step-update is enabled. Skip explicit domain update!")
      else:
        log.debug("Extract domain state from previous state...")
        previous_state = self.DoVManager.get_backup_state()
        reset_state = NFFGToolBox.extract_domain(domain=event.domain,
                                                 nffg=previous_state)
        self.DoVManager.update_domain(domain=event.domain,
                                      nffg=reset_state)
    log.debug("Rollback status: %s" % deploy_status)
    if not deploy_status.still_pending:
      if deploy_status.reset:
        log.info("All ROLLBACK process has been finished! Result: %s" %
                 deploy_status.status)
        if CONFIG.one_step_update():
          log.debug("One-step-update is enabled. Restore DoV state now...")
          backup = self.DoVManager.get_backup_state()
          self.DoVManager.set_global_view(nffg=backup)
      elif deploy_status.failed:
        log.error("All ROLLBACK process has been finished! Result: %s" %
                  deploy_status.status)
        if CONFIG.one_step_update():
          log.warning("One-step-update is enabled. "
                      "Skip restore state due to failed request...")
      result = InstallationFinishedEvent.get_result_from_status(deploy_status)
      log.info("Overall installation result: %s" % result)
      self._layer_API.raiseEventNoErrors(InstallationFinishedEvent,
                                         id=request_id,
                                         result=result)

  def _handle_InfoHookEvent (self, event):
    """
    Handle event raised by received callback of an Info request.

    :param event: raised event
    :type event: :class:`InfoHookEvent`
    :return: None
    """
    log.debug("Received %s event..." % event.__class__.__name__)
    request_id = event.callback.request_id
    req_status = self.status_mgr.get_status(id=request_id)
    original_info, binding = req_status.data
    log.log(VERBOSE, "Original Info:\n%s" % original_info.xml())
    if event.was_error():
      log.warning("Update failed status for info request: %s..." % request_id)
      req_status.set_domain_failed(domain=event.domain)
    else:
      log.debug("Update success status for info request: %s..." % request_id)
      req_status.set_domain_ok(domain=event.domain)
      # Update Info XML with the received callback body
      try:
        log.debug("Parsing received callback data...")
        body = event.callback.body if event.callback.body else ""
        new_info = Info.parse_from_text(body)
        log.log(VERBOSE, "Received data:\n%s" % new_info.xml())
        log.debug("Update collected info with parsed data...")
        log.debug("Merging received data...")
        original_info.merge(new_info)
        log.log(VERBOSE, "Updated Info data:\n%s" % original_info.xml())
      except Exception:
        log.exception("Got error while processing Info data!")
        req_status.set_domain_failed(domain=event.domain)
    log.debug("Info request status: %s" % req_status)
    if not req_status.still_pending:
      log.info("All info processes have been finished!")
      self.__reset_node_ids(info=original_info, binding=binding)
      result = InfoRequestFinishedEvent.get_result_from_status(req_status)
      log.debug("Overall info result: %s" % result)
      self._layer_API.raiseEventNoErrors(InfoRequestFinishedEvent,
                                         result=result,
                                         status=req_status)

  def collect_domain_urls (self, mapping):
    """
    Extend the given mapping info structure with related domain URLs.

    :param mapping: collected mapping info
    :type mapping: dict
    :return: updated mapping info structure
    :rtype: dict
    """
    for m in mapping:
      try:
        domain = m['bisbis']['domain']
      except KeyError:
        log.error("Missing domain from mapping:\n%s" % m)
        continue
      url = self.get_domain_url(domain=domain)
      if url:
        log.debug("Found URL: %s for domain: %s" % (url, domain))
      else:
        log.error("URL is missing from domain: %s!" % domain)
        url = "N/A"
      m['bisbis']['url'] = url
    return mapping

  def get_domain_url (self, domain):
    """
    Return the configured domain URL based on given `domain` name.

    :param domain: domain name
    :type domain: str
    :return: URL
    :rtype: str
    """
    mgr = self.domains.get_component_by_domain(domain_name=domain)
    if not mgr:
      log.error("Domain Manager for domain: %s is not found!" % domain)
      return
    elif not isinstance(mgr, AbstractRemoteDomainManager):
      log.warning("Domain Manager for domain %s is not a remote domain manager!"
                  % domain)
      return
    else:
      return mgr.get_domain_url()

  def __resolve_nodes_in_info (self, info):
    """
    Resolve the node path in given `info` structure using the full topology
    view. Return with the collected path binding in reverse ordered way.

    :param info: info request structure
    :type info: :class:`Info`
    :return: reverse ordered path binding
    :rtype: dict
    """
    log.debug("Resolve NF paths...")
    reverse_binding = {}
    dov = self.DoVManager.dov.get_resource_info()
    for attr in (getattr(info, e) for e in info._sorted_children):
      rewrite = []
      for element in attr:
        if hasattr(element, "object"):
          old_path = element.object.get_value()
          bb, nf = get_bb_nf_from_path(path=old_path)
          new_bb = [node.id for node in dov.infra_neighbors(node_id=nf)]
          if len(new_bb) != 1:
            log.warning("Original BiSBiS for NF: %s was not found "
                        "in neighbours: %s" % (nf, new_bb))
            continue
          sep = NFFGConverter.UNIQUE_ID_DELIMITER
          new_bb = str(new_bb.pop()).rsplit(sep, 1)[0]
          reverse_binding[new_bb] = bb
          old_bb, new_bb = "/node[id=%s]" % bb, "/node[id=%s]" % new_bb
          log.debug("Find BiSBiS node remapping: %s --> %s" % (old_bb, new_bb))
          new_path = str(old_path).replace(old_bb, new_bb)
          rewrite.append((element, new_path))
      # Tricky override because object is key in yang -> del and re-add
      for e, p in rewrite:
        attr.remove(e)
        e.object.set_value(p)
        attr.add(e)
        log.debug("Overrided new path for NF --> %s" % e.object.get_value())
    return reverse_binding

  @staticmethod
  def __reset_node_ids (info, binding):
    """
    Reset node path in given `info` strucure with a previously collected
    reverse path binding structure.

    :param info: received Info object
    :type info: :class:`Info`
    :param binding: reversed node path bindings
    :type binding: dict
    :return: updated info object
    :rtype: :class:`Info`
    """
    log.debug("Reset NF paths...")
    for attr in (getattr(info, e) for e in info._sorted_children):
      rewrite = []
      for element in attr:
        if hasattr(element, "object"):
          old_path = element.object.get_value()
          bb, nf = get_bb_nf_from_path(path=old_path)
          if bb not in binding:
            log.warning("Missing binding for node: %s" % bb)
            continue
          new_bb = binding.get(bb)
          log.debug("Find BiSBiS node remapping: %s --> %s" % (bb, new_bb))
          old_bb, new_bb = "/node[id=%s]" % bb, "/node[id=%s]" % new_bb
          new_path = str(old_path).replace(old_bb, new_bb)
          rewrite.append((element, new_path))
      # Tricky override because object is key in yang -> del and re-add
      for e, p in rewrite:
        attr.remove(e)
        e.object.set_value(p)
        attr.add(e)
        log.debug("Overrided new path for NF --> %s" % e.object.get_value())
    log.log(VERBOSE, info.xml())
    return info

  def __split_info_request_by_domain (self, info):
    """
    Split the given `info` structure based on domains.

    :param info: received Info object
    :type info: :class:`Info`
    :return: splitted info dict keyed by domain names
    :rtype: dict
    """
    dov = self.DoVManager.dov.get_resource_info()
    vnfs = get_nfs_from_info(info=info)
    if not vnfs:
      log.debug("No NF has been detected from info request!")
      return {}
    splitted = NFFGToolBox.split_nfs_by_domain(nffg=dov, nfs=vnfs, log=log)
    for domain, nfs in splitted.items():
      log.debug("Splitted domain: %s --> %s" % (domain, nfs))
      info_part = strip_info_by_nfs(info, nfs)
      log.log(VERBOSE, "Splitted info part:\n%s" % info_part.xml())
      splitted[domain] = info_part
    return splitted

  def propagate_info_requests (self, id, info):
    """
    Process the received Info request and propagate the relevant part to the
    domain orchestrators.

    :param id: Info request ID
    :type id: str or int
    :param info: received Info object
    :type info: :class:`Info`
    :return: request status
    :rtype: :class:`DomainRequestStatus`
    """
    binding = self.__resolve_nodes_in_info(info=info)
    splitted = self.__split_info_request_by_domain(info=info)
    status = self.status_mgr.register_request(id=id,
                                              domains=splitted.keys(),
                                              data=(info, binding))
    if not splitted:
      log.warning("No valid request has been remained after splitting!")
      return status
    for domain, info_part in splitted.iteritems():
      log.debug("Search DomainManager for domain: %s" % domain)
      # Get Domain Manager
      domain_mgr = self.domains.get_component_by_domain(domain_name=domain)
      if domain_mgr is None:
        log.warning("No DomainManager has been initialized for domain: %s! "
                    "Skip install domain part..." % domain)
        status.set_domain_failed(domain=domain)
        continue
      if not isinstance(domain_mgr, UnifyDomainManager):
        log.warning("Domain manager: %s does not support info request! Skip...")
        status.set_domain_failed(domain=domain)
        continue
      log.log(VERBOSE, "Splitted info request: %s part:\n%s"
              % (domain, info_part.xml()))
      success = domain_mgr.request_info_from_domain(req_id=id,
                                                    info_part=info_part)
      if not success:
        log.warning("Info request: %s in domain: %s was unsuccessful!"
                    % (status.id, domain))
        status.set_domain_failed(domain=domain)
    if status.success:
      log.info("All 'info' sub-requests were successful!")
    elif status.failed:
      log.error("Top Info request: %s was unsuccessful!" % status.id)
    elif status.still_pending:
      log.info("All 'info' sub-requests have been finished! "
               "Waiting for results...")
    log.debug("Info request status: %s" % status)
    return status

  def _handle_GetLocalDomainViewEvent (self, event):
    """
    Handle GetLocalDomainViewEvent and set the domain view for the external
    DomainManager.

    :param event: event object
    :type event: :any:`DomainChangedEvent`
    :return: None
    """
    # TODO implement
    pass

  def remove_external_domain_managers (self, domain):
    """
    Shutdown adn remove ExternalDomainManager.

    :param domain: domain name
    :type domain: str
    :return: None
    """
    log.warning("Connection has been lost with external domain client! "
                "Shutdown successor DomainManagers for domain: %s..." %
                domain)
    # Get removable DomainManager names
    ext_mgrs = [name for name, mgr in self.domains
                if '@' in mgr.domain_name and
                mgr.domain_name.endswith(domain)]
    # Remove DomainManagers one by one
    for mgr_name in ext_mgrs:
      log.debug("Found DomainManager: %s for ExternalDomainManager: %s" %
                (mgr_name, domain))
      self.domains.remove_mgr(name=mgr_name)
    return

  def get_external_domain_ids (self, domain, topo_nffg):
    """
    Get the IDs of nodes from the detected external topology.

    :param domain: domain name
    :type domain: str
    :param topo_nffg: topology description
    :type topo_nffg: :class:`NFFG`
    :return: external domain IDs
    :rtype: set
    """
    domain_mgr = self.domains.get_component_by_domain(domain_name=domain)
    new_ids = {infra.id for infra in topo_nffg.infras}
    try:
      if new_ids:
        # Remove oneself from domains
        new_ids.remove(domain_mgr.bgp_domain_id)
    except KeyError:
      log.warning("Detected domains does not include own BGP ID: %s" %
                  domain_mgr.bgp_domain_id)
    return new_ids

  def _manage_external_domain_changes (self, event):
    """
    Handle DomainChangedEvents came from an :any:`ExternalDomainManager`.

    :param event: event object
    :type event: :any:`DomainChangedEvent`
    :return: None
    """
    # BGP-LS client is up
    if event.cause == DomainChangedEvent.TYPE.DOMAIN_UP:
      log.debug("Detect remote domains from external DomainManager...")
    # New topology received from BGP-LS client
    elif event.cause == DomainChangedEvent.TYPE.DOMAIN_CHANGED:
      log.debug("Detect domain changes from external DomainManager...")
    # BGP-LS client is down
    elif event.cause == DomainChangedEvent.TYPE.DOMAIN_DOWN:
      return self.remove_external_domain_managers(domain=event.domain)
    topo_nffg = event.data
    if topo_nffg is None:
      log.warning("Topology description is missing!")
      return
    # Get domain Ids
    new_ids = self.get_external_domain_ids(domain=event.domain,
                                           topo_nffg=topo_nffg)
    # Get the main ExternalDomainManager
    domain_mgr = self.domains.get_component_by_domain(domain_name=event.domain)
    # Check lost domain
    for id in (domain_mgr.managed_domain_ids - new_ids):
      log.info("Detected disconnected domain from external DomainManager! "
               "BGP id: %s" % id)
      MessageDumper().dump_to_file(data=topo_nffg.dump(),
                                   unique="%s-changed" % event.domain)
      # Remove lost domain
      if id in domain_mgr.managed_domain_ids:
        domain_mgr.managed_domain_ids.remove(id)
      else:
        log.warning("Lost domain is missing from managed domains: %s!" %
                    domain_mgr.managed_domain_ids)
        # Get DomainManager name by domain name
        ext_domain_name = "%s@%s" % (id, domain_mgr.domain_name)
        ext_mgr_name = self.domains.get_component_name_by_domain(
          domain_name=ext_domain_name)
        # Stop DomainManager and remove object from register
        self.domains.stop_mgr(name=ext_mgr_name)
    # Check new domains
    for id in (new_ids - domain_mgr.managed_domain_ids):
      orchestrator_url = topo_nffg[id].metadata.get(self.EXTERNAL_MDO_META_NAME)
      if orchestrator_url is None:
        log.warning("MdO URL is not found in the Node: %s with the name: %s! "
                    "Skip initialization..." % (
                      id, self.EXTERNAL_MDO_META_NAME))
        return
      log.info("New domain detected from external DomainManager! "
               "BGP id: %s, Orchestrator URL: %s" % (id, orchestrator_url))
      MessageDumper().dump_to_file(data=topo_nffg.dump(),
                                   unique="%s-changed" % event.domain)
      # Track new domain
      domain_mgr.managed_domain_ids.add(id)
      # Get RemoteDM config
      mgr_cfg = CONFIG.get_component_params(component=domain_mgr.prototype)
      if mgr_cfg is None:
        log.warning("DomainManager: %s configurations is not found! "
                    "Skip initialization...")
        return
      # Set domain name
      mgr_cfg['domain_name'] = "%s%s%s" % (id,
                                           self.EXTERNAL_DOMAIN_NAME_JOINER,
                                           domain_mgr.domain_name)
      log.debug("Generated domain name: %s" % mgr_cfg['domain_name'])
      # Set URL and prefix
      try:
        url = urlparse.urlsplit(orchestrator_url)
        mgr_cfg['adapters']['REMOTE']['url'] = "http://%s" % url.netloc
        mgr_cfg['adapters']['REMOTE']['prefix'] = url.path
      except KeyError as e:
        log.warning("Missing required config entry %s from "
                    "RemoteDomainManager: %s" % (e, domain_mgr.prototype))
      log.log(VERBOSE, "Used configuration:\n%s" % pprint.pformat(mgr_cfg))
      log.info("Initiate DomainManager for detected external domain: %s, "
               "URL: %s" % (mgr_cfg['domain_name'], orchestrator_url))
      # Initialize DomainManager for detected domain
      ext_mgr = self.domains.load_component(component_name=domain_mgr.prototype,
                                            params=mgr_cfg)
      log.debug("Use domain name: %s for external DomainManager name!" %
                ext_mgr.domain_name)
      # Start the DomainManager
      self.domains.register_mgr(name=ext_mgr.domain_name,
                                mgr=ext_mgr,
                                autostart=True)


class DomainRequestStatus(object):
  """
  Container class for storing related information about a service request.
  """
  INITIALIZED = "INITIALIZED"
  OK = "OK"
  WAITING = "WAITING"
  FAILED = "FAILED"
  RESET = "RESET"
  RESET_FAILED = "RESET_FAILED"

  def __init__ (self, id, domains, data=None):
    """
    Init.

    :param id: request ID
    :type id: str or int
    :param domains: domains affected by the request
    :type domains: set
    :param data: service request under deploy (optional)
    :type data: :class:`NFFG`
    """
    self.__id = id
    self.__statuses = {}.fromkeys(domains, self.INITIALIZED)
    self.__standby = False
    self.__data = data

  @property
  def id (self):
    """
    Return service ID.

    :return: service ID
    :rtype: str or int
    """
    return self.__id

  @property
  def data (self):
    """
    Return data.

    :return: data
    :rtype: :class:`NFFG` or
    """
    return self.__data

  def set_mapping_result (self, data):
    """
    Overwrite the stored service request under deploy.

    :param data: new service request
    :type data: :class:`NFFG`
    :return: None
    """
    log.debug("Set mapping result: %s for service request: %s"
              % (data.id, self.__id))
    self.__data = data

  def reset_status (self, data=None):
    """
    Reset the object state and use the given data as service request.

    :param data: optional service request
    :type data: :class:`NFFG`
    :return: None
    """
    log.debug("Clear domain status...")
    for domain in self.__statuses:
      self.__statuses[domain] = self.INITIALIZED
    self.set_mapping_result(data=data)
    self.reset_standby()

  def set_standby (self):
    """
    Set deploy status object in `standby` state.

    :return: None
    """
    log.debug("Put request: %s in standby mode" % self.__id)
    self.__standby = True

  @property
  def standby (self):
    """
    Return standby state.

    :return: standby
    :rtype: bool
    """
    return self.__standby

  def set_active (self):
    """
    Set deploy status object in `active` state.

    :return: None
    """
    if self.__standby:
      log.debug("Continue request: %s " % self.__id)
      self.__standby = False

  def reset_standby (self):
    """
    Reset standby state to default value.

    :return: None
    """
    if self.__standby:
      log.debug("Reset request to active mode")
      self.__standby = False

  def clear (self):
    """
    Clear tracked domain statuses.

    :return: None
    """
    self.__statuses.clear()

  @property
  def still_pending (self):
    """
    :return: Return True if the deployment is still pending
    :rtype: bool
    """
    if self.__statuses:
      return any(map(lambda s: s in (self.INITIALIZED, self.WAITING),
                     self.__statuses.itervalues()))
    else:
      return False

  @property
  def success (self):
    """
    :return: Return True if the deployment was successful
    :rtype: bool
    """
    if self.__statuses:
      return all(map(lambda s: s == self.OK,
                     self.__statuses.itervalues()))
    else:
      return False

  @property
  def reset (self):
    """
    :return: Return True if the service was successfuly reset
    :rtype: bool
    """
    if self.__statuses:
      return all(map(lambda s: s == self.RESET,
                     self.__statuses.itervalues()))
    else:
      return False

  @property
  def failed (self):
    """
    :return: Return True if the deployment was failed
    :rtype: bool
    """
    return any(map(lambda s: s == self.FAILED,
                   self.__statuses.itervalues()))

  @property
  def reset_failed (self):
    """
    :return: Return True if the service was unsuccessfully reset
    :rtype: bool
    """
    return any(map(lambda s: s == self.RESET_FAILED,
                   self.__statuses.itervalues()))

  @property
  def status (self):
    """
    Return the overall deploy status.

    :return: deploy status
    :rtype: str
    """
    for s in self.statuses:
      if s == self.FAILED:
        return self.FAILED
      elif s == self.RESET_FAILED:
        return self.RESET_FAILED
      elif s == self.WAITING:
        return self.WAITING
    if self.reset:
      return self.RESET
    elif self.success:
      return self.OK
    else:
      return self.INITIALIZED

  @property
  def domains (self):
    """
    :return: Tracked domains names
    :rtype: tuple
    """
    return self.__statuses.keys()

  @property
  def statuses (self):
    """
    :return: Tracked domain statuses
    :rtype: tuple
    """
    return self.__statuses.values()

  def __str__ (self):
    return "%s(id=%s) => %s" % (self.__class__.__name__,
                                self.__id, str(self.__statuses))

  def get_domain_status (self, domain):
    """
    Return with the given domain deploy status.

    :param domain: domain name
    :type domain: str
    :return: deploy status
    :rtype: str
    """
    return self.__statuses.get(domain)

  def set_domain (self, domain, status):
    """
    Set the given domain wioht the given status value.

    :param domain: domain name
    :type domain: str
    :param status: deploy status
    :type status: str
    :return: domain status object
    :rtype: :class:`DomainRequestStatus`
    """
    if domain not in self.__statuses:
      raise RuntimeError("Updated domain: %s is not registered!" % domain)
    self.__statuses[domain] = status
    if status in (self.OK, self.FAILED, self.RESET):
      stats.add_measurement_end_entry(type=stats.TYPE_DEPLOY_DOMAIN,
                                      info="%s-->%s" % (domain, status))
    return self

  def set_domain_ok (self, domain):
    """
    Set successful domain status for given domain.

    :param domain: domain name
    :type domain: str
    :return: domain status object
    :rtype: :class:`DomainRequestStatus`
    """
    log.debug("Set install status: %s for domain: %s" % (self.OK, domain))
    return self.set_domain(domain=domain, status=self.OK)

  def set_domain_waiting (self, domain):
    """
    Set pending domain status for given domain.

    :param domain: domain name
    :type domain: str
    :return: domain status object
    :rtype: :class:`DomainRequestStatus`
    """
    log.debug("Set install status: %s for domain: %s" % (self.WAITING, domain))
    return self.set_domain(domain=domain, status=self.WAITING)

  def set_domain_failed (self, domain):
    """
    Set failed domain status for given domain.

    :param domain: domain name
    :type domain: str
    :return: domain status object
    :rtype: :class:`DomainRequestStatus`
    """
    log.debug("Set install status: %s for domain: %s" % (self.FAILED, domain))
    return self.set_domain(domain=domain, status=self.FAILED)

  def set_domain_reset (self, domain):
    """
    Set reset domain status for given domain.

    :param domain: domain name
    :type domain: str
    :return: domain status object
    :rtype: :class:`DomainRequestStatus`
    """
    log.debug("Set install status: %s for domain: %s" % (self.RESET, domain))
    return self.set_domain(domain=domain, status=self.RESET)

  def set_domain_reset_failed (self, domain):
    """
    Set faield reset domain status for given domain.

    :param domain: domain name
    :type domain: str
    :return: domain status object
    :rtype: :class:`DomainRequestStatus`
    """
    log.debug("Set install status: %s for domain: %s" % (self.RESET_FAILED,
                                                         domain))
    return self.set_domain(domain=domain, status=self.RESET_FAILED)


class DomainRequestManager(object):
  """
  Manager class to register service requests for managing deployment.
  """

  def __init__ (self):
    """
    Init.
    """
    self._services = []
    self._last = None

  def register_request (self, id, domains, data=None):
    """
    Register a service request.

    :param id: request ID
    :type id: str or int
    :param domains: domains affected by the request
    :type domains: set
    :param data: service request under deploy (optional)
    :type data: :class:`NFFG`
    :return: created deploy status object
    :rtype: :class:`DomainRequestStatus`
    """
    for s in self._services:
      if s.id == id:
        log.warning("Detected already registered service request: %s in %s! "
                    "Reset deploy status..." % (id, self.__class__.__name__))
        s.reset_status(data=data)
        self._last = s
        return s
    else:
      status = DomainRequestStatus(id=id, domains=domains, data=data)
      self._services.append(status)
      self._last = status
      log.info("Request with id: %s is registered for status management!" % id)
      log.debug("Status: %s" % status)
      return status

  def get_last_status (self):
    """
    :return: Last registered deploy status object
    :rtype: :class:`DomainRequestStatus`
    """
    return self._last

  def register_service (self, nffg):
    """
    Wrapper function to register a service request using the request object.

    :param nffg: service request
    :type nffg: :class:`NFFG`
    :return: created deploy status object
    :rtype: :class:`DomainRequestStatus`
    """
    domains = NFFGToolBox.detect_domains(nffg=nffg)
    return self.register_request(id=nffg.id, domains=domains, data=nffg)

  def get_status (self, id):
    """
    Return the deploy status object of the given ID.

    :param id: service request ID
    :type id: str or int
    :return: created deploy status object
    :rtype: :class:`DomainRequestStatus`
    """
    for status in self._services:
      if status.id == id:
        return status
    else:
      log.error("Service status for service: %s is missing!" % id)


class GlobalResourceManager(object):
  """
  Handle and store the Global Resources view as known as the DoV.
  """

  def __init__ (self):
    """
    Init.
    """
    super(GlobalResourceManager, self).__init__()
    log.debug("Init DomainResourceManager")
    self.__dov = DomainVirtualizer(self)  # Domain Virtualizer
    self.__tracked_domains = set()  # Cache for detected and stored domains
    self.status_updates = CONFIG.use_status_based_update()
    self.remerge_strategy = CONFIG.use_remerge_update_strategy()
    self.__backup = None

  @property
  def dov (self):
    """
    Getter for :class:`DomainVirtualizer`.

    :return: global infrastructure view as the Domain Virtualizer
    :rtype: :any:`DomainVirtualizer`
    """
    return self.__dov

  @property
  def tracked (self):
    """
    Getter for tuple of detected domains.

    :return: detected domains
    :rtype: tuple
    """
    return tuple(self.tracked)

  def backup_dov_state (self):
    """
    Backup current state of DoV.

    :return: None
    """
    log.debug("Backup current DoV state...")
    self.__backup = self.dov.get_resource_info()
    self.__backup.id = (self.__backup.id + "-backup")

  def get_backup_state (self):
    """
    Return with the stored beckup.

    :return: stashed DoV
    :rtype: :class:`NFFG`
    """
    log.debug("Acquire previous DoV state...")
    return self.__backup

  def set_global_view (self, nffg):
    """
    Replace the global view with the given topology.

    :param nffg: new global topology
    :type nffg: :class:`NFFG`
    :return: None
    """
    log.debug("Update the whole Global view (DoV) with the NFFG: %s..." % nffg)
    self.__dov.update_full_global_view(nffg=nffg)
    self.__tracked_domains.clear()
    self.__tracked_domains.update(NFFGToolBox.detect_domains(nffg))
    notify_remote_visualizer(data=self.__dov.get_resource_info(),
                             unique_id="DOV",
                             params={"event": "datastore"})

  def update_global_view_status (self, status):
    """
    Update the status of the elements in DoV with the given status.

    :param status: status
    :type status: str
    :return: None
    """
    log.debug("Update Global view (DoV) mapping status with: %s" % status)
    NFFGToolBox.update_status_info(nffg=self.__dov.get_resource_info(),
                                   status=status, log=log)

  def rewrite_global_view_with_status (self, nffg):
    """
    Replace the global view with the given topology and add status for the
    elements.

    :param nffg: new global topology
    :type nffg: :class:`NFFG`
    :return: None
    """
    if not nffg.is_infrastructure():
      log.error("New topology is not contains no infrastructure node!"
                "Skip DoV update...")
      return
    if nffg.is_virtualized():
      log.debug("Update NFFG contains virtualized node(s)!")
      if self.__dov.get_resource_info().is_virtualized():
        log.debug("DoV also contains virtualized node(s)! "
                  "Enable DoV rewriting!")
      else:
        log.warning("Detected unexpected virtualized node(s) in update NFFG! "
                    "Skip DoV update...")
        return
    log.debug("Migrate status info of deployed elements from DoV...")
    NFFGToolBox.update_status_by_dov(nffg=nffg,
                                     dov=self.__dov.get_resource_info(),
                                     log=log)
    self.set_global_view(nffg=nffg)
    log.log(VERBOSE,
            "Updated DoV:\n%s" % self.__dov.get_resource_info().dump())

  def add_domain (self, domain, nffg):
    """
    Update the global view data with the specific domain info.

    :param domain: domain name
    :type domain: str
    :param nffg: infrastructure info collected from the domain
    :type nffg: :class:`NFFG`
    :return: None
    """
    # If the domain is not tracked
    if domain not in self.__tracked_domains:
      if not nffg:
        log.warning("Got empty data. Skip domain addition...")
        return
      log.info("Append %s domain to DoV..." % domain)
      # If DoV is empty
      if not self.__dov.is_empty():
        # Merge domain topo into global view
        self.__dov.merge_new_domain_into_dov(nffg=nffg)
      else:
        # No other domain detected, set NFFG as the whole Global view
        log.debug(
          "DoV is empty! Add new domain: %s as the global view!" % domain)
        self.__dov.set_domain_as_global_view(domain=domain, nffg=nffg)
      # Add detected domain to cached domains
      self.__tracked_domains.add(domain)
      notify_remote_visualizer(data=self.__dov.get_resource_info(),
                               unique_id="DOV",
                               params={"event": "datastore"})
    else:
      log.error("New domain: %s has already tracked in domains: %s! "
                "Abort adding..." % (domain, self.__tracked_domains))

  def update_domain (self, domain, nffg):
    """
    Update the detected domain in the global view with the given info.

    :param domain: domain name
    :type domain: str
    :param nffg: changed infrastructure info
    :type nffg: :class:`NFFG`
    :return: None
    """
    if domain in self.__tracked_domains:
      log.info("Update domain: %s in DoV..." % domain)
      if self.status_updates:
        log.debug("Update status info for domain: %s in DoV..." % domain)
        self.__dov.update_domain_status_in_dov(domain=domain, nffg=nffg)
      elif self.remerge_strategy:
        log.debug("Using REMERGE strategy for DoV update...")
        self.__dov.remerge_domain_in_dov(domain=domain, nffg=nffg)
      else:
        log.debug("Using UPDATE strategy for DoV update...")
        self.__dov.update_domain_in_dov(domain=domain, nffg=nffg)
      notify_remote_visualizer(data=self.__dov.get_resource_info(),
                               unique_id="DOV",
                               params={"event": "datastore"})
    else:
      log.error(
        "Detected domain: %s is not included in tracked domains: %s! Abort "
        "updating..." % (domain, self.__tracked_domains))

  def remove_domain (self, domain):
    """
    Remove the detected domain from the global view.

    :param domain: domain name
    :type domain: str
    :return: None
    """
    if domain in self.__tracked_domains:
      log.info("Remove domain: %s from DoV..." % domain)
      self.__dov.remove_domain_from_dov(domain=domain)
      self.__tracked_domains.remove(domain)
      notify_remote_visualizer(data=self.__dov.get_resource_info(),
                               unique_id="DOV",
                               params={"event": "datastore"})
    else:
      log.warning("Removing domain: %s is not included in tracked domains: %s! "
                  "Skip removing..." % (domain, self.__tracked_domains))

  def clean_domain (self, domain):
    """
    Clean given domain.

    :param domain: domain name
    :type domain: str
    :return: None
    """
    if domain in self.__tracked_domains:
      log.info(
        "Remove initiated VNFs and flowrules from the domain: %s" % domain)
      self.__dov.clean_domain_from_dov(domain=domain)
      notify_remote_visualizer(data=self.__dov.get_resource_info(),
                               unique_id="DOV",
                               params={"event": "datastore"})
    else:
      log.error(
        "Detected domain: %s is not included in tracked domains: %s! Abort "
        "cleaning..." % (domain, self.__tracked_domains))
