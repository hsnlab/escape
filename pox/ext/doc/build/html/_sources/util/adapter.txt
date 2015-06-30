*adapter.py* module
===================

:any:`DomainChangedEvent` signals changes for :any:`ControllerAdapter` in
an unified way.

:any:`AbstractDomainManager` contains general logic for top domain managers

:any:`AbstractDomainAdapter` contains general logic for actual Adapters.

:any:`VNFStarterAPI` defines the interface for VNF management based on
VNFStarter YANG description.

:any:`OpenStackAPI` defines the interface for communication with OpenStack
domain.

Requirements::

  sudo pip install requests

:any:`AbstractRESTAdapter` contains the general functions for communication
through an HTTP/RESTful API

Module contents
---------------

.. automodule:: escape.util.adapter
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:
