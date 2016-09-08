*domain.py* module
==================

Implement the supporting classes for domain adapters.

Classes of the module:

.. inheritance-diagram::
   escape.util.domain
   :parts: 1

:any:`DomainChangedEvent` signals changes for :any:`ControllerAdapter` in
an unified way.

:any:`DeployEvent` can send NFFG to Infrastructure layer for deploying.

:any:`AbstractDomainManager` contains general logic for top domain managers.

:any:`AbstractRemoteDomainManager` contains polling functionality for remote
domains.

:any:`AbstractESCAPEAdapter` contains general logic for actual Adapters.

:any:`AbstractOFControllerAdapter` contains general logic for actual OF
controller based Adapters.

:any:`DefaultUnifyDomainAPI` defines unified interface for domain's REST-API.

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

Requirements:

.. code-block:: bash

   $ sudo pip install requests

Module contents
---------------

.. automodule:: escape.util.domain
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:
