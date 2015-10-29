*mapping.py* module
===================

Contains abstract classes for NFFG mapping.

.. inheritance-diagram::
   escape.util.mapping.AbstractMapper
   escape.util.mapping.AbstractMappingStrategy
   escape.util.mapping.AbstractOrchestrator
   escape.util.mapping.ProcessorError
   escape.util.mapping.AbstractMappingDataProcessor
   escape.util.mapping.ProcessorSkipper
   escape.util.mapping.PrePostMapNotifier
   escape.util.mapping.PreMapEvent
   escape.util.mapping.PostMapEvent
   :parts: 3

:any:`AbstractMappingStrategy` is an abstract class for containing entirely
the mapping algorithm as a class method.

:any:`ProcessorError` can signal unfulfilled requirements.

:any:`AbstractMappingDataProcessor` is an abstract class to implement pre and
post processing functions right before/after the mapping.

:any:`ProcessorSkipper` is a dummy implementation to skip processing.

:any:`PrePostMapNotifier` is a simple processor implementation to notify external
entities about pre/post mapping.

:any:`PreMapEvent` can signal pre mapping event.

:any:`PostMapEvent` can signal post mapping event.

:any:`AbstractMapper` is an abstract class for orchestration method which
should implement mapping preparations and invoke actual mapping algorithm.

:any:`AbstractOrchestrator` implements the common functionality for
orchestrator's in different layers.

Module contents
---------------

.. automodule:: escape.util.mapping
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:


