*cas_API.py* module
===================

Implements the platform and POX dependent logic for the Controller Adaptation
Sublayer.

.. inheritance-diagram::
   escape.adapt.cas_API.GlobalResInfoEvent
   escape.adapt.cas_API.InstallationFinishedEvent
   escape.adapt.cas_API.DeployNFFGEvent
   escape.adapt.cas_API.ControllerAdaptationAPI
   :parts: 3

:any:`GlobalResInfoEvent` can send back global resource info requested from
upper layer.

:any:`InstallationFinishedEvent` can send back status about the NFFG
installation.

:any:`DeployNFFGEvent` can send NFFG to Infrastructure layer for deploying.

:any:`ControllerAdaptationAPI` represents the CAS layer and implement all
related functionality.

Module contents
---------------

.. automodule:: escape.adapt.cas_API
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__,_eventMixin_events
   :undoc-members:
   :show-inheritance:

