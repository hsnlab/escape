*virtualization.py* module
==========================

Contains components relevant to virtualization of resources and views.

Classes of the module:

.. inheritance-diagram::
   escape.adapt.virtualization
   :parts: 1

:any:`DoVChangedEvent` can signal for the specific Virtualizers the DOV is
changed.

:any:`MissingGlobalViewEvent` can signal missing global view.

:any:`AbstractVirtualizer` contains the basic logic and defines the API of
Virtualizers.

:any:`AbstractFilteringVirtualizer` contains the main logic for observing
global Virtualizer.

:any:`DomainVirtualizer` implements the standard virtualization/generalization
logic of the Resource Orchestration Sublayer.

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
