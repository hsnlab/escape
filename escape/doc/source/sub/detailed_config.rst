:orphan:

Detailed configuration structure
--------------------------------

The configuration is divided into 4 parts according to the UNIFY's / ESCAPE's
main layers, namely ``service``, ``orchestration``, ``adaptation`` and ``infrastructure``.

Service and Orchestration
^^^^^^^^^^^^^^^^^^^^^^^^^

The top 2 layer (``service`` and ``orchestration``) has similar configuration parameters.
In both layers the core mapping process can be controlled with the following entries:

  * **MAPPER** defines the mapping class which controls the mapping process
    (inherited from :any:`AbstractMapper`)
  * **STRATEGY** defines the mapping strategy class which calls the actual mapping
    algorithm (inherited from :any:`AbstractMappingStrategy`)
  * **PROCESSOR** defines the Processor class which contains the pre/post mapping
    functions for validation and other auxiliary functions (inherited from :any:`AbstractMappingDataProcessor`)

The values of the class configurations (such the entries above) always contains the **module** and **class** names.
With this approach ESCAPE can also instantiate and use different implementations from external Python packages.
The only requirement for these classes is to be included in the scope of ESCAPE
(more precisely in the PYTHONPATH of the Python interpreter which runs ESCAPE).

.. note::

  Every additional subdirectory in the project's root is always added to the search
  path (scope) dynamically by the main ``escape`` module at initial time.

The mapping process and pre/post processing can be enabled/disabled with the
``mapping-enabled`` (boolean) and ``enabled`` (boolean) values under the appropriate entries.

The mapping algorithm called in the Strategy class can be initiated in a worker
thread with the ``THREADED`` flag but this feature is still in experimental phase!

These 2 layers can also initiate REST-APIs. The initial parameters are defined
under the names of the APIs:

  * **REST-API** - top REST-API in the SAS layer
  * **Sl-Or** - Sl-Or interface in the ROS layer for external components
    i.e. for upper UNIFY entities, GUI or other ESCAPE instance in a distributed, multi-layered scenario
  * **Cf-Or** - Cf-Or interface in the ROS layer for supporting service elasticity feature

These REST-API configurations consist of

  * a specific handler class which initiated for every request and handles the
    requests (inherited from :any:`AbstractRequestHandler`) defined with the ``module`` and ``class`` pair
  * address of the REST-API defined with the ``address`` and ``port`` (integer) pair
  * ``prefix`` of the API which appears in the URL right before the REST functions
  * optionally the type of used Virtualizer (``virtualizer_type``) which filters the data flow of the API
    (currently only supported the global (`GLOBAL`) and single BiS-BiS (`SINGLE`) Virtualizer)
  * flags mark the interface as UNIFY interface (``unify_interface``) with difference format (``diff``)

Schematic config description:

MAPPER
******
Contains the configuration of the *Mapper* class responsible for managing the overall mapping process of the layer.

    `module`
        (:any:`string`) Python module name where `class` can be found, e.g. ``escape.orchest.ros_mapping``
    `class`
        (:any:`string`) Python class name of the *MAPPER*, e.g. ``ResourceOrchestrationMapper``
    `mapping-enabled`
        (:any:`bool`) Enables the mapping process in the actual layer
    `mapping config`
        (:class:`dict`) Optional arguments directly given to the main entry point of the core mapping function
        ``MappingAlgorithms.MAP()``, e.g. ``mode="REMAP"`` force the algorithm to use the *REMAP* orchestration
        approach in every case. See more in the function's documentation.

STRATEGY
********
Contains the configuration of the *Strategy* class responsible for running chosen orchestration algorithm.

    `module`
        (:any:`string`) Python module name where `class` can be found, e.g. ``escape.service.sas_mapping``
    `class`
        (:any:`string`) Python class name of the *STRATEGY*, e.g. ``DefaultServiceMappingStrategy``
    `THREADED`
        (:any:`bool`) Enables the mapping process in a separate thread (experimental).

PROCESSOR
*********
Contains the configurations of the *Processor* class responsible for invoke pre/post mapping functionality.

    `module`
        (:any:`string`) Python module name where `class` can be found, e.g. ``escape.util.mapping``
    `class`
        (:any:`string`) Python class name of the *PROCESSOR*, e.g. ``ProcessorSkipper``
    `enabled`
        (:any:`bool`) Enables pre/post processing

REST-API, Sl-Or, Cf-Or, DOV-API
*******************************
Contains the configuration of the *Handler* class responsible for processing requests *Sl-Or*, *Cf-Or* interface.

    `module`
        (:any:`string`) Python module name where `class` can be found, e.g. ``escape.orchest.ros_API``
    `class`
        (:any:`string`) Python class name of the *HANDLER*, e.g. ``BasicUnifyRequestHandler``
    `address`
        (:any:`string`) Address the REST server bound to, e.g. ``0.0.0.0``
    `port`
        (:any:`int`) Port the REST server listens on, e.g. ``8008``
    `prefix`
        (:any:`string`) Used prefix in the REST request URLs, e.g. ``escape``
    `unify_interface`
        (:any:`bool`) Set the interface to use the Virtualizer format.
    `diff`
        (:any:`bool`) Set accepted format to difference instead of full.
    `virtualizer_type`
        (:any:`string`) Use the given abstraction for generation topology description:
            ``SINGLE``: use Single BiSBiS representation

            ``GLOBAL``: offer the whole domain view intact

Other configuration entries
***************************
Other configuration entries of these layers.

*service*
  `SERVICE-LAYER-ID`
    (:any:`string`) Internal ID of Service module - shouldn't be changed.
  `SCHEDULED_SERVICE_REQUEST_DELAY`
    (:any:`int`) Add delay before initiate service mapping read from initial parameter.

*orchestration*
  `ESCAPE-SERVICE`
    (:class:`dict`) Defines parameters for internal Service API identified by the name: *ESCAPE-SERVICE*
      `virtualizer_type`
        (:any:`string`) Use the given topology abstraction for internal Service layer:
          ``SINGLE``: use Single BiSBiS representation

          ``GLOBAL``: offer the whole domain view intact
*NFIB*
  `enable`
    (:any:`bool`) Enable using NFIB Manager
  `host`
    (:any:`bool`) Address of the neo4j server API - shouldn't be changed.
  `port`
    (:any:`bool`) Port of the neo4j server API - shouldn't be changed.
  `manage-neo4j-service`
    (:any:`bool`) Force ESCAPE to start and stop Neo4j service by itself

Adaptation
^^^^^^^^^^

The ``adaptation`` layer contains the configuration of different Manager (inherited from :any:`AbstractDomainManager`)
classes under their specific name which is defined in the ``name`` class attribute.

These configurations are used by the :any:`ComponentConfigurator` to initiate the required components dynamically.
Every Manager use different Adapters (inherited from :any:`AbstractESCAPEAdapter`)
to hide the specific protocol-agnostic steps in the communication between the ESCAPE orchestrator and network elements.

The configurations of these Adapters can be found under the related Manager config (``adapters``)
in order to be able to initiate multiple Managers based on the same class with different Adapter configurations.

The class configurations can be given by the ``module`` and ``class`` pair similar way as so far.
Other values such as ``path``, ``url``, ``keepalive``, etc. will be forwarded to the constructor of the component
at initialization time so the possible configurations parameters and its types are derived from the parameters
of the class' constructor.

The ``MANAGERS`` list contains the configuration names of Managers need to be initiated.

In order to activate a manager and manage the specific domain, add the config name of the DomainManager
to the ``MANAGERS`` list. The manager will be initiated with other Managers at boot time of ESCAPE.

.. warning::

    If a Manager's name does not included in the ``MANAGERS`` list, the corresponding domain will NOT be managed!

Schematic config description:

    `MANAGERS`
        (:any:`list`) Contains the name of the domain managers need to be initiated, e.g. `["SDN", "OPENSTACK"]`

Domain Managers
***************

The domain manager configurations contain the parameters of the different manager objects.
The defined manager configuration is directly given to the constructor function of the manager
class by the :any:`ComponentConfigurator` object.

The default configuration defines a default domain manager and the relevant adapter configurations
for the Infrastructure layer with the name: `INTERNAL`. The internal domain manager
is used for managing the Mininet-based emulated network initiated by the ``--full`` command line parameter.

ESCAPE also has default configuration for other type of domain managers:

* ``SDN`` entry defines a domain manager dedicated to manage external SDN-capable hardware or software switches
  with a single-purpose domain manager realized by ``SDNDomainManager``.
  This manager uses the available POX OpenFlow controller features and a static topology description file to form the domain view.

* ``OPENSTACK`` entry defines a more generic domain manager which uses the general ``UnifyDomainManager`` to manage UNIFY domains.

* ``REMOTE-ESCAPE`` entry defines a domain manager for another ESCAPE instance in the role of local DO.
  This domain manager also uses the UNIFY format with some additional data for the DO's mapping algorithm to be more deterministic.

* ``BGP-LS-SPEAKER`` gives an example for an external domain manager which discovers other providers' domains
  with the help of different external tools instead of directly managing a local DO. External domain managers have
  the authority to initiate other domain managers for the detected domain.

An additional configuration file typically contains these domain manager configurations along with the list (``MANAGERS``)
of the enabled managers. As an example several example file can be found under the ``config`` folder.

Schematic description of main configuration entries related to domain managers:

    `NAME`
        Unique domain manager name. Used also in the ``MANAGERS`` list for enabling the defined domain manager.

        Default domain managers: ``INTERNAL``, ``SDN``, ``OPENSTACK``, ``REMOTE-ESCAPE``, ``BGP-LS-SPEAKER``.

        `module`
            (:any:`string`) Python module name where `class` can be found, e.g. ``escape.adapt.managers``
        `class`
            (:any:`string`) Python class name of the domain manager, e.g. ``UnifyDomainManager``
        `domain_name`
            (:any:`string`) Optional domain name used in the global topology view. Default value is the domain manager's config name.
        `poll`
            (:any:`bool`) Enables domain polling.
        `diff`
            (:any:`bool`) Enables differential format. Works only with UNIFY-based domain managers (inherited from :any:`AbstractRemoteDomainManager`).
        `keepalive`
            (:any:`bool`) Enables sending `ping` messaged to domains to detect domain up/down events. Works only with UNIFY-based domain managers (inherited from :any:`AbstractRemoteDomainManager`).
        `adapters`
            (:class:`dict`) Contains the domain adapter config given directly to the adapters at creation time. Each domain manager has the required set
            of domain adapter types.

Domain Adapters
***************

The domain adapter configurations contain the parameters of the different adapter objects splitted by its roles. The adapter objects are instantiated and
configured by the container domain manager object. Each adapter class has its own role and parameter set. The defined adapter configuration is directly
given to the constructor function of the adapter class by the container domain manager.

Schematic config description of domain adapters:

    `<ROLE>`
        Unique role of the defined domain adapter. Used in the ``adapters`` configuration entry of domain managers.

        Defined roles: ``CONTROLLER``, ``MANAGEMENT``, ``TOPOLOGY``, ``REMOTE``

        `module`
            (:any:`string`) Python module name where `class` can be found, e.g. ``escape.adapt.adapters``
        `class`
            (:any:`string`) Python class name of the domain adapter, e.g. ``UnifyRESTAdapter``

    *CONTROLLER*
        Define domain adapter for controlling domain elements, typically SDN-capable switches.

        `name`
            (:any:`string`) Optional name for the OpenFlow controller instance used in the POX's core object, shouldn't be changed.
        `address`
            (:any:`string`) Address the OF controller instance bound to, e.g. ``0.0.0.0``
        `port`
            (:any:`int`) Port number the OF controller listens on, e.g. ``6653``
        `keepalive`
            (:any:`bool`) Enables internal keepalive mechanism for sending periodic OF Echo messages to switches.
        `sap_if_prefix`
            (:any:`string`) Defines the prefix of physical interfaces for SAPs, e.g. ``eth``.
            Works only with :any:`InternalPOXAdapter`.
        `binding`
            (:any:`dict`) Defines static BiSBiS name --> DPID binding for OF switches as key-value pairs, e.g. ``{"MT1": 365441792307142}``.
            Works only with :any:`SDNDomainPOXAdapter`.

    *TOPOLOGY*
        Define domain adapter for providing topology description of the actual domain.

        `net`
            (:any:`object`) Optional network object for :class:`mininet.net.Mininet`.
            Works only with :class:`InternalMininetAdapter`. Only for development!
        `path`
            (:any:`string`) Path of the static topology description :class:`NFFG` file, e.g. ``examples/sdn-topo.nffg``.
            Works only with ``SDNDomainTopoAdapter``.

    *REMOTE*
        Define domain adapter for communication with remote domain, typically through a REST-API.

        `url`
            (:any:`string`) URL of the remote domain agent, e.g. ``http://127.0.0.1:8899``
        `prefix`
            (:any:`string`) Specific prefix of the REST interface, e.g. ``/virtualizer``
        `timeout`
            (:any:`int`) Connection timeout in sec, e.g. ``5``
        `unify_interface`
            (:any:`bool`) Set the interface to use the Virtualizer format.

    *MANAGEMENT*
        Defines domain adapter for init/start/stop VNFs in the domain. Currently only NETCONF-based management is implemented!

        `server`
            (:any:`string`) Server address of the NETCONF server in the domain, e.g. ``127.0.0.1``
        `port`
            (:any:`int`) Listening port of the NETCONF server, e.g. ``830``
        `username`
            (:any:`string`) Username for the SSH connection, e.g. ``mininet``
        `password`
            (:any:`string`) Password for the SSH connection, e.g. ``mininet``
        `timeout`
            (:any:`int`) Connection timeout in sec, e.g. ``5``

    *CALLBACK*
       Set the domain manager to use callback mechanism for detecting deployment result

        `enabled`
            (:any:`bool`) Enable using callback mechanism for the actual domain manager.
        `explicit_host`
            (:any:`string`) Use explicit host name for callback URL instead of calculated one. Useful e.g. behind NAT.
        `explicit_port`
            (:any:`int`) Use explicit host name for callback URL instead of default one.
        `explicit_update`
            (:any:`bool`) Issue a get-config request to acquire the latest domain topology after a callback was received.

Generic adaptation layer configuration
**************************************

Among the Manager configurations the `adaptation` section also contains several configuration parameters
which are mostly general parameters and have effect on the overall behavior of the Adaptation layer.

Schematic config description of general parameters:

    *VNFM*
        `enable`
            (:any:`bool`) Enables to use external VNFM component.
        `url`
            (:any:`bool`) Url of the external component.
        `prefix`
            (:any:`string`) Specific prefix of the REST interface.
        `timeout`
            (:any:`int`) Default connection timeout in sec.
        `diff`
            (:any:`bool`) Enables differential format.

    *CALLBACK*
        `address`
            (:any:`string`) Use explicit host name for callback Manager.
        `port`
            (:any:`int`) Use explicit port for callback Manager.
        `timeout`
            (:any:`int`) Default connection timeout in sec.

    *DOV*
        `ENSURE-UNIQUE-ID`
            (:any:`bool`) Generate unique id for every BiSBiS node in the detected domain using the original BiSBiS id and domain name.
        `USE-REMERGE-UPDATE-STRATEGY`
            (:any:`bool`) Use the `REMERGE` strategy for the global view updates which stand of an explicit remove and add step
        `USE-STATUS-BASED-UPDATE`
            (:any:`bool`) Use status values for the service instead of imminent domain view rewriting.
        `ONE-STEP-UPDATE`
            (:any:`bool`) Use one step update strategy to update dov at the end of a deploy request

    *deployment*
        `RESET-DOMAINS-BEFORE-INSTALL`
            (:any:`bool`) Enables to send the resetting topology before an service install is initiated.
        `RESET-DOMAINS-AFTER-SHUTDOWN`
            (:any:`bool`) Enables to send the resetting topology before shutdown of ESCAPE.
        `CLEAR-DOMAINS-AFTER-SHUTDOWN`
            (:any:`bool`) Enables to send a cleaned topology right before shutdown of ESCAPE.
        `ROLLBACK-ON-FAILURE`
            (:any:`bool`) Enables to send rollback request to domains if the overall deploy status was failed.
        `DOMAIN-DEPLOY-DELAY`
            (:any:`int`) Add a delay before initiate deploying the mapped service.

Infrastructure
^^^^^^^^^^^^^^

The configuration of ``infrastructure`` layer controls the Mininet-based emulation.

The ``TOPO`` path value defines the file which will be parsed and processed to build the Mininet structure.

The ``FALLBACK-TOPO`` defines an inner class which can initiate a topology if the topology file is not found.

The ``NETWORK-OPTS`` is an optional data which can be added to override the default constructor parameters of the Mininet class.

The ``Controller``, ``EE``, ``Switch``, ``SAP`` and ``Link`` dictionaries can contain optional parameters for the constructors
 of the internal Mininet-based representation. In most cases these parameters need to be left unchanged.

Other simple values can be added too to refine the control of the emulation such as enable/disable the
xterm initiation for SAPs (``SAP-xterm``) or the cleanup task (``SHUTDOWN-CLEAN``).

Schematic config description:

    `TOPO`
        (:any:`string`) Path of the topology :class:`NFFG` used to build the emulated network, e.g. ``examples/escape-mn-topo.nffg``
    `SHUTDOWN-CLEAN`
        (:any:`bool`) Uses the first received topologies to reset the detected domains before shutdown.
    `SAP-xterms`
        (:any:`bool`) Initiates xterm windows for the SAPs.
    `NETWORK-OPTS`
        (:class:`dict`) Optional parameters directly given to the main :class:`Mininet` object at build time.
    `Controller`
        (:class:`dict`) Optional parameters directly given to the Mininet's :class:`Controller` object at build time.

        `ip`
            (:any:`string`) IP address of the internal OpenFlow controller used for the Mininet's components, e.g. ``127.0.0.1``
        `port`
            (:any:`int`) Port the internal OpenFlow controller listens on, e.g. ``6653``
    `EE`
        (:class:`dict`) Optional parameters directly given to the Mininet's :class:`EE` objects at build time.
    `Link`
        (:class:`dict`) Optional parameters directly given to the Mininet's :class:`Link` objects at build time.
    `SAP`
        (:class:`dict`) Optional parameters directly given to the Mininet's :class:`SAP` objects at build time.
    `Switch`
        (:class:`dict`) Optional parameters directly given to the Mininet's :class:`Switch` objects at build time.
    `FALLBACK-TOPO`
        (:class:`dict`) Defines fallback topology for the Infrastructure layer (only for development).

        `module`
            (:any:`string`) Python module name where `class` can be found, e.g. ``escape.infr.topology``
        `class`
            (:any:`string`) Python class name of the *Topology*, e.g. ``FallbackDynamicTopology``

Visualizations
^^^^^^^^^^^^^^
ESCAPE has an additional mechanism which collects the intermediate formats of a service request
and sends them to a remote database through a REST-API for visualization purposes.

The visualization feature can be enabled with the ``--visualization`` command line argument.

The `visualization` config section contains the connection parameters for the remote visualization.

Schematic config description:

    `url`
        (:any:`string`) Base URL of the remote database, e.g. ``http://localhost:8081``
    `rpc`
        (:any:`string`) The prefix of the collector RPC, e.g. ``edit-config``
    `params`
        Define URL params to the REST calls

        `instance_id`
            (:any:`string`) Optional distinguishing identification
    `headers`
        (:class:`dict`) Define specific HTTP headers to the REST calls