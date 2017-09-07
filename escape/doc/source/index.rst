####################################
Welcome to ESCAPEv2's documentation!
####################################

Overview
========

On the one hand, ESCAPE (Extensible Service ChAin Prototyping Environment) is a
general prototyping framework which supports the development of several parts of
the service chaining architecture including VNF implementation, traffic steering,
virtual network embedding, etc.  On the other hand, ESCAPE is a proof of concept
prototype implementing a novel SFC (Service Function Chaining) architecture proposed
by `EU FP7 UNIFY project <https://www.fp7-unify.eu/>`__.
It is a realization of the UNIFY service programming and orchestration framework
which enables the joint programming and virtualization of cloud and networking
resources.

The main scope of ESCAPE as a multi-domain orchestrator (MdO) is to
discover, detect and manage infrastructure domains using different
technologies.

ESCAPE receives the specific service requests on its REST-like API,
orchestrate the requested Service Function Chains on the full resource
view (which is constructed automatically based on the information
gathered from lower level domains) making use of a dedicated resource
mapping algorithm and propagate the calculated service parts to the
corresponding Domain Orchestrators (DO).

In addition, ESCAPE can be used in the role of a local Domain
Orchestrator when an extended version of Mininet network emulation
platform is used as an infrastructure which is able to run Network
Functions and realize dataplane connectivity.

.. tip::

   For more information on the concept, motivation and demo use-cases, we
   suggest the following papers.

   **UNIFY Architecture:**

   * Balázs Sonkoly, Robert Szabo, Dávid Jocha, János Czentye, Mario
     Kind, and Fritz-Joachim Westphal, *UNIFYing Cloud and Carrier
     Network Resources: An Architectural View*, In Proceedings of IEEE Global
     Telecommunications Conference (GLOBECOM), 2015.

   **ESCAPE as a multi-domain orchestrator:**

   * Balázs Sonkoly, János Czentye, Robert Szabo, Dávid Jocha, János
     Elek, Sahel Sahhaf, Wouter Tavernier, Fulvio Risso,
     *Multi-domain service orchestration over networks and clouds: a
     unified approach*, In Proceedings of ACM SIGCOMM (Demo), August
     17-21, 2015, London, United Kingdom.  `Download the paper
     <http://conferences.sigcomm.org/sigcomm/2015/pdf/papers/p377.pdf>`__
   * `Demo video <https://www.youtube.com/watch?v=T3Fna5v-hFw>`__
   * `Demo video as a presentation with manual control
     <http://prezi.com/f-ms1rwxxdwa/?utm_campaign=share&utm_medium=copy&rc=ex0share>`__

   **Previous version of ESCAPE:**

   * Attila Csoma, Balázs Sonkoly, Levente Csikor, Felicián Németh,
     András Gulyás, Wouter Tavernier, Sahel Sahhaf, *ESCAPE: Extensible
     Service ChAin Prototyping Environment using Mininet, Click, NETCONF
     and POX*, In Proceedings of ACM SIGCOMM (Demo), August 17-22, 2014,
     Chicago, IL, USA.  `Download the paper
     <http://dl.acm.org/authorize?N71297>`__
   * The source code of the previous version of ESCAPE is available at
     our `github page <https://github.com/nemethf/escape>`__.

For further information contact balazs.sonkoly@tmit.bme.hu

Installation
============

Setup scripts
-------------

The ``install_dep.sh`` script is responsible for managing the dependencies. It sets up
the required sym-links, updates the related submodules and installs only the necessary
packages regarding the given install parameters in one step.

.. note::

    The installation steps are detailed in the following chapter: :ref:`install_steps`.

If you don't want to use the complex install script or the included project setup script
then just create a sym-link to the relevant gitmodules file with the name ``.gitmodules``,
update the submodules

.. code-block:: bash

    $ ln -vfs .gitmodules.<PROJECT> .gitmodules
    $ git submodules update --init

and install the dependencies manually.

As the core layers of ESCAPE relies on POX and written in Python there is no need
for explicit compiling or installation. The required libraries and dependencies such as
external databases and programs, system packages and the latest Python 2.7 interpreter
are completely handled and installed by the main setup script.

The currently recommended Python version, in which the development and mostly the
testing are performed, is the standard CPython **2.7.13**.

.. important::

  Only the standard CPython interpreter is tested and supported!

If for some reason a different version of Python is desired, check the Virtual
Environment section below.

The best choice of platform on which ESCAPE is recommended to be installed and
the ``install-dep.sh`` installation script is tested on Ubuntu **16.04.3** LTS.

In case of installing ESCAPE as a Local Orchestrator, check the :doc:`sub/install_issues`.

.. _install_steps:

The preferred way
-----------------

1. Download one of pre-build Ubuntu LTS VM image, create one in your preferred VM
manager or just use the default Docker image of Ubuntu.

2. Create the ``~/.ssh`` folder in your environment and copy your private RSA key
you have given on the *GitLab* site, with the name ``id_rsa``.
If you use a VM image then the following commands can be used to copy your RSA key from your host:

.. code-block:: bash

    $ cd
    $ mkdir .ssh
    $ scp <your_user>@<host_ip>:~/.ssh/<your_ssh_key> ~/.ssh/id_rsa
    $ sudo chmod 700 .ssh && sudo chmod 600 .ssh/id_rsa

3. Clone the shared escape repository
(the default folder name will be: *escape*).

.. code-block:: bash

    $ git clone <git repo URL> escape

4. Install the necessary dependencies with the ``install_dep.sh`` script (system
and Python packages, optionally the OpenYuma with VNFStarter module, etc.):

.. code-block:: bash

    $ cd escape
    $ ./install_dep.sh

Usage:

.. code-block:: text

    $ ./install-dep.sh -h
        Detected platform is Ubuntu, version: 16.04!
        User project config: N/A
        Usage: ./install-dep.sh [-c] [-d] [-g] [-h] [-i] [-p project]
        Install script for ESCAPEv2

        options:
            -c:   (default) install (C)ore dependencies for Global Orchestration
            -d:   install additional dependencies for (D)evelopment and test tools
            -g:   install dependencies for our rudimentary (G)UI (deprecated)
            -h:   print this (H)elp message
            -i:   install components of (I)nfrastructure Layer
                for Local Orchestration (deprecated)
            -p:   explicitly setup project name based on: .gitmodules.<name>
                instead of automatic detection

In a high level, the script above takes care of the following things:

* Setup sym-links and submodules for given project name
* Install the necessary system and Python packages

In case of an installed Infrastructure layer:

* Compile and install the `OpenYuma <https://github.com/OpenClovis/OpenYuma>`__
  tools with our `VNF_starter` module
* Compile and install `Click <http://read.cs.ucla.edu/click/click>`__ modular
  router and The Click GUI: `Clicky <http://read.cs.ucla.edu/click/clicky>`__
* Install `neo4j <http://neo4j.com/>`__ graph database for NFIB
* Install additional tool for development, helper scripts and our rudimentary GUI
* If Mininet is not installed on the VM, install the ``mnexec`` utility and
  create a system user: **mininet** for NETCONF-based communication

5. Run ESCAPE with one of the commands listed in a later section. To see the
available arguments of the top starting script (``escape.py``), check the help menu:

.. code-block:: bash

    $ ./escape.py --help

To verify ESCAPE in **MdO** role a dry-run can be performed without any command line flag.
If ESCAPE is up and running, the following line should be logged to the console:

.. code-block:: text

  > [core                   ] ESCAPEv2 is up.

This final log entry means that each component was installed and configured successfully.

To verify ESCAPE in **DO** role with all the components the following command can be run
in order to test the reachability between the initiated service access points (SAP)
represented by the ``xterm`` windows with the ``ping`` command:

.. code-block:: bash

    $ ./escape.py -df -s examples/escape-mn-req.nffg

    # in SAP1 xterm
    $ ping sap2
    # in SAP2 xterm
    $ ping sap1

This command starts the full stack ESCAPE with the default topology (`examples/escape-mn-topo.nffg`)
and initiate a service request consists of a *HeaderCompressor* and a *HeaderDecompressor* VNF
for one direction and a simple *Forwarder* VNF for the backward direction between SAP1 and SAP2.
The two initiated SAP should reach each other after the service request has been processed.

.. note::

    For advanced install instructions check the :doc:`sub/install_hard_way`.

ESCAPE as a Docker container
----------------------------

ESCAPE can be run in a Docker container. To create the basic image, issue the following command
in the project root:

.. code-block:: bash

    $ docker build --rm --no-cache -t mdo/ro .

This command creates a minimal image based on the official Python image with the name: ``mdo/ro``,
installs the required Python dependencies listen in `requirement.txt` and sets the entry point.

To create and start a persistent container based on the ``mdo/ro`` image, use the following commands:

.. code-block:: bash

    $ docker create --name escape -p 8008:8008 -p 8888:8888 -p 9000:9000 -it mdo/ro
    $ docker start -i escape

To create a one-time container, use the following command:

.. code-block:: bash

    $ docker run --rm -p 8008:8008 -p 8888:8888 -p 9000:9000 -ti mdo/ro

Dockerfiles for other type of images can be found under the ``docker`` folder
 with several helper scripts.

.. note::

    ESCAPE can be used in a virtual environment to separate dependencies from host packages.
    For the instruction to setup virtualenv check the :doc:`sub/virtualenv`

ESCAPE example commands
=======================

ESCAPE can be started with the topmost ``escape.py`` script in the project's root directory.

.. note::

    For development purposes ESCAPE can be started calling the ``pox.py`` script
    directly with the layer modules and necessary arguments under the `pox` directory.

The simplest use-cases
----------------------

The most common use case is starting ESCAPE with a dedicated config file and using
debug mode for more verbose logging messages:

.. code-block:: bash

    $ ./escape.py -d -c config/escape-static-test.yaml

For the full feature set check the help menu:

.. code-block:: text

    $ ./escape.py -h
    usage: escape.py [-h] [-v] [-a] [-b] [-c path] [-d] [-e] [-f] [-g] [-i]
                     [-l file] [-m file] [-n] [-o [port]] [-q] [+q] [-r] [-s file]
                     [-t] [-x] [-V] [-4]
                     ...

    ESCAPEv2: Extensible Service ChAin Prototyping Environment using Mininet,
    Click, NETCONF and POX

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         show program's version number and exit

    ESCAPEv2 arguments:
      -a, --agent           run in AGENT mode: start the infrastructure layer with
                            the ROS REST-API (without the Service sublayer (SAS))
      -b, --bypassapi       start the REST-API to bypass embedding and access to
                            the DoV directly
      -c path, --config path
                            use external config file to extend the default
                            configuration
      -d, --debug           run the ESCAPE in debug mode (can use multiple times
                            for more verbose logging)
      -e, --environment     run ESCAPEv2 in the pre-defined virtualenv
      -f, --full            run the infrastructure layer also
      -g, --gui             (OBSOLETE) initiate the graph-viewer GUI app which
                            automatically connects to the ROS REST-API
      -i, --interactive     run an interactive shell for observing internal states
      -l file, --log file   define log file path explicitly (default:
                            log/escape.log)
      -m file, --mininet file
                            read the Mininet topology from the given file
      -n, --nosignal        run ESCAPE in a sub-shell that prevents propagation of
                            received SIGNALs
      -o [port], --openflow [port]
                            initiate internal OpenFlow module with given listening
                            port (default: 6633)
      -q, --quit            quit right after the first service request has
                            processed
      +q, ++quit            explicitly disable quit mode
      -r, --rosapi          start REST-API for the Resource Orchestration sublayer
                            (ROS)
      -s file, --service file
                            skip the SAS REST-API initiation and read the service
                            request from the given file
      -t, --test            run in test mode
      -x, --clean           run the cleanup task standalone and kill remained
                            programs, interfaces, veth parts and junk files
      -V, --visualization   run the visualization module to send data to a remote
                            server
      -4, --cfor            start the REST-API for the Cf-Or interface
      ...                   optional POX modules


In the role fo a Local Orchestrator, you can run ESCAPE with the Mininet-based
Infrastructure layer and enabled debug logging mode with the following command:

.. code-block:: bash

    $ ./escape.py -df

During a test or development the ``--debug`` flag is almost necessary for detailed logging.

To run a test topology, use the ``--full`` flag to initiate the Mininet-based Infrastructure layer.
ESCAPE will parse the topology description form file (``escape-mn-topo.nffg`` by default)
and start the Infrastructure layer with the Mininet-based emulation.

If the request is in a file, it's more convenient to pass it to ESCAPE with the ``--service``
initial parameter and avoid assembling the service request for the REST-API.

.. warning::

    If the service request is given by the ``--service`` parameter,
    the topmost REST-API of the *Service* layer will not be started!

To initiate the Mininet-based infrastructure layer and use ESCAPE as
the local orchestrator, set the ``--agent`` flag.

With ``--agent`` flag ESCAPE will initiate the ROS API for communication with
upper layers instead of initiating the whole Service Layer.
Note to mention that this flag also effects on different parts of the ESCAPE's
operation therefore it is not equivalent with the pair of ``--full --rosapi``!

An additional configuration file can be given with the ``--config`` flag. The
configuration file is loaded during initialization and ESCAPE only updates
the default configuration instead of replacing it in order to minimize the sizes
of the additional parameters.

One of the most common change in the configuration is the file path of the initial
topology which is used by the Infrastructure layer to initiate the Mininet-emulated
network. To simplify this case the topology file can be explicitly given with
the ``--topo`` parameter.

With the ``--environment`` flag ESCAPE can be started in a pre-defined virtualenv
environment whether the virtualenv is permanently enabled with the ``.use_virtualenv`` file or not.

With the ``--visualization`` flag ESCAPE will send topologies in Virtualizer format
to a predefined remote server for the purpose of visualization.

If an error is occurred or need to observe the internal states, ESCAPE can be started
with an interactive Python shell using the ``--interactive`` flag.

The main layers which grouping the entities are reachable through the main POX
object called ``core`` with the names:

  * ``service`` - Service layer
  * ``orchestration`` - Resource Orchestration Sublayer
  * ``adaptation`` - Controller Adaptation Sublayer
  * ``infrastructure`` - Infrastructure layer

.. hint::

  In the interactive shell the tab-auto completion is working in most cases.

A possible scenario for testing ESCAPE with a test request given in a file
and check the state of the DoV can be the following:

.. code-block:: bash

    $ ./escape.py -dfi -s examples/escape-mn-req.nffg
    Starting ESCAPEv2...
    Command: sudo /home/czentye/escape/pox/pox.py unify --full \
        --sg_file=/home/czentye/escape/examples/escape-mn-req.nffg py --completion

    ...

    ESCAPE> print core.adaptation.controller_adapter.domainResManager._dov
                .get_resource_info().dump()
    {
      "parameters": {
        "id": "DoV",
        "name": "dov-140454330075984",
        "version": "1.0"
      },
      "node_saps": [
        {
          "id": "SAP1",

    ...

Advanced start commands (mostly advisable for testing purposes)
---------------------------------------------------------------

By default ESCAPE initiates the logging module with level: *INFO*.
To set the logging level to *DEBUG* the ``-d`` initial flag needs to be used.

.. code-block:: bash

    $ ./escape.py -d

ESCAPE defines a lower and more detailed logging level with the name: *VERBOSE*
which logs all the received, transmitted and calculated internal data.

In order to start ESCAPE with VERBOSE logging the debug initial flag needs to be
used multiple times e.g. ``-dd`` or ``-d -d``.

.. code-block:: bash

    $ ./escape.py -dd

.. note::

    For lower level commands check the :doc:`sub/low_level_commands`.

REST APIs
=========

ESCAPE has currently 4 REST-APIs.

The Service layer has a REST-API for communication with the users and/or a GUI.
This API is initiated by default when its layer is started.

The Resource Orchestration layer has 2 API which are only initiated if the
appropriate flag is given to the starting script.

The ROS API can be used for communicating with other UNIFY layer e.g. a
Controller Adaptation Sublayer of a standalone ESCAPE in a multi-level
scenario or with a GUI.

The Controller Adaptation layer also has a REST-API for mostly debugging purposes
and define a direct interface to the Global topology view (DoV) for external components.

The CfOr API realizes the interface for UNIFY's service elasticity feature.

All the REST function path should contain the prefix value which is ``escape``
by default and can be changed in the APIs' configuration.

.. note::

    The required format of the REST calls is the following: `http://<ip>:<port>/<prefix>/<operation>`


Common API functions
--------------------

*Operations:*   Every API has the following 3 function (defined in :any:`AbstractRequestHandler`):

+-------------------+----------------+-------------------+----------------------------------------------+
|    Operation      |     Params     |     HTTP verbs    | Description                                  |
+===================+================+===================+==============================================+
| */version*        | ``None``       | GET               | Returns with the current version of ESCAPE   |
+-------------------+----------------+-------------------+----------------------------------------------+
| */ping*           | ``None``       | GET, POST         | Returns with the "OK" string                 |
+-------------------+----------------+-------------------+----------------------------------------------+
| */operations*     | ``None``       | GET               | Returns with the implemented operations      |
+-------------------+----------------+-------------------+----------------------------------------------+

Service API specific functions
------------------------------

The SAS API is automatically initiated by the Service layer. If the ``--service`` flag is used,
the service request is loaded from the given file and the REST-API initiation is skipped.

*Content Negotiation:* The Service layer's RESTful API can accept and return data
in JSON format and in Virtualizer format too (need to set in the config).

The following functions are defined in :any:`ServiceRequestHandler`.

+-------------------+------------------+-------------------+----------------------------------------------------------------+
|    Operation      |     Params       |     HTTP verbs    | Description                                                    |
+===================+==================+===================+================================================================+
| */topology*       | ``None``         | GET, POST         | Returns with the resource view of the Service layer            |
+-------------------+------------------+-------------------+----------------------------------------------------------------+
| */sg*             | ``NFFG``         | POST              | Initiate given NFFG. Returns the initiation is accepted or not |
+-------------------+------------------+-------------------+----------------------------------------------------------------+
| */status*         | ``message-id``   | GET               | Returns with the service status                                |
+-------------------+------------------+-------------------+----------------------------------------------------------------+

ROS API specific functions
--------------------------

Can be started with the ``--agent`` or ``--rosapi`` initial flags.

The following functions are defined in :any:`Extended5GExRequestHandler`.

+----------------------+----------------+-------------------+-------------------------------------------+
|    Operation         |     Params     |     HTTP verbs    | Description                               |
+======================+================+===================+===========================================+
| */get-config*        | ``None``       | GET, POST         | Returns with the resource view of the ROS |
+----------------------+----------------+-------------------+-------------------------------------------+
| */edit-config*       | ``NFFG``       | POST              | Initiate given Virtualizer                |
+----------------------+----------------+-------------------+-------------------------------------------+
| */mapping-info/<id>* | service id     | POST              | Returns the NF mappings of given service  |
+----------------------+----------------+-------------------+-------------------------------------------+
| */mappings*          | ``Mappings``   | POST              | Returns the mapping of given NFs          |
+----------------------+----------------+-------------------+-------------------------------------------+
| */info*              | ``Info``       | POST              | Returns collected Info data from domains  |
+----------------------+----------------+-------------------+-------------------------------------------+
| */status*            | service id     | GET               | Returns the status of given service       |
+----------------------+----------------+-------------------+-------------------------------------------+

Cf-Or API specific functions
----------------------------

Can be started with the ``--cfor`` flag.

The following functions are defined in :any:`CfOrRequestHandler`.

+-------------------+----------------+-------------------+-----------------------------------------------------------------+
|    Operation      |     Params     |     HTTP verbs    | Description                                                     |
+===================+================+===================+=================================================================+
| */get-config*     | ``None``       | GET, POST         | Returns with the resource view from the assigned Virtualizer    |
+-------------------+----------------+-------------------+-----------------------------------------------------------------+
| */edit-config*    | ``NFFG``       | POST              | Initiate given Virtualizer                                      |
+-------------------+----------------+-------------------+-----------------------------------------------------------------+

CAS API specific functions
--------------------------

Can be started with the ``--bypassapi`` flag.

The following functions are defined in :any:`DirectDoVRequestHandler`.

+-------------------+----------------+-------------------+---------------------------------------------+
|    Operation      |     Params     |     HTTP verbs    | Description                                 |
+===================+================+===================+=============================================+
| */get-config*     | ``None``       | GET, POST         | Returns with the Global domain view (DoV)   |
+-------------------+----------------+-------------------+---------------------------------------------+
| */edit-config*    | ``NFFG``       | POST              | Deploy given Virtualizer without embedding  |
+-------------------+----------------+-------------------+---------------------------------------------+

Configuration
=============

ESCAPE loads its default configuration from file placed in the project's root directory: ``escape.config``.
This configuration contains the necessary information for manager/adapter initializations,
remote connections, etc. and also provides the base for the internal running configuration.

If some parameters need to be changed, one option could be to modify the values
in the default configuration directly, which is highly not recommended.

However, ESCAPE provides the opportunity to specify the minimal change set in an additional
config file and load it with the ``--config`` initial parameter at boot time.

.. important::

  The configuration is parsed at boot time. Changes in the config file have no effect at runtime.

Only the changed entries are required to be defined in the additional configuration files.
The additional config can be added only in JSON format, but the structure of the
configuration has to strictly follow the default configuration.

ESCAPE merges the additional configuration with the basic configuration file to create
the running configuration held in the memory.
This merging mechanism gives the possibility not just to define new config entries but also
to override any part of the default config entry set in a straightforward way.

The configuration entries (coherent values, single boolean flags, paths, etc.) are
handled through the main :any:`ESCAPEConfig` class so every possible configuration
entry has an assigned `getter` function in the main class.

Default configuration (YAML)
----------------------------

The following YAML-based configuration (``escape-config.yaml``) contains the default (and possible)
configuration entries of the main layers and its subcomponents.

.. include:: escape-config.yaml
    :literal:
    :code: yaml

As an example, several additional configuration files can be found under the ``config`` folder.

For detailed explanations check the :doc:`sub/detailed_config`.

Development
===========

Suggested IDE: `PyCharm Community Edition <https://www.jetbrains.com/pycharm/>`__

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
=========

PyCharm can be a good choice for debugging.
In this case a new Python interpreter has to be specified in order that PyCharm will be able to run ESCAPE with root privilege.
The *python_root_debugger.sh* script under the ``tools`` folder emulates that kind of Python interpreter.

For debugging POX's *py* stock component also can be used, which open an interactive Python shell after ESCAPE has started.
That module allows observing the internal state of the running ESCAPE instance, experimenting with the internal objects or even calling different functions.

POX uses a topmost object called *core* which serves a rendezvous point between POX's components (e.g. our components representing the UNIFY layers).
Through that object we can reach every registered object easily. For example to shut down the REST API of the Service layer manually the
following function call can be invoked on-the-fly:

.. code-block:: bash

  $ Ready.
  $ ESCAPE>
  $ ESCAPE> core.service.rest_api.stop()

One instance of the *ESCAPEInteractiveHelper* is registered by default under the
name: *helper*. An example to dump the running configuration of ESCAPE:

.. code-block:: bash

  $ ESCAPE> core.helper.config()
    {
        "infrastructure": {
            "NETWORK-OPTS": null,
            "FALLBACK-TOPO": {
                "class": "BackupTopology",
                "module": "escape.infr.topology"
    ...

More help and description about the useful helper functions and the *core* object is in the comments/documentation and on the POX's
`wiki <https://openflow.stanford.edu/display/ONL/POX+Wiki#POXWiki-POXAPIs>`__ site.

Tests
=====

ESCAPE has several testcases formed as Unit tests. These tests can be found under
the `test` folder.

Dependent packages for the test can be installed with the `install_requirements.sh` script.
To run the test see the main running script:

.. code-block:: text

    $ ./run_tests.py -h
    usage: run_tests.py [-h] [-f] [-o] [-t t] [-s] [-v]
                        [testcases [testcases ...]]

    ESCAPE Test runner

    positional arguments:
      testcases          list test case names you want to run. Example:
                         ./run_tests.py case05 case03 --show-output

    optional arguments:
      -h, --help         show this help message and exit
      -f, --failfast     stop on first failure
      -o, --show-output  show ESCAPE output (can use multiple times for more
                         verbose logging)
      -t t, --timeout t  define explicit timeout in sec (default: 60s)
      -s, --standalone   run standalone mode: no timeout, no quitting
      -v, --verbose      run testframework in verbose mode and show output

The test cases can be run in a Docker container as well:

.. code-block:: text

    $ ./dockerized-test.sh -h
    Run testcases in a docker container.

    Usage: ./dockerized-test.sh [-b] | ...
    Parameters:
         -b, --build   force to rebuild the Docker image
         -h, --help    show this help message and exit
         ...           runner parameters, see run_tests.py -h

    Example: ./dockerized-test.sh -b | ./dockerized-test.sh case15 -o

Documentation
=============

The documentation can be generated from source code with `generate-docs.sh` script
or directly with the `Makefile` in `escape/doc` directory.
The generated doc can be found in `escape/doc/build/`.

Requirements:

    * sphinx (sudo -H pip install sphinx)
    * texlive-latex-extra (sudo apt install -y texlive-latex-extra)

API documentation
=================

The following documentation contains only the Python class structure and description of the ESCAPE framework.

The Mininet-based infrastructure, which is an extended version of Mininet, the POX framework and our resource mapping algorithm is not documented here.

ESCAPEv2 class structure
------------------------

.. toctree::
    :maxdepth: 6
    :titlesonly:

    escape

Topmost POX modules for ESCAPE's layers/sublayers
-------------------------------------------------

.. toctree::
    :maxdepth: 2
    :titlesonly:

    ESCAPE <ESCAPE>

License and Contacts
====================

Licensed under the Apache License, Version 2.0, see LICENSE file.

    Copyright (C) 2017 by

    - János Czentye - janos.czentye@tmit.bme.hu
    - Balázs Németh - balazs.nemeth@tmit.bme.hu
    - Balázs Sonkoly - balazs.sonkoly@tmit.bme.hu

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

