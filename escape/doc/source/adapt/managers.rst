*managers.py* module
====================

Contains Manager classes which contains the higher-level logic for complete
domain management.

Uses Adapter classes for ensuring protocol-specific connections with entities in
the particular domain.

Classes of the module:

.. inheritance-diagram::
   escape.adapt.managers
   :parts: 1

:any:`GetLocalDomainViewEvent` implements an event for requesting the
Global View (DoV).

:any:`InternalDomainManager` represent the top class for interacting with the
emulated infrastructure.

:any:`SDNDomainManager` interacts and handles legacy OpenFlow 1.0 switches
aggregated into a separate domain.

:any:`RemoteESCAPEDomainManager` ensures the connection with a different ESCAPE
instance started in agent mode.

:any:`UnifyDomainManager` is a common parent class for DomainManagers
supervising "Unify" domains.

:any:`OpenStackDomainManager` implements the related functionality for managing
the OpenStack-based domain.

:any:`UniversalNodeDomainManager` implements the related functionality for
managing the domain based on the Universal Node conception.

:any:`ExternalDomainManager` implements the related functionality for
managing/detecting external domain from other providers.

:any:`BGPLSBasedExternalDomainManager` implements an external manager which uses
the TopologyManager component to detect external domains though BGP-LS protocol.

Module contents
---------------

.. automodule:: escape.adapt.managers
     :members:
     :private-members:
     :special-members:
     :exclude-members: __dict__,__weakref__,__module__
     :undoc-members:
     :show-inheritance:

