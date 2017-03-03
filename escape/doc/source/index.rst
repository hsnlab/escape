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

The **install_dep.sh** script is responsible for managing the dependencies. It sets up
the required sym-links, updates the related submodules and installs only the necessary
packages regarding the given install parameters.

As the core layers of ESCAPE relies on POX and written in Python there is no need
for explicit compiling or installation. The required libraries and dependencies such as
external databases and programs, system packages and the latest Python 2.7 interpreter
are completely handled and installed by the main setup script.

The currently recommended Python version, in which the development and mostly the
testing are performed, is the standard CPython **2.7.13**.

.. important::

  Only the standard CPython interpreter is tested and supported!

If for some reason a different version of Python is desired, check the Virtual Environment section below.

The best choice of platform on which ESCAPE is recommended to be installed and
the *install-dep.sh* installation script is tested is Ubuntu 14.04.5 and 16.04.2 LTS.

However ESCAPE has been developed on Ubuntu 16.04, some issues are experienced
related to SAP-xterm initiation in case ESCAPE was run on an Ubuntu 16.04 virtual
machine through an SSH channel with X11 forwarding.

.. important::

    Considering this limitation we recommend to use the older 14.04.5 LTS version
    in case ESCAPE is intended to run:

      * on a VM
      * without any graphical interface
      * as a local Domain Orchestrator.

Nevertheless the install script (``install-dep.sh``) supports both LTS version.

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

3. Clone the shared escape repository (the default folder name will be: *escape*).

  .. code-block:: bash

    $ git clone <git repo URL>

4. Install the necessary dependencies with the ``install_dep.sh`` script (system
    and Python packages, optionally the OpenYuma with VNFStarter module, etc.):

  .. code-block:: bash

    $ cd escape
    $ ./install_dep.sh

  Usage:

  .. code-block:: text

    $ ./install-dep.sh -h
    Usage: ./install-dep.sh [-a] [-c] [-d] [-g] [-h] [-i] [-p project]
    Install script for ESCAPEv2

    options:
        -a:   (default) install (A)ll ESCAPEv2 components (identical with -cgi)
        -c:   install (C)ore dependencies for Global Orchestration
        -d:   install additional dependencies for (D)evelopment and test tools
        -g:   install dependencies for our rudimentary (G)UI
        -h:   print this (H)elp message
        -i:   install components of (I)nfrastructure Layer for Local Orchestration
        -p:   explicitly setup project name based on: .gitmodules.<name>


  In a high level, the script above takes care of the following things:
    * Install the necessary system and Python packages
    * Compile and install the `OpenYuma <https://github.com/OpenClovis/OpenYuma>`__
      tools with our `VNF_starter` module
    * Compile and install `Click <http://read.cs.ucla.edu/click/click>`__ modular
      router and The Click GUI: `Clicky <http://read.cs.ucla.edu/click/clicky>`__
    * Install `neo4j <http://neo4j.com/>`__ graph database for NFIB
    * Install additional tool for development, helper scripts and our rudimentary GUI
    * If Mininet is not installed on the VM, install the ``mnexec`` utility and
      create a system user: **mininet** for NETCONF-based communication

5. Run ESCAPE with one of the commands listed in a later section. To see the
available arguments of the top starting script (*escape.py*), check the help menu:

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

.. important::

    If more then 7 node (including switches and also Execution Environments) is required in the Mininet-based
    Infrastructure layer the OpenSSh server have to be recompiled and reinstalled from source to increase
    the number of possible listening ports. In this case the necessary commands are the following:

     .. code-block:: bash

         $ sudo -i
         $ cd /usr/src
         $ apt-get update && apt-get source openssh-server
         $ cd openssh-*
         $ sed -i 's/^\(#define\s*MAX_LISTEN_SOCKS\s*\).*/\1256/' sshd.c
         $ sed -i 's/^\(#define\s*MAX_PORTS\s*\).*/\1256/' servconf.h
         $ ./configure --prefix=/usr --sysconfdir=/etc/ssh --with-default-path=$PATH
         $ make
         $ make install
         $ service ssh restart

The hard way
------------

Obviously ESCAPE can be installed on a host machine or on a different platform too.
If the install script fails on a newer OS for some reason, the installation steps need to be carried out manually.

**Submodules**

The project uses several dependent component as a Git submodule. To acquire these
source codes a symlink have to be created in the project's root folder at first,
referring to the gitmodules config of the actual project.

Moreover, the required submodules need to be configured with the related project's gitmodules file recursively.
For this task the ``project-setup.sh`` wrapper script can be used with the referred project's name:

.. code-block:: bash

    $ ./project-setup.sh
        Usage: ./project-setup.sh [project]
        Setup submodules according to given project for ESCAPE.

        parameters:
             project: setup project [sb|5gex|ericsson]

The submodule configuration can be set up and updated manually as well:

.. code-block:: bash

    $ ln -s .gitmodules.<project_name> .gitmodules
    $ git submodule update --init --remote --recursive --merge

**Dependencies**

If ESCAPE's Python dependencies are not wanted to be installed globally, follow the
hard way and setup a virtual environment step-by-step.

For stability ESCAPE uses the dedicated version of the following packages:
    * neo4j: 2.2.7 (Ubuntu 14.04) or 3.1.1 (Ubuntu 16.04)
    * cryptography 1.3.1

neo4j requires Java 7 which can't be found in the official Ubuntu 14.04 repositories.
To install the Java package and the latest Python 2.7, the following PPA repositories
can be used:

.. code-block:: bash

    $ sudo apt-get install -y software-properties-common
    $ sudo add-apt-repository -y ppa:openjdk-r/ppa
    $ sudo add-apt-repository -y ppa:jonathonf/python-2.7
    $ sudo apt-get install openjdk-7-jdk python2.7

Required system and Python packages:

.. code-block:: bash

    $ sudo apt-get -y install python-dev python-pip zlib1g-dev libxml2-dev libxslt1-dev \
        libssl-dev libffi-dev python-crypto openvswitch-switch neo4j=2.2.7

    $ sudo -H pip install numpy jinja2 py2neo networkx requests ncclient cryptography==1.3.1

For Mininet emulation tool:

.. code-block:: bash

    $ sudo apt-get -y install gcc make socat psmisc xterm ssh iperf iproute telnet \
    python-setuptools cgroup-bin ethtool help2man pyflakes pylint pep8 openvswitch-switch

For our rudimentary GUI:

.. code-block:: bash

    $ sudo apt-get install -y python-tk
    $ sudo -H pip install networkx_viewer

For doc generations:

.. code-block:: bash

    # html
    $ sudo apt-get -y install graphviz
    $ sudo -H pip install sphinx
    # latex
    $ sudo apt-get install -y texlive-latex-extra

For domain emulation scripts:

.. code-block:: bash

    $ sudo -H pip install tornado openvswitch-switch

If a newer version of ``neo4j`` has been installed on the system, use the following commands to downgrade.
In this case the authentication bypass needs to be done again.

.. code-block:: bash

    $ sudo -i
    $ apt-get purge neo4j
    $ rm -rf /var/lib/neo4j/data/
    $ rm -rf /etc/neo4j/
    $ apt-get install -y neo4j=2.2.7
    $ apt-mark hold neo4j

In extreme cases, e.g. the `install_dep.sh` ran into an error, these dependencies should be installed
one by one according to the used OS, distro or development environment.
For that follow the steps in the install script and/or the online documentations
referenced in entry 4. of the previous subsection.

In case of the additional DO functionality other required programs (OpenYuma, click, neo4j, etc.),
which are installed by the `install_dep.sh` script by default, are also need to be installed manually.
The relevant command can be found in the ``install-dep.sh`` script's *install_mn_dep()* and
*install_infra()* functions.

To use the Infrastructure Layer of ESCAPE, Mininet must be installed on the host machine
(more precisely the **Open vSwitch** implementation and the specific **mnexec** utility
is only required to be installed globally).

If Mininet has already been installed, there is nothing to do.
ESCAPE always uses the specifically-modified Mininet files in the project folder (*Mininet v2.1.0mod-ESCAPE*)
which will use the globally installed Mininet utility scripts (mnexec).

Otherwise these assets have to be installed manually which could be done from our
Mininet folder (escape/mininet) or from the official Mininet git repository
(`<https://github.com/mininet/mininet/>`__). Mininet has an install script for
the installations (see the help with the ``-h`` flag) but this script will install
the whole Mininet tool with unnecessary packages:

.. code-block:: bash

    $ sudo mininet/util/install.sh -n

In this case you can run the following command to check whether the installation was correct or not:

.. code-block:: bash

    $ sudo mn --test pingall

But the script will install the whole Mininet package and additional dependencies.
For a minimal install, compile the ``mnexec`` source by manual and
copy the binary into a folder which is in your ``PATH`` system variable.

.. code-block:: bash

    $ cd mininet/
    $ make mnexec
    $ sudo install mnexec /usr/bin

If ESCAPE is intended to be used on a host machine, it is recommended to create a separate user for the netconfd server.
This user's name and password will be used for the connection establishment between ESCAPE and the Execution Environments (EE).

.. note::

  These parameters can be changed conveniently in the global config under the
  config entry of *VNFStarter Adapter* .

Another solution is to define a system user for the netconfd. To create a user
(advisable to use `mininet` as in the Mininet-based VM) use the following commands:

.. code-block:: bash

    $ sudo adduser --system --shell /bin/bash --no-create-home mininet
    $ sudo addgroup mininet sudo
    $ echo "mininet:mininet" | sudo chpasswd

For security reasons, it's highly recommended to limit the SSH connections for the
`mininet` user only to localhost.

.. code-block:: bash

    $ sudo echo -e 'Match Host *,!localhost\n  DenyUsers  mininet' >> /etc/ssh/sshd_config
    $ sudo service ssh reload

Check the created user with the following command:

.. code-block:: bash

    $ ssh mininet@localhost

Setup a Virtual environment (optional)
--------------------------------------

ESCAPE also supports Python-based virtual environments in order to setup a
different Python version or even a different interpreter (not recommended) for
itself or to separate dependent packages from system-wide Python installation.

To setup a virtual environment based on `virtualenv <https://virtualenv.readthedocs.org/en/latest/>`__
Python package with a standalone CPython 2.7.13 interpreter run the following script:

.. code-block:: bash

    $ ./set_virtualenv.sh

This script performs the following steps:
  * Install additional dependencies
  * Download, compile and install the 2.7.13 (currently the newest) Python
    interpreter in a separated directory
  * Setup a virtual environment in the main project directory independently from
    the system-wide Python packages
  * Install the Python dependencies in this environment
  * and finally create a ``.use_virtualenv"`` file to enable the newly created
    virtual environment for the topmost ``escape.py`` starting script.

Usage:

.. code-block:: text

    $ ./set_virtualenv.sh -h
      Usage: ./set_virtualenv.sh [-p python_version] [-h]
      Install script for ESCAPEv2 to setup virtual environment

      optional parameters:
        -p   set Python version (default: 2.7.13)
        -h   show this help message and exit
      Example: ./set_virtualenv.sh -p 2.7.10
      Based on virtualenv. More information: virtualenv -h


The ``escape.py`` script can detect the ``.use_virtualenv`` file automatically
and activates the virtual environment transparently. To disable the virtual environment,
delete the ``.use_virtualenv`` file.

The virtualenv can also be enabled by the ``--environment`` flag of the topmost ``escape.py`` script.

In order to setup the environment manually, define the Python version/interpreter;
enable the system-wide Python / ``pip`` packages;

.. code-block:: bash

    $ virtualenv -p=<python_dir> --no-site-packages/system-site-packages <...> escape

and then activate/deactivate the environment manually:

.. code-block:: bash

    $ cd escape
    $ source bin/activate # activate virtual environment
    $ deactivate  # deactivate

For more information check the content of the setup script or see the
`Virtualenv User Guide <https://virtualenv.readthedocs.org/en/latest/userguide.html>`_.

ESCAPE example commands
=======================

ESCAPE can be started with the topmost ``escape.py`` script in the project's
root directory (recommended) or can be started calling the ``pox.py`` script directly with the
layer modules and necessary arguments under the `pox` directory.

The simplest use-case
---------------------

Run ESCAPE with the Mininet-based Infrastructure layer and enabled debug logging mode:

.. code-block:: bash

    $ ./escape.py -df

Usage:

.. code-block:: text

    $ ./escape.py -h
    usage: escape.py [-h] [-v] [-a] [-c path] [-d] [-e] [-f] [-g] [-i] [-l file]
                     [-m file] [-p] [-r] [-s file] [-t] [-q] [-x] [-V] [-4]
                     ...

    ESCAPEv2: Extensible Service ChAin Prototyping Environment using Mininet,
    Click, NETCONF and POX

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         show program's version number and exit

    ESCAPEv2 arguments:
      -a, --agent           run in AGENT mode: start the infrastructure layer with
                            the ROS REST-API (without the Service sublayer (SAS))
      -c path, --config path
                            override default config filename
      -d, --debug           run the ESCAPE in debug mode (can use multiple times
                            for more verbose logging)
      -e, --environment     run ESCAPEv2 in the pre-defined virtualenv
      -f, --full            run the infrastructure layer also
      -g, --gui             initiate the graph-viewer GUI app which automatically
                            connects to the ROS REST-API
      -i, --interactive     run an interactive shell for observing internal states
      -l file, --log file   add log file explicitly for test mode (default:
                            log/escape.log)
      -m file, --mininet file
                            read the Mininet topology from the given file
      -p, --POXlike         start ESCAPEv2 in the actual interpreter using ./pox
                            as working directory instead of using a separate shell
                            process with POX's own PYTHON env
      -r, --rosapi          start the REST-API for the Resource Orchestration
                            sublayer (ROS)
      -s file, --service file
                            skip the SAS REST-API initiation and read the service
                            request from the given file
      -t, --test            run in test mode
      -q, --quit            quit right after the first service request has
                            processed
      -x, --clean           run the cleanup task standalone and kill remained
                            programs, interfaces, veth parts and junk files
      -V, --visualization   run the visualization module to send data to a remote
                            server
      -4, --cfor            start the REST-API for the Cf-Or interface
      ...                   optional POX modules


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

Lower level start commands (only advisable for developers)
----------------------------------------------------------

For more flexible control ESCAPE can be started directly with POX's starting
script under the ``pox`` folder.

.. note::

  The topmost ``escape.py`` script uses this ``pox.py`` script to start ESCAPE.
  In debug mode the assembled POX command is printed also.

Basic command:

.. code-block:: bash

    $ ./pox.py unify

One of a basic commands for debugging:

.. code-block:: bash

    $ ./pox.py --verbose unify py

For forcing to log on DEBUG level the ``--verbose`` flag of the ``pox.py``
script can be used. Or the *log.level* POX module can be used (which would be the
preferred way). Example:

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
    $ ./pox.py adaptation --mapped_nffg=<path> ...

Start ESCAPE with built-in GUI:

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

REST APIs
=========

ESCAPE has currently 3 REST-APIs.

The Service layer has a REST-API for communication with the users and/or a GUI.
This API is initiated by default when its layer is started.

The Resource Orchestration layer has 2 API which are only initiated if the
appropriate flag is given to the starting script.

The ROS API can be used for communicating with other UNIFY layer e.g. a
Controller Adaptation Sublayer of a standalone ESCAPE in a multi-level
scenario or with a GUI.

The CfOr API realizes the interface for UNIFY's service elasticity feature.

All the REST function path should contain the prefix value which is ``escape``
by default and can be changed in the APIs' configuration. See more in
`REST-API, Sl-Or, Cf-Or`_.

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

The following functions are defined in :any:`BasicUnifyRequestHandler`.

+-------------------+----------------+-------------------+-------------------------------------------+
|    Operation      |     Params     |     HTTP verbs    | Description                               |
+===================+================+===================+===========================================+
| */get-config*     | ``None``       | GET, POST         | Returns with the resource view of the ROS |
+-------------------+----------------+-------------------+-------------------------------------------+
| */edit-config*    | ``NFFG``       | POST              | Initiate given NFFG.                      |
+-------------------+----------------+-------------------+-------------------------------------------+

Cf-Or API specific functions
----------------------------

Can be started with the ``--cfor`` flag.

The following functions are defined in :any:`CfOrRequestHandler`.

+-------------------+----------------+-------------------+---------------------------------------------------------------------------+
|    Operation      |     Params     |     HTTP verbs    | Description                                                               |
+===================+================+===================+===========================================================================+
| */get-config*     | ``None``       | GET, POST         | Returns with the resource view from the assigned Virtualizer              |
+-------------------+----------------+-------------------+---------------------------------------------------------------------------+
| */edit-config*    | ``NFFG``       | POST              | Initiate given NFFG.                                                      |
+-------------------+----------------+-------------------+---------------------------------------------------------------------------+

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

Default configuration (JSON)
----------------------------

The following JSON-based configuration (``escape-config.json``) contains the default (and possible)
configuration entries of the main layers and its subcomponents.

As an example, several additional configuration files can be found under the ``config`` folder.

.. include:: escape-config.json
    :literal:
    :code: json

Configuration structure
-----------------------

The configuration is divided into 4 parts according to the UNIFY's / ESCAPE's
main layers, namely ``service``, ``orchestration``, ``adaptation`` and ``infrastructure``.

Service and Orchestration
^^^^^^^^^^^^^^^^^^^^^^^^^

The top 2 layer (``service`` and ``orchestration``) has similar configuration parameters.
In both layers the core mapping process can be controlled with the following entries:

  * **MAPPER** defines the mapping class which controls the mapping process
    (inherited from :any:`AbstractMapper`)
  * **STRATEGY** defines the mapping strategy class which calls the actual mapping
    algorithm (inherited from :any:`AbstractMappingStrategy`)
  * **PROCESSOR** defines the Processor class which contains the pre/post mapping
    functions for validation and other auxiliary functions (inherited from :any:`AbstractMappingDataProcessor`)

The values of the class configurations (such the entries above) always contains the **module** and **class** names.
With this approach ESCAPE can also instantiate and use different implementations from external Python packages.
The only requirement for these classes is to be included in the scope of ESCAPE
(more precisely in the PYTHONPATH of the Python interpreter which runs ESCAPE).

.. note::

  Every additional subdirectory in the project's root is always added to the search
  path (scope) dynamically by the main ``escape`` module at initial time.

The mapping process and pre/post processing can be enabled/disabled with the
``mapping-enabled`` (boolean) and ``enabled`` (boolean) values under the appropriate entries.

The mapping algorithm called in the Strategy class can be initiated in a worker
thread with the ``THREADED`` flag but this feature is still in experimental phase!

These 2 layers can also initiate REST-APIs. The initial parameters are defined
under the names of the APIs:

  * **REST-API** - top REST-API in the SAS layer
  * **Sl-Or** - Sl-Or interface in the ROS layer for external components
    i.e. for upper UNIFY entities, GUI or other ESCAPE instance in a distributed, multi-layered scenario
  * **Cf-Or** - Cf-Or interface in the ROS layer for supporting service elasticity feature

These REST-API configurations consist of

  * a specific handler class which initiated for every request and handles the
    requests (inherited from :any:`AbstractRequestHandler`) defined with the ``module`` and ``class`` pair
  * address of the REST-API defined with the ``address`` and ``port`` (integer) pair
  * ``prefix`` of the API which appears in the URL right before the REST functions
  * optionally the type of used Virtualizer (``virtualizer_type``) which filters the data flow of the API
    (currently only supported the global (`GLOBAL`) and single BiS-BiS (`SINGLE`) Virtualizer)
  * flags mark the interface as UNIFY interface (``unify_interface``) with difference format (``diff``)

Schematic config description:

MAPPER
******
Contains the configuration of the *Mapper* class responsible for managing the overall mapping process of the layer.

    `module`
        (:any:`string`) Python module name where `class` can be found, e.g. ``escape.orchest.ros_mapping``
    `class`
        (:any:`string`) Python class name of the *MAPPER*, e.g. ``ResourceOrchestrationMapper``
    `mapping-enabled`
        (:any:`bool`) Enables the mapping process in the actual layer
    `mapping config`
        (:class:`dict`) Optional arguments directly given to the main entry point of the core mapping function
        ``MappingAlgorithms.MAP()``, e.g. ``mode="REMAP"`` force the algorithm to use the *REMAP* orchestration
        approach in every case. See more in the function's documentation.

STRATEGY
********
Contains the configuration of the *Strategy* class responsible for running chosen orchestration algorithm.

    `module`
        (:any:`string`) Python module name where `class` can be found, e.g. ``escape.service.sas_mapping``
    `class`
        (:any:`string`) Python class name of the *STRATEGY*, e.g. ``DefaultServiceMappingStrategy``
    `THREADED`
        (:any:`bool`) Enables the mapping process in a separate thread (experimental).

PROCESSOR
*********
Contains the configurations of the *Processor* class responsible for invoke pre/post mapping functionality.

    `module`
        (:any:`string`) Python module name where `class` can be found, e.g. ``escape.util.mapping``
    `class`
        (:any:`string`) Python class name of the *PROCESSOR*, e.g. ``ProcessorSkipper``
    `enabled`
        (:any:`bool`) Enables pre/post processing

REST-API, Sl-Or, Cf-Or
**********************
Contains the configuration of the *Handler* class responsible for processing requests *Sl-Or*, *Cf-Or* interface.

    `module`
        (:any:`string`) Python module name where `class` can be found, e.g. ``escape.orchest.ros_API``
    `class`
        (:any:`string`) Python class name of the *HANDLER*, e.g. ``BasicUnifyRequestHandler``
    `address`
        (:any:`string`) Address the REST server bound to, e.g. ``0.0.0.0``
    `port`
        (:any:`int`) Port the REST server listens on, e.g. ``8008``
    `prefix`
        (:any:`string`) Used prefix in the REST request URLs, e.g. ``escape``
    `unify_interface`
        (:any:`bool`) Set the interface to use the Virtualizer format.
    `diff`
        (:any:`bool`) Set accepted format to difference instead of full.
    `virtualizer_type`
        (:any:`string`) Use the given abstraction for generation topology description:
            ``SINGLE``: use Single BiSBiS representation

            ``GLOBAL``: offer the whole domain view intact

Other configuration entries
***************************
Other configuration entries of these layers.

*service*
  `SERVICE-LAYER-ID`
    (:any:`string`) Internal ID of Service module - shouldn't be changed.

*orchestration*
  `ESCAPE-SERVICE`
    (:class:`dict`) Defines parameters for internal Service API identified by the name: *ESCAPE-SERVICE*
      `virtualizer_type`
        (:any:`string`) Use the given topology abstraction for internal Service layer:
          ``SINGLE``: use Single BiSBiS representation

          ``GLOBAL``: offer the whole domain view intact
  `manage-neo4j-service`
    (:any:`bool`) Force ESCAPE to start and stop Neo4j service by itself

Adaptation
^^^^^^^^^^

The ``adaptation`` layer contains the configuration of different Manager (inherited from :any:`AbstractDomainManager`)
classes under their specific name which is defined in the ``name`` class attribute.

These configurations are used by the :any:`ComponentConfigurator` to initiate the required components dynamically.
Every Manager use different Adapters (inherited from :any:`AbstractESCAPEAdapter`)
to hide the specific protocol-agnostic steps in the communication between the ESCAPE orchestrator and network elements.

The configurations of these Adapters can be found under the related Manager config (``adapters``)
in order to be able to initiate multiple Managers based on the same class with different Adapter configurations.

The class configurations can be given by the ``module`` and ``class`` pair similar way as so far.
Other values such as ``path``, ``url``, ``keepalive``, etc. will be forwarded to the constructor of the component
at initialization time so the possible configurations parameters and its types are derived from the parameters
of the class' constructor.

The ``MANAGERS`` list contains the configuration names of Managers need to be initiated.

In order to activate a manager and manage the specific domain, add the config name of the DomainManager
to the ``MANAGERS`` list. The manager will be initiated with other Managers at boot time of ESCAPE.

.. warning::

    If a Manager's name does not included in the ``MANAGERS`` list, the corresponding domain will NOT be managed!

Schematic config description:

    `MANAGERS`
        (:any:`list`) Contains the name of the domain managers need to be initiated, e.g. `["SDN", "OPENSTACK"]`

Domain Managers
***************

The domain manager configurations contain the parameters of the different manager objects.
The defined manager configuration is directly given to the constructor function of the manager
class by the :any:`ComponentConfigurator` object.

The default configuration defines a default domain manager and the relevant adapter configurations
for the Infrastructure layer with the name: `INTERNAL`. The internal domain manager
is used for managing the Mininet-based emulated network initiated by the ``--full`` command line parameter.

ESCAPE also has default configuration for other type of domain managers:

* ``SDN`` entry defines a domain manager dedicated to manage external SDN-capable hardware or software switches
  with a single-purpose domain manager realized by ``SDNDomainManager``.
  This manager uses the available POX OpenFlow controller features and a static topology description file to form the domain view.

* ``OPENSTACK`` entry defines a more generic domain manager which uses the general ``UnifyDomainManager`` to manage UNIFY domains.

* ``REMOTE-ESCAPE`` entry defines a domain manager for another ESCAPE instance in the role of local DO.
  This domain manager also uses the UNIFY format with some additional data for the DO's mapping algorithm to be more deterministic.

* ``BGP-LS-SPEAKER`` gives an example for an external domain manager which discovers other providers' domains
  with the help of different external tools instead of directly managing a local DO. External domain managers have
  the authority to initiate other domain managers for the detected domain.

An additional configuration file typically contains these domain manager configurations along with the list (``MANAGERS``)
of the enabled managers. As an example several example file can be found under the ``config`` folder.

Schematic config description of domain managers:

    `NAME`
        Unique domain manager name. Used also in the ``MANAGERS`` list for enabling the defined domain manager.

        Default domain managers: ``INTERNAL``, ``SDN``, ``OPENSTACK``, ``REMOTE-ESCAPE``, ``BGP-LS-SPEAKER``.

        `module`
            (:any:`string`) Python module name where `class` can be found, e.g. ``escape.adapt.managers``
        `class`
            (:any:`string`) Python class name of the domain manager, e.g. ``UnifyDomainManager``
        `domain_name`
            (:any:`string`) Optional domain name used in the global topology view. Default value is the domain manager's config name.
        `poll`
            (:any:`bool`) Enables domain polling.
        `diff`
            (:any:`bool`) Enables differential format. Works only with UNIFY-based domain managers (inherited from :any:`AbstractRemoteDomainManager`).
        `adapters`
            (:class:`dict`) Contains the domain adapter config given directly to the adapters at creation time. Each domain manager has the required set
            of domain adapter types.

Domain Adapters
***************

The domain adapter configurations contain the parameters of the different adapter objects splitted by its roles. The adapter objects are instantiated and
configured by the container domain manager object. Each adapter class has its own role and parameter set. The defined adapter configuration is directly
given to the constructor function of the adapter class by the container domain manager.

Schematic config description of domain adapters:

    `<ROLE>`
        Unique role of the defined domain adapter. Used in the ``adapters`` configuration entry of domain managers.

        Defined roles: ``CONTROLLER``, ``MANAGEMENT``, ``TOPOLOGY``, ``REMOTE``

        `module`
            (:any:`string`) Python module name where `class` can be found, e.g. ``escape.adapt.adapters``
        `class`
            (:any:`string`) Python class name of the domain adapter, e.g. ``UnifyRESTAdapter``

    *CONTROLLER*
        Define domain adapter for controlling domain elements, typically SDN-capable switches.

        `name`
            (:any:`string`) Optional name for the OpenFlow controller instance used in the POX's core object, shouldn't be changed.
        `address`
            (:any:`string`) Address the OF controller instance bound to, e.g. ``0.0.0.0``
        `port`
            (:any:`int`) Port number the OF controller listens on, e.g. ``6653``
        `keepalive`
            (:any:`bool`) Enables internal keepalive mechanism for sending periodic OF Echo messages to switches.
        `sap_if_prefix`
            (:any:`string`) Defines the prefix of physical interfaces for SAPs, e.g. ``eth``.
            Works only with :any:`InternalPOXAdapter`.
        `binding`
            (:any:`dict`) Defines static BiSBiS name --> DPID binding for OF switches as key-value pairs, e.g. ``{"MT1": 365441792307142}``.
            Works only with :any:`SDNDomainPOXAdapter`.

    *TOPOLOGY*
        Define domain adapter for providing topology description of the actual domain.

        `net`
            (:any:`object`) Optional network object for :class:`mininet.net.Mininet`.
            Works only with :any:`InternalMininetAdapter`. Only for development!
        `path`
            (:any:`string`) Path of the static topology description :any:`NFFG` file, e.g. ``examples/sdn-topo.nffg``.
            Works only with ``SDNDomainTopoAdapter``.

    *REMOTE*
        Define domain adapter for communication with remote domain, typically through a REST-API.

        `url`
            (:any:`string`) URL of the remote domain agent, e.g. ``http://127.0.0.1:8899``
        `prefix`
            (:any:`string`) Specific prefix of the REST interface, e.g. ``/virtualizer``
        `timeout`
            (:any:`int`) Connection timeout in sec, e.g. ``5``
        `unify_interface`
            (:any:`bool`) Set the interface to use the Virtualizer format.

    *MANAGEMENT*
        Defines domain adapter for init/start/stop VNFs in the domain. Currently only NETCONF-based management is implemented!

        `server`
            (:any:`string`) Server address of the NETCONF server in the domain, e.g. ``127.0.0.1``
        `port`
            (:any:`int`) Listening port of the NETCONF server, e.g. ``830``
        `username`
            (:any:`string`) Username for the SSH connection, e.g. ``mininet``
        `password`
            (:any:`string`) Password for the SSH connection, e.g. ``mininet``
        `timeout`
            (:any:`int`) Connection timeout in sec, e.g. ``5``

Generic adaptation layer configuration
**************************************

Among the Manager configurations the `adaptation` section also contains several configuration parameters
which are mostly general parameters and have effect on the overall behavior of the Adaptation layer.

Schematic config description of general parameters:

    `RESET-DOMAINS-BEFORE-INSTALL`
        (:any:`bool`) Enables to send the resetting topology before an service install is initiated.
    `CLEAR-DOMAINS-AFTER-SHUTDOWN`
        (:any:`bool`) Enables to send the resetting topology right before shutdown of ESCAPE.
    `USE-REMERGE-UPDATE-STRATEGY`
        (:any:`bool`) Use the `REMERGE` strategy for the global view updates which stand of an explicit remove and add step
          instead of a complex update step.
    `USE-STATUS-BASED-UPDATE`
        (:any:`bool`) Use status values for the service instead of imminent domain view rewriting.
    `ENSURE-UNIQUE-ID`
        (:any:`bool`) Generate unique id for every BiSBiS node in the detected domain using the original BiSBiS id and domain name.

Infrastructure
^^^^^^^^^^^^^^

The configuration of ``infrastructure`` layer controls the Mininet-based emulation.

The ``TOPO`` path value defines the file which will be parsed and processed to build the Mininet structure.

The ``FALLBACK-TOPO`` defines an inner class which can initiate a topology if the topology file is not found.

The ``NETWORK-OPTS`` is an optional data which can be added to override the default constructor parameters of the Mininet class.

The ``Controller``, ``EE``, ``Switch``, ``SAP`` and ``Link`` dictionaries can contain optional parameters for the constructors
 of the internal Mininet-based representation. In most cases these parameters need to be left unchanged.

Other simple values can be added too to refine the control of the emulation such as enable/disable the
xterm initiation for SAPs (``SAP-xterm``) or the cleanup task (``SHUTDOWN-CLEAN``).

Schematic config description:

    `TOPO`
        (:any:`string`) Path of the topology :any:`NFFG` used to build the emulated network, e.g. ``examples/escape-mn-topo.nffg``
    `SHUTDOWN-CLEAN`
        (:any:`bool`) Uses the first received topologies to reset the detected domains before shutdown.
    `SAP-xterms`
        (:any:`bool`) Initiates xterm windows for the SAPs.
    `NETWORK-OPTS`
        (:class:`dict`) Optional parameters directly given to the main :class:`Mininet` object at build time.
    `Controller`
        (:class:`dict`) Optional parameters directly given to the Mininet's :class:`Controller` object at build time.

        `ip`
            (:any:`string`) IP address of the internal OpenFlow controller used for the Mininet's components, e.g. ``127.0.0.1``
        `port`
            (:any:`int`) Port the internal OpenFlow controller listens on, e.g. ``6653``
    `EE`
        (:class:`dict`) Optional parameters directly given to the Mininet's :class:`EE` objects at build time.
    `Link`
        (:class:`dict`) Optional parameters directly given to the Mininet's :class:`Link` objects at build time.
    `SAP`
        (:class:`dict`) Optional parameters directly given to the Mininet's :class:`SAP` objects at build time.
    `Switch`
        (:class:`dict`) Optional parameters directly given to the Mininet's :class:`Switch` objects at build time.
    `FALLBACK-TOPO`
        (:class:`dict`) Defines fallback topology for the Infrastructure layer (only for development).

        `module`
            (:any:`string`) Python module name where `class` can be found, e.g. ``escape.infr.topology``
        `class`
            (:any:`string`) Python class name of the *Topology*, e.g. ``FallbackDynamicTopology``

Visualizations
^^^^^^^^^^^^^^
ESCAPE has an additional mechanism which collects the intermediate formats of a service request
and sends them to a remote database through a REST-API for visualization purposes.

The visualization feature can be enabled with the ``--visualization`` command line argument.

The `visualization` config section contains the connection parameters for the remote visualization.

Schematic config description:

    `url`
        (:any:`string`) Base URL of the remote database, e.g. ``http://localhost:8081``
    `rpc`
        (:any:`string`) The prefix of the collector RPC, e.g. ``edit-config``
    `instance_id`
        (:any:`string`) Optional distinguishing identification

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

ESCAPE has several testcases formed as Unit test. These test can be found under
the `test` folder.

Dependent packages for the test can be installed with the `install_requirements.sh` script.
To run the test see the main running script:

```text
$ ./run_tests.py -h
usage: run_tests.py [-h] [--failfast] [--show-output] [--timeout t]
                    [--standalone] [--verbose]
                    [testcases [testcases ...]]

ESCAPE Test runner

positional arguments:
  testcases          list test case names you want to run. Example:
                     ./run_tests.py case05 case03 --show-output

optional arguments:
  -h, --help         show this help message and exit
  --failfast, -f     Stop on first failure
  --show-output, -o  Show ESCAPE output
  --timeout t, -t t  define explicit timeout in sec (default: 30s)
  --standalone, -s   run standalone mode: no timeout, no quitting
  --verbose, -v      Run in verbose mode and show output
```

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

Topmost POX modules for UNIFY's layers/sublayers
------------------------------------------------

.. toctree::
    :maxdepth: 2
    :titlesonly:

    UNIFY <unify>

License and Contacts
====================

Licensed under the Apache License, Version 2.0, see LICENSE file.

    Copyright (C) 2017 by
    János Czentye - janos.czentye@tmit.bme.hu
    Balázs Németh - balazs.nemeth@tmit.bme.hu
    Balázs Sonkoly - balazs.sonkoly@tmit.bme.hu

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

