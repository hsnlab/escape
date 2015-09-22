*ros_API.py* module
===================

Implements the platform and POX dependent logic for the Resource Orchestration
Sublayer.

.. inheritance-diagram::
   escape.orchest.ros_API.InstallNFFGEvent
   escape.orchest.ros_API.VirtResInfoEvent
   escape.orchest.ros_API.GetGlobalResInfoEvent
   escape.orchest.ros_API.InstantiationFinishedEvent
   escape.orchest.ros_API.ROSAgentRequestHandler
   escape.orchest.ros_API.ResourceOrchestrationAPI
   :parts: 3

:any:`InstallNFFGEvent` can send mapped NF-FG to the lower layer.

:any:`VirtResInfoEvent` can send back virtual resource info requested from
upper layer.

:any:`GetGlobalResInfoEvent` can request global resource info from lower layer.

:any:`InstantiationFinishedEvent` can signal info about NFFG instantiation.

:any:`ROSAgentRequestHandler` implements the REST-API functions for agent mode.

:any:`ResourceOrchestrationAPI` represents the ROS layer and implement all
related functionality.

Module contents
---------------

.. automodule:: escape.orchest.ros_API
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__,_eventMixin_events
   :undoc-members:
   :show-inheritance:


