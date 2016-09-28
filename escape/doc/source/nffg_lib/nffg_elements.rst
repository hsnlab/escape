*nffg_elements.py* module
=========================

Element classes for NFFG based on ``nffg.yang``.

Classes of the module:

.. inheritance-diagram::
   escape.nffg_lib.nffg_elements
   :parts: 1

:any:`Persistable` ensures the basic parse/dump functionality.

:any:`Element` represents the common functions for elements.

:any:`L3Address` represents L3 address.

:any:`L3AddressContainer` implements a container for :any:`L3Address` objects.

:any:`Port` represents a port of a Node.

:any:`PortContainer` implements a container for :any:`Port` objects.

:any:`Node` represents the common functions for Node elements.

:any:`Link` represents the common functions for Edge elements.

:any:`NodeResource` represents the resource attributes of a Node.

:any:`Flowrule` represents the attributes of a flowrule.

:any:`InfraPort` extends the port capabilities for the Infrastructure Node.

:any:`NodeNF` defines the NF type of Node.

:any:`NodeSAP` defines the SAP type of Node.

:any:`NodeInfra` defines the Infrastructure type of Node.

:any:`EdgeLink` defines the dynamic and static connections between Nodes.

:any:`EdgeSGLink` defines the connection between SG elements.

:any:`EdgeReq` defines the requirements between SG elements.

:any:`NFFGParseError` implements an exception for specific parsing errors.

:any:`NFFGModel` represents the main container class.

Module contents
---------------

.. automodule:: escape.nffg_lib.nffg_elements
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:
