*domain.py* module
==================

Implement the supporting classes for domain adapters.

.. inheritance-diagram::
   escape.util.domain.DomainChangedEvent
   escape.util.domain.DeployEvent
   escape.util.domain.AbstractDomainManager
   escape.util.domain.AbstractESCAPEAdapter
   escape.util.domain.DefaultDomainRESTAPI
   escape.util.domain.VNFStarterAPI
   escape.util.domain.OpenStackAPI
   escape.util.domain.UniversalNodeAPI
   escape.util.domain.RemoteESCAPEv2API
   escape.util.domain.AbstractRESTAdapter
   :parts: 3

:any:`DomainChangedEvent` signals changes for :any:`ControllerAdapter` in
an unified way.

:any:`DeployEvent` can send NFFG to Infrastructure layer for deploying.

:any:`AbstractDomainManager` contains general logic for top domain managers.

:any:`AbstractESCAPEAdapter` contains general logic for actual Adapters.

:any:`DefaultDomainRESTAPI` defines unified interface for domain's REST-API.

:any:`VNFStarterAPI` defines the interface for VNF management based on
VNFStarter YANG description.

:any:`OpenStackAPI` defines the interface for communication with OpenStack
domain.

:any:`UniversalNodeAPI` defines the interface for communication with Universal
Node domain.

:any:`RemoteESCAPEv2API` defines the interface for communication with a remote
ESCAPE instance started in agent mode.

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
