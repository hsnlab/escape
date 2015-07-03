*domain.py* module
==================

Implement the supporting classes for domain adapters.

:any:`DomainChangedEvent` signals changes for :any:`ControllerAdapter` in
an unified way.

:any:`DeployEvent` can send NFFG to Infrastructure layer for deploying.

:any:`AbstractDomainManager` contains general logic for top domain managers.

:any:`AbstractDomainAdapter` contains general logic for actual Adapters.

:any:`VNFStarterAPI` defines the interface for VNF management based on
VNFStarter YANG description.

:any:`OpenStackAPI` defines the interface for communication with OpenStack
domain.

:any:`AbstractRESTAdapter` contains the general functions for communication
through an HTTP/RESTful API.

Requirements::

  sudo pip install requests


Module contents
---------------

.. automodule:: escape.util.domain
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:
