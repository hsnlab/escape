*adapters.py* module
====================

Contains Adapter classes which contains protocol and technology specific
details for the connections between ESCAPEv2 and other different domains.

Classes of the module:

.. inheritance-diagram::
   escape.adapt.adapters
   :parts: 1

:any:`TopologyLoadException` implements exception class for
topology-related errors.

:any:`InternalPOXAdapter` implements the OF controller functionality for the
Mininet-based emulated topology.

:any:`SDNDomainPOXAdapter` implements the OF controller functionality for the
external SDN/OpenFlow switches.

:any:`InternalMininetAdapter` implements Mininet related functionality
transparently e.g. start/stop/clean topology built from an :any:'NFFG'.

:any:`StaticFileAdapter` implements the main functions of reading from file.

:any:`VirtualizerBasedStaticFileAdapter` reads the topology information from
Virtualizer file.

:any:`StaticFileAdapter` implements the main functions of reading from file.

:any:`SDNDomainTopoAdapter` implements SDN topology related functions.

:any:`VNFStarterAdapter` is a helper/wrapper class for vnf_starter NETCONF
module.

:any:`UnifyRESTAdapter` is a wrapper class for the unified, REST-like
communication with the "Unify" domain which using pre-defined REST-API functions
and the "Virtualizer" XML-based format.

:any:`RemoteESCAPEv2RESTAdapter` is a wrapper class for REST-based communication
with an another ESCAPE instance started in agent mode.

:any:`OpenStackRESTAdapter` is a wrapper class for OpenStack-REST-like API
functions.

:any:`UniversalNodeRESTAdapter` is a wrapper class for REST-like communication
with the Universal Node domain.

:any:`BGPLSRESTAdapter` is a wrapper class for communicating with an external
component called TopologyManager using BGP-LS protocol with special extensions.

Module contents
---------------

.. automodule:: escape.adapt.adapters
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:

