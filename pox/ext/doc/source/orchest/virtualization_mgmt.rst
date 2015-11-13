*virtualization_mgmt.py* module
===============================

Contains components relevant to virtualization of resources and views.

.. inheritance-diagram::
   escape.orchest.virtualization_mgmt.MissingGlobalViewEvent
   escape.orchest.virtualization_mgmt.AbstractVirtualizer
   escape.orchest.virtualization_mgmt.GlobalViewVirtualizer
   escape.orchest.virtualization_mgmt.SingleBiSBiSVirtualizer
   escape.orchest.virtualization_mgmt.VirtualizerManager
   :parts: 1

:any:`MissingGlobalViewEvent` can signal missing global view.

:any:`AbstractVirtualizer` contains the central logic of Virtualizers.

:any:`GlobalViewVirtualizer` implements a non-filtering/non-virtualizing logic.

:any:`SingleBiSBiSVirtualizer` implement the default, 1-Bis-Bis virtualization
logic of the Resource Orchestration Sublayer.

:any:`VirtualizerManager` stores and handles the virtualizers.

Module contents
---------------

.. automodule:: escape.orchest.virtualization_mgmt
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:
