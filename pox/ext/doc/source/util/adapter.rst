*adapter.py* module
===================

:any:`DomainChangedEvent` signals changes for :any:`ControllerAdapter` in
an unified way.

:any:`AbstractNETCONFAdapter` contains the main function for communication
over NETCONF such as managing SSH channel, handling configuration, assemble
RPC request and parse RPC reply

:any:`AbstractDomainAdapter` contains general logic for actual Adapters.

:any:`VNFStarterAPI` defines the interface for VNF management.

Module contents
---------------

.. automodule:: escape.util.adapter
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:
