*managers.py* module
====================

Contains Manager classes which contains the higher-level logic for complete
domain management.

Uses Adapter classes for ensuring protocol-specific connections with entities in
the particular domain.

.. figure::  ../_static/components.png
     :align:  center

:any:`InternalDomainManager` represent the top class for interacting with the
emulated infrastructure.

:any:`RemoteESCAPEDomainManager` ensures the connection with a different ESCAPE
instance started in agent mode.

:any:`OpenStackDomainManager` implements the related functionality for managing
the OpenStack-based domain.

:any:`UniversalNodeDomainManager` implements the related functionality for
managing the domain based on the Universal Node conception.

:any:`DockerDomainManager` is a placeholder class for managing Docker-based
network entities.

:any:`SDNDomainManager` interacts and handles legacy OpenFlow 1.0 switches
aggregated into a separate domain.


Module contents
---------------

.. automodule:: escape.adapt.managers
     :members:
     :private-members:
     :special-members:
     :exclude-members: __dict__,__weakref__,__module__
     :undoc-members:
     :show-inheritance:

