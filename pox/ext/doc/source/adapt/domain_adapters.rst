*domain_adapters.py* module
===========================

:any:`DomainChangedEvent` signals changes for :any:`ControllerAdapter` in
an unified way.

:any:`AbstractDomainAdapter` contains general logic for actual Adapters.

:any:`POXDomainAdapter` implements POX related functionality.

:any:`MininetDomainAdapter` implements Mininet related functionality
transparently.

:any:`InternalDomainManager` represent the top class for interacting with
emulated infrastructure.

:any:`VNFStarterAPI` defines the interface for VNF management.

:any:`DirectMininetManager` implements  VNF management directly.

:any:`VNFStarterManager` is a wrapper class for vnf_starter NETCONF module.

:any:`OpenStackDomainAdapter` implements OpenStack related functionality.

:any:`DockerDomainAdapter` implements Docker related functionality.

Module contents
---------------

.. automodule:: escape.adapt.domain_adapters
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:

