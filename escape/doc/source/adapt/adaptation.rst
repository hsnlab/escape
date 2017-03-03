*adaptation.py* module
======================

Contains classes relevant to the main adaptation function of the Controller
Adaptation Sublayer.

Classes of the module:

.. inheritance-diagram::
   escape.adapt.adaptation
   :parts: 1

:class:`ComponentConfigurator` creates, initializes, stores and manages different
adaptation components, i.e. derived classes of :class:`AbstractDomainManager` and
:class:`AbstractESCAPEAdapter`.

:class:`ControllerAdapter` implements the centralized functionality of high-level
adaptation and installation of :class:`NFFG`.

:class:`GlobalResourceManager` stores and manages the global Virtualizer.

Module contents
---------------

.. automodule:: escape.adapt.adaptation
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:

