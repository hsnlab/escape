*virtualization.py* module
==========================

Contains components relevant to virtualization of resources and views.

.. inheritance-diagram::
   escape.adapt.virtualization.MissingGlobalViewEvent
   escape.adapt.virtualization.DoVChangedEvent
   escape.adapt.virtualization.AbstractVirtualizer
   escape.adapt.virtualization.AbstractFilteringVirtualizer
   escape.adapt.virtualization.DomainVirtualizer
   escape.adapt.virtualization.GlobalViewVirtualizer
   escape.adapt.virtualization.SingleBiSBiSVirtualizer
   escape.adapt.virtualization.VirtualizerManager
   :parts: 1

:any:`MissingGlobalViewEvent` can signal missing global view.

:any:`DoVChangedEvent` can signal for the specific Virtualizers the DOV is
changed.

:any:`AbstractVirtualizer` contains the basic logic and defines the API of
Virtualizers.

:any:`AbstractFilteringVirtualizer` contains the main logic for observing
global Virtualizer.

:any:`GlobalViewVirtualizer` implements a non-filtering/non-virtualizing logic.

:any:`SingleBiSBiSVirtualizer` implement the default, 1-Bis-Bis virtualization
logic of the Resource Orchestration Sublayer.

:any:`VirtualizerManager` stores and handles the virtualizers.

Module contents
---------------

.. automodule:: escape.adapt.virtualization
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:
