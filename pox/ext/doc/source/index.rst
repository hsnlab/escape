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

Class structure
+++++++++++++++

.. toctree::
    :maxdepth: 1

    ESCAPEv2 <escape>

Top module
++++++++++

.. toctree::
    :maxdepth: 1

    UNIFY <unify>

Main modules for layers/sublayers
+++++++++++++++++++++++++++++++++

.. toctree::
    :maxdepth: 1

          Service layer <service>
          Resource Orchestration sublayer <orchestration>
          Controller Adaptation sublayer <adaptation>

README
++++++

ESCAPEv2 starting commands

Basic command:

.. code-block:: bash

    $ ./pox.py unify

Basic command for debugging:

.. code-block:: bash

    $ ./pox.py --verbose --no-openflow unify py

Minimal command with explicitly-defined components (components' order is irrelevant):

.. code-block:: bash

    $ ./pox.py service orchestration adaptation

Without the service layer:

.. code-block:: bash

    $ ./pox.py orchestration adaptation

Long version with debugging and explicitly-defined components (analogous with ./pox.py unify):

.. code-block:: bash

     $./pox.py --verbose log.level --DEBUG samples.pretty_log service orchestration adaptation

Start layers with graph-represented input contained in a specific file:

.. code-block:: bash

    $ ./pox.py service --sg_file=<path>
    $ ./pox.py unify --sg_file=<path>

    $ ./pox.py orchestration --nffg_file=<path>
    $ ./pox.py adaptation --mapped_nffg_file=<path>

Start ESCAPEv2 with built-in GUI:

.. code-block:: bash

    $ ./pox.py service --gui ...
    $ ./pox.py unify --gui

Start layer in standalone mode (no dependency handling) for test/debug:

.. code-block:: bash

    $ ./pox.py service --standalone
    $ ./pox.py orchestration --standalone
    $ ./pox.py adaptation --standalone

    $ ./pox.py service orchestration --standalone

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

