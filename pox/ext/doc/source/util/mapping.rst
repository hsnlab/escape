*mapping.py* module
===================

Contains abstract classes for NFFG mapping.

.. inheritance-diagram::
   escape.util.mapping.AbstractMapper
   escape.util.mapping.AbstractMappingStrategy
   escape.util.mapping.AbstractOrchestrator
   :parts: 3

:any:`AbstractMapper` is an abstract class for orchestration method which
should implement mapping preparations and invoke actual mapping algorithm.

:any:`AbstractMappingStrategy` is an abstract class for containing entirely
the mapping algorithm as a class method.

:any:`AbstractOrchestrator` implements the common functionality for
orchestrators in different layers.

Module contents
---------------

.. automodule:: escape.util.mapping
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:


