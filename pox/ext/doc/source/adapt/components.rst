*components.py* module
======================

Contains component classes which represent the connections between ESCAPEv2 and
other different domains and manage the interactions.

.. figure::  ../_static/components.png
   :align:  center

:any:`POXDomainAdapter` implements POX related functionality.

:any:`MininetDomainAdapter` implements Mininet related functionality
transparently.

:any:`VNFStarterAdapter` is a wrapper class for vnf_starter NETCONF module.

:any:`OpenStackRESTAdapter` is a wrapper class for OpenStack-RESTlike API
functions.

:any:`InternalDomainManager` represent the top class for interacting with
emulated infrastructure.

:any:`OpenStackDomainManager` implements OpenStack related functionality.

:any:`DockerDomainManager` implements Docker related functionality.

Module contents
---------------

.. automodule:: escape.adapt.components
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:

