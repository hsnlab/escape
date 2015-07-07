Welcome to ESCAPEv2's documentation!
====================================

Welcome! This is the API documentation for **ESCAPEv2**.

Overview
--------

`Mininet <http://mininet.org/>`_ is a great prototyping tool which takes
existing SDN-related software components (e.g. Open vSwitch, OpenFlow
controllers, network namespaces, cgroups, etc.) and combines them into a
framework, which can automatically set up and configure customized OpenFlow
testbeds scaling up to hundreds of nodes. Standing on the shoulders of Mininet,
we have implemented a similar prototyping system called ESCAPE, which can be
used to develop and test various components of the service chaining
architecture. Our framework incorporates
`Click <http://www.read.cs.ucla.edu/click/>`_ for implementing Virtual Network
Functions (VNF), NETCONF (:rfc:`6241`) for managing Click-based VNFs and
`POX <https://openflow.stanford.edu/display/ONL/POX+Wiki>`_ for taking care of
traffic steering. We also add our extensible Orchestrator module, which can
accommodate mapping algorithms from abstract service descriptions to deployed
and running service chains.

.. seealso::
    The source code of previous ESCAPE version is available at our `github page
    <https://github.com/nemethf/escape>`_. For more information we first suggest
    to read our paper:

    Attila Csoma, Balazs Sonkoly, Levente Csikor, Felician Nemeth, Andras Gulyas,
    Wouter Tavernier, and Sahel Sahhaf: **ESCAPE: Extensible Service ChAin
    Prototyping Environment using Mininet, Click, NETCONF and POX**.
    Demo paper at Sigcomm'14.

    * `Download the paper <http://dl.acm.org/authorize?N71297>`_
    * `Accompanying poster <http://sb.tmit.bme.hu/mediawiki/images/b/ba/Sigcomm2014_poster.png>`_

    For further information contact csoma@tmit.bme.hu, sonkoly@tmit.bme.hu

ESCAPEv2 structure
------------------

Dependencies:
+++++++++++++

.. code-block:: bash

  $ sudo apt-get install libxml2 libxslt1-dev python-setuptools python-pip \
  python-paramiko python-lxml python-libxml2 python-libxslt1

  sudo pip install networkx ncclient requests

Class structure
+++++++++++++++

.. toctree::
    :maxdepth: 1

    ESCAPEv2 <top>

Main modules for layers/sublayers
+++++++++++++++++++++++++++++++++

.. toctree::
    :maxdepth: 3

    UNIFY <unify>

README
++++++

ESCAPEv2 example commands

**The simpliest use-case:**

.. code-block:: bash

    $ ./escape.py

Usage:

.. code-block:: bash

    $ ./escape.py -h
    usage: escape.py [-h] [-v] [-d] [-f] [-i]

    ESCAPE: Extensible Service ChAin Prototyping Environment using Mininet, Click,
    NETCONF and POX

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         show program's version number and exit

    ESCAPE arguments:
      -c path, --config path
                            override default config filename
      -d, --debug           run the ESCAPE in debug mode
      -f, --full            run the infrastructure layer also
      -i, --interactive     run an interactive shell for observing internal states


**More advanced commands:**

Basic command:

.. code-block:: bash

    $ ./pox.py unify

One of a basic commands for debugging:

.. code-block:: bash

    $ ./pox.py --verbose unify py

For forcing to log on DEBUG level the ``--verbose`` flag of the ``pox.py``
script can be used. Or the log.level POX module can be used which would be the
preferred way. E.g.:

.. code-block:: bash

    $ ./pox.py --verbose <modules>
    $ ./pox.py log.level --DEBUG <modules>

Basic command to initiate a built-in emulated network for testing:

.. code-block:: bash

    # Infrastructure layer requires root privileges due to use of Mininet!
    $ sudo ./pox.py unify --full

Minimal command with explicitly-defined components (components' order is
irrelevant):

.. code-block:: bash

    $ ./pox.py service orchestration adaptation

Without service layer:

.. code-block:: bash

    $ ./pox.py orchestration adaptation

With infrastructure layer:

.. code-block:: bash

    $ sudo ./pox.py service orchestration adaptation --with_infr infrastructure

Long version with debugging and explicitly-defined components (analogous with
``./pox.py unify --full``):

.. code-block:: bash

     $ sudo ./pox.py --verbose log.level --DEBUG samples.pretty_log service \
     orchestration adaptation --with_infr infrastructure

Start layers with graph-represented input contained in a specific file:

.. code-block:: bash

    $ ./pox.py service --sg_file=<path> ...
    $ ./pox.py unify --sg_file=<path>

    $ ./pox.py orchestration --nffg_file=<path> ...
    $ ./pox.py adaptation --mapped_nffg_file=<path> ...

Start ESCAPEv2 with built-in GUI:

.. code-block:: bash

    $ ./pox.py service --gui ...
    $ ./pox.py unify --gui

Start layer in standalone mode (no dependency check and handling) for test/debug:

.. code-block:: bash

    $ ./pox.py service --standalone
    $ ./pox.py orchestration --standalone
    $ ./pox.py adaptation --standalone
    $ sudo ./pox.py infrastructure --standalone

    $ ./pox.py service orchestration --standalone

REST API
++++++++

*Content Negotiation:* The Service layer's RESTful API accepts and returns data only in JSON format.

*Operations:*   Every operation need to be called under the **escape/** path. E.g. *http://localhost/escape/version*

+-------------------+----------------+-------------------+-----------------------------------------------------------------------------------+
|      Path         |     Params     |     HTTP verbs    | Description                                                                       |
+===================+================+===================+===================================================================================+
| */version*        | ``None``       | GET               | Returns with the current version of ESCAPEv2                                      |
+-------------------+----------------+-------------------+-----------------------------------------------------------------------------------+
| */echo*           | ``ANY``        | ALL               | Returns with the given parameters                                                 |
+-------------------+----------------+-------------------+-----------------------------------------------------------------------------------+
| */operations*     | ``None``       | GET               | Returns with the implemented operations as a list                                 |
+-------------------+----------------+-------------------+-----------------------------------------------------------------------------------+
| */sg*             | ``NFFG``       | POST              | Initiate given NFFG. Returns the given NFFG initiation is accepted or not.        |
+-------------------+----------------+-------------------+-----------------------------------------------------------------------------------+

Configuration
+++++++++++++

ESCAPEv2 has a default configuration under the `escape` package (in the
`__init__.py` file as `cfg`). This configuration is used as the running config
also. This config also contains the necessary information for component
instantiation and initialization.

To override some of the parameters you can change it in the `cfg` directly (not
preferred) or you can define it in the additional config file: `escape.config`.
The ESCAPEv2 checks this file at every start, and update/override the internal
config if it"s necessary. The config file can be changed during start with the
`--config` initial parameter.

Development
+++++++++++

Suggested IDE: Pycharm Community Edition `Pycharm Community Edition <https://www.jetbrains.com/pycharm/>`_

Coding conventions:

* Sizes:
    * Tab size: 2
    * Indent: 2
    * Continuation indent: 5
    * Right margin (columns): 80
* Use spaces instead of tab characters
* Use one space before method declaration parentheses
* Use spaces around operators
* Not use spaces in named parameters and keywords argument
* Use double blank lines around classes and top-level functions

Debugging
+++++++++

You can use PyCharm for debugging. In this case you have to specify a new Python
interpreter using the *python_root_debugger.sh* script to be able to run ESCAPE
with root privileges.

You can use POX's *py* stock component also which open an interactive Python
shell. With that you can observe the internal state of the running ESCAPE
instance, experiment or even call different functions.

POX uses a topmost object called *core* which serves a rendezvous point between
POX's components (e.g. our components representing the UNIFY layers). Through
that object we can reach every registered object easily.
E.g. to shut down the REST API of the Service layer manually we can use the
following function call:

.. code-block:: python

  $ Ready.
  $ POX>
  $ POX> core.service.rest_api.stop()

One instance of the *ESCAPEInteractiveHelper* is registered by default under the
name: *helper*. An example to dump the running configuration of ESCAPEv2:

.. code-block:: python

  $ POX> core.helper.config()
    {
        "infrastructure": {
            "NETWORK-OPTS": null,
            "FALLBACK-TOPO": {
                "class": "BackupTopology",
                "module": "escape.infr.topology"
    ...

More help and description about the useful helper functions and the *core*
object is in the comments/documentation and on the POX's `wiki <https://openflow.stanford.edu/display/ONL/POX+Wiki#POXWiki-POXAPIs>`_
site.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

