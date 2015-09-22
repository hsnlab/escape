*pox_extension.py* module
=========================

Override and extend internal POX components to achieve ESCAPE-desired behaviour.

.. inheritance-diagram::
   escape.util.pox_extension.OpenFlowBridge
   escape.util.pox_extension.ExtendedOFConnectionArbiter
   escape.util.pox_extension.ESCAPEInteractiveHelper
   :parts: 3

:any:`OpenFlowBridge` is a special version of OpenFlow event originator class.

:any:`ExtendedOFConnectionArbiter` dispatches incoming OpenFlow connections to
fit ESCAPEv2.

:any:`ESCAPEInteractiveHelper` contains helper function for debugging.

Module contents
---------------

.. automodule:: escape.util.pox_extension
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:
