*api.py* module
===============

:any:`AbstractAPI` contains the register mechanism into the POX core for
layer APIs, the event handling/registering logic and defines the general
functions for initialization and finalization steps

:any:`RESTServer` is a general HTTP server which parse HTTP request and
forward to explicitly given request handler

:any:`AbstractRequestHandler` is a base class for concrete request handling.
It implements the general URL and request body parsing functions

Module contents
---------------

.. automodule:: escape.util.api
   :members:
   :private-members:
   :special-members:
   :exclude-members: __dict__,__weakref__,__module__
   :undoc-members:
   :show-inheritance:
