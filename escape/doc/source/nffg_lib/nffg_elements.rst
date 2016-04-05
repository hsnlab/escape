*nffg_elements.py* module
=========================

Element classes for NFFG based on ``nffg.yang``.

.. inheritance-diagram::
   escape.nffg_lib.nffg_elements.NFFGModel
   escape.nffg_lib.nffg_elements.Persistable
   escape.nffg_lib.nffg_elements.Element
   escape.nffg_lib.nffg_elements.PortContainer
   escape.nffg_lib.nffg_elements.Node
   escape.nffg_lib.nffg_elements.Link
   escape.nffg_lib.nffg_elements.NodeResource
   escape.nffg_lib.nffg_elements.Flowrule
   escape.nffg_lib.nffg_elements.Port
   escape.nffg_lib.nffg_elements.InfraPort
   escape.nffg_lib.nffg_elements.NodeNF
   escape.nffg_lib.nffg_elements.NodeSAP
   escape.nffg_lib.nffg_elements.NodeInfra
   escape.nffg_lib.nffg_elements.EdgeLink
   escape.nffg_lib.nffg_elements.EdgeSGLink
   escape.nffg_lib.nffg_elements.EdgeReq
   :parts: 1

:any:`NFFGModel` represents the main container class.

:any:`Persistable` ensures the basic parse/dump functionality.

:any:`Element` represents the common functions for elements.

:any:`Node` represents the common functions for Node elements.

:any:`Link` represents the common functions for Edge elements.

:any:`NodeResource` represents the resource attributes of a Node.

:any:`Flowrule` represents the attributes of a flowrule.

:any:`Port` represents a port of a Node.

:any:`InfraPort` extends the port capabilities for the Infrastructure Node.

:any:`NodeNF` defines the NF type of Node.

:any:`NodeSAP` defines the SAP type of Node.

:any:`NodeInfra` defines the Infrastructure type of Node.

:any:`EdgeLink` defines the dynamic and static connections between Nodes.

:any:`EdgeSGLink` defines the connection between SG elements.

:any:`EdgeReq` defines the requirements between SG elements.

Module contents
---------------

.. automodule:: escape.nffg_lib.nffg_elements
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:
