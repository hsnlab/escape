*nffg_elements.py* module
=========================

Element classes for NFFG based on ``nffg.yang``.

.. inheritance-diagram::
   escape.util.nffg_elements.NFFGModel
   escape.util.nffg_elements.Persistable
   escape.util.nffg_elements.Element
   escape.util.nffg_elements.PortContainer
   escape.util.nffg_elements.Node
   escape.util.nffg_elements.Link
   escape.util.nffg_elements.NodeResource
   escape.util.nffg_elements.Flowrule
   escape.util.nffg_elements.Port
   escape.util.nffg_elements.InfraPort
   escape.util.nffg_elements.NodeNF
   escape.util.nffg_elements.NodeSAP
   escape.util.nffg_elements.NodeInfra
   escape.util.nffg_elements.EdgeLink
   escape.util.nffg_elements.EdgeSGLink
   escape.util.nffg_elements.EdgeReq
   :parts: 3

:any:`NFFGModel` represents the main container class.

:any:`Persistable` ensures the basic parse/dump functionality.

:any:`Element` represents the common functions for elements.

:any:`PortContainer` can contain :any:`Port` objects.

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

.. automodule:: escape.util.nffg_elements
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:
