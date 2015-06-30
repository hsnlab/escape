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
      -h, --help         show this help message and exit
      -v, --version      show program's version number and exit

    ESCAPE arguments:
      -d, --debug        run the ESCAPE in debug mode
      -f, --full         run the infrastructure layer also
      -i, --interactive  run an interactive shell for observing internal states

**More advanced commands:**

Basic command:

.. code-block:: bash

    $ ./pox.py unify

Basic command for debugging:

.. code-block:: bash

    $ ./pox.py --verbose --no-openflow unify py

Basic command to initiate a built-in emulated network for testing:

.. code-block:: bash

    # Infrastructure layer requires root privileges due to use of Mininet!
    $ sudo ./pox.py unify --full

Minimal command with explicitly-defined components (components' order is irrelevant):

.. code-block:: bash

    $ ./pox.py service orchestration adaptation

Without service layer:

.. code-block:: bash

    $ ./pox.py orchestration adaptation

With infrastructure layer:

.. code-block:: bash

    $ sudo ./pox.py service orchestration adaptation --with_infr infrastructure

Long version with debugging and explicitly-defined components (analogous with ./pox.py unify --full):

.. code-block:: bash

     $./pox.py --verbose log.level --DEBUG samples.pretty_log service orchestration adaptation--with_infr infrastructure

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

Start layer in standalone mode (no dependency handling) for test/debug:

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

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

