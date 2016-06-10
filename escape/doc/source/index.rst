####################################
Welcome to ESCAPEv2's documentation!
####################################

Overview
========

On the one hand, ESCAPE (Extensible Service ChAin Prototyping
Environment) is a general prototyping framework which supports the
development of several parts of the service chaining architecture
including VNF implementation, traffic steering, virtual network
embedding, etc.  On the other hand, ESCAPE is a proof of concept
prototype implementing a novel SFC (Service Function Chaining)
architecture proposed by `EU FP7 UNIFY project <https://www.fp7-unify.eu/>`__.
It is a realization of the UNIFY service programming and orchestration framework
which enables the joint programming and virtualization of cloud and networking
resources.

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

Because the core ESCAPEv2 relies on POX and written in Python there is no need
for explicit compiling or installation. The only requirement need to be
pre-installed is a Python interpreter.

The recommended Python version, in which the development and mostly the testing
are performed, is the standard CPython **2.7.11**.

.. important::

  Only the standard CPython interpreter is supported!

If you want to use a different and separated Python version check the Virtual
Environment section below.

The best choice of platform on wich ESCAPEv2 is recommended to install and the
*install-dep.sh* is tested is Ubuntu 14.04.4 LTS.

However ESCAPEv2 is developed on Kubuntu 16.04, some issues are experienced
related to SAP-xterm initiation in case the platform was an Ubuntu 16.04 server
image and ESCAPEv2 was started through an SSH channel.

.. important::
    Considering this limitation we recommend to use the older 14.04 LTS version in
    case ESCAPEv2 is intended to run on a VM without any graphical interface.

The install script (*install-dep.sh*) supports both LTS version.

The preferred way
-----------------

1. Download one of pre-build Ubuntu LTS image or create one in your VM manager.

2. Create the ``.ssh`` folder in the home directory and copy your private RSA key
which you gave on the *fp7-unify.eu GitLab* site into the VM with the name
``id_rsa``. If you use a VM image then the following commands can be used
in the VM to copy your RSA key from your host:

  .. code-block:: bash

    $ cd
    $ mkdir .ssh
    $ scp <your_user>@<host_ip>:~/.ssh/<your_ssh_key> ~/.ssh/id_rsa
    $ sudo chmod 700 .ssh && sudo chmod 600 .ssh/id_rsa

3. Clone the shared escape repository in a folder named: *escape*.

  .. code-block:: bash

    $ git clone git@gitlab.fp7-unify.eu:Balazs.Sonkoly/escape-shared.git escape

4. Install the necessary dependencies with the ``install_dep.sh`` script (system
and Python packages, OpenYuma with VNFStarter module):

  .. code-block:: bash

    $ cd escape
    $ ./install_dep.sh

  Usage:

  .. code-block:: text

    $ ./install-dep.sh -h
    Usage: ./install-dep.sh [-a] [-c] [-d] [-g] [-h] [-i]
    Install script for ESCAPEv2

    options:
        -a:   (default) install (A)ll ESCAPEv2 components (identical with -cgi)
        -c:   install (C)ore dependencies for Global Orchestration
        -d:   install additional dependencies for (D)evelopment and test tools
        -g:   install dependencies for our rudimentary (G)UI
        -h:   print this (H)elp message
        -i:   install components of (I)nfrastructure Layer for Local Orchestration


  In a high level the script above carries the following things:
    * Install the necessary system and Python packages
    * Compile and install the `OpenYuma <https://github.com/OpenClovis/OpenYuma>`__
      tools with our `VNF_starter` module
    * Compile and install `Click <http://read.cs.ucla.edu/click/click>`__ modular
      router and The Click GUI: `Clicky <http://read.cs.ucla.edu/click/clicky>`__
    * Install `neo4j <http://neo4j.com/>`__ graph database for NFIB
    * If Mininet is not installed on the VM, install the ``mnexec`` utility and
      create a system user: **mininet** for NETCONF communication

5. Run ESCAPEv2 with one of the commands listed in a later section. To see the
available arguments of the top starting script check the help menu:

  .. code-block:: bash

    $ ./escape.py --help

To verify ESCAPEv2's components are installed and set up correctly you can run
the following command and test the reachability of the initiated SAPs (``xterm``)
with ``ping``:

  .. code-block:: bash

    $ ./escape.py -df -s examples/escape-mn-req.nffg

    # SAP1 xterm
    $ ping sap2
    # SAP2 xterm
    $ ping sap1

This command start the full stack ESCAPEv2 with the default topology
(`examples/escape-mn-topo.nffg`) and initiate a service request consists of a
*HeaderCompressor* and a *HeaderDecompressor* VNF for one direction and a simple
*Forwarder* VNF for the backward direction. The two initiated SAP can reach each
other.

.. important::

    If you want to initiate more then 15 node (including switches and also Execution
    Environments) in the Mininet-based Infrastructure layer you should recompile
    the OpenSSH server from source to increase the number of possible listening
    ports up to 256. In this case you can use the following commands:

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

Obviously you can install ESCAPEv2 on your host or on an empty VM too. For that
you need to install the requirements manually.

To install the Python dependencies and other system packages you can use the
dependency installation script mentioned above or you can do it manually.

**Dependencies**

If you don't want to install the Python dependencies globally you can follow the
hard way and setup a virtual environment. Otherwise just run the following
command(s):

Required system and Python packages:

.. code-block:: bash

    $ sudo apt-get -y install python-dev python-pip zlib1g-dev libxml2-dev \
    libxslt1-dev libssl-dev libffi-dev neo4j=2.2.7

    $ sudo -H pip install numpy jinja2 py2neo networkx requests ncclient \
    cryptography==1.3.1

For Mininet emulation tool:

.. code-block:: bash

    $ sudo apt-get -y install gcc make socat psmisc xterm ssh iperf iproute \
    telnet python-setuptools cgroup-bin ethtool help2man pyflakes pylint pep8 \
    openvswitch-switch

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

    $ sudo -H pip install tornado

Other required programs (OpenYuma, click, neo4j, etc.), which are installed by
the `install_dep.sh` script by default, are also need to be installed manually.

On Ubuntu the ``neo4j`` database server (>=2.3.1) does not work with
OpenJDK 7 correctly. In this case the ``neo4j`` server is need to be downgraded
or the latest OpenJDK 8 need to be installed.

If a newer version of ``neo4j`` has been installed on the system, use the
following commands to downgrade. In this case the authentication bypass needs
to be done again.

.. code-block:: bash

    $ sudo -i
    $ apt-get purge neo4j
    $ rm -rf /var/lib/neo4j/data/
    $ rm -rf /etc/neo4j/
    $ apt-get install -y neo4j=2.2.7
    $ apt-mark hold neo4j

In extreme cases, e.g. the `install_dep.sh` ran into an error, you should install
these dependencies one by one according to your OS, distro or development environment.
For that you can check the steps in the install script and/or the online documentations
referenced in entry 4. of the previous subsection.

To use the Infrastructure Layer of ESCAPEv2, Mininet must be installed on the
host (more precisely the **Open vSwitch** implementation and the specific
**mnexec** utility is only required to be installed globally).

If Mininet has already been installed, there should be nothing to do. ESCAPEv2
uses the specifically-modified Mininet files in the project folder
(*Mininet v2.1.0mod-ESCAPE*) which use the globally installed Mininet utility
scripts (mnexec).

Otherwise these assets have to be install manually which could be done from our
Mininet folder (escape/mininet) or from the official Mininet git repository
(`<https://github.com/mininet/mininet/>`__). Mininet has an install script for
the installations (see the help with the ``-h`` flag) but this script will install
the whole Mininet tool with unnecessary packages:

.. code-block:: bash

    $ sudo mininet/util/install.sh -n

In this case you can run the following command to check whether the installation
was correct or not:

.. code-block:: bash

    $ sudo mn --test pingall

But the script will install the whole Mininet package and additional dependencies.
If you want to do a minimal install, compile the ``mnexec`` source by manual and
copy the binary into a folder which is in your ``PATH`` system variable.

.. code-block:: bash

    $ cd mininet/
    $ make mnexec
    $ sudo install mnexec /usr/bin

However you can install the Open vSwitch packages manually:

.. code-block:: bash

    $ sudo apt-get install openvswitch-switch

If the command complains about the Open vSwitch not installed then you have to
install it from source. See more on `<http://openvswitch.org/download/>`_. On the
newest distributions (e.g. Ubuntu 15.04) more steps and explicit patching is
required. For that the only way is sadly to use google and search for it based
on your distro. But a good choice to start here:
https://github.com/mininet/mininet/wiki/Installing-new-version-of-Open-vSwitch

.. hint::

  If your intention is to run ESCAPEv2 in a virtual machine, you should really
  consider to use one of the pre-build Mininet VM images.

If you want to develop on your host machine, you should take care of a user for
the netconfd server. This user's name and password will be used for the
connection establishment between ESCAPEv2 and the Execution Environments (EE).

.. note::

  These parameters can be changed conveniently in the global config under the
  config entry of *VNFStarter Adapter* .

An another solution is to define a system user for the netconfd. To create a user
(advisable to use `mininet` as in the Mininet-based VM) use the following commands:

.. code-block:: bash

    $ sudo adduser --system --shell /bin/bash --no-create-home mininet
    $ sudo addgroup mininet sudo
    $ echo "mininet:mininet" | sudo chpasswd

For security reasons it's highly recommended to limit the SSH connections for the
`mininet` user only to localhost.

.. code-block:: bash

    $ sudo echo -e 'Match Host *,!localhost\n  DenyUsers  mininet' >> /etc/ssh/sshd_config
    $ sudo service ssh reload

Check the created user with the following command:

.. code-block:: bash

    $ ssh mininet@localhost

Setup a Virtual environment (optional)
--------------------------------------

ESCAPEv2 also supports Python-based virtual environment in order to setup a
different Python version or even a different interpreter (not recommended) for
ESCAPEv2 or to separate dependent packages from system-wide Python.

To setup a virtual environment based on `virtualenv <https://virtualenv.readthedocs.org/en/latest/>`__
Python package with a standalone CPython 2.7.10 interpreter run the following script:

.. code-block:: bash

    $ ./set_virtualenv.sh

This script does the following steps:
  * Install additional dependencies
  * Download, compile and install the 2.7.10 (currently the newest) Python
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
        -p   set Python version (default: 2.7.10)
        -h   show this help message and exit
      Example: ./set_virtualenv.sh -p 2.7.9
      Based on virtualenv. More information: virtualenv -h


The ``escape.py`` script can detect the ``.use_virtualenv`` file automatically
and activates the virtual environment transparently. If you want to disable the
virtual environment then just delete the ``.use_virtualenv`` file.

The virtualenv can also be enabled by the ``--environment`` flag of the topmost
``escape.py`` script.

In order to setup the environment manually, define other Python version/interpreter,
enable system-wide Python / ``pip`` packages

.. code-block:: bash

    $ virtualenv -p=<python_dir> --no-site-packages/system-site-packages <...> escape

or activate/deactivate the environment manually

.. code-block:: bash

    $ cd escape
    $ source bin/activate # activate virtual environment
    $ deactivate  # deactivate

check the content of the setup script or see the
`Virtualenv User Guide <https://virtualenv.readthedocs.org/en/latest/userguide.html>`_.

ESCAPEv2 example commands
=========================

ESCAPEv2 can be started with the topmost ``escape.py`` script in the project's
root directory or can be started calling the ``pox.py`` script directly with the
layer modules and necessary arguments under the `pox` directory.

The simplest use-case
---------------------

Run ESCAPEv2 with the Mininet-based Infrastructure layer and debug logging mode:

.. code-block:: bash

    $ ./escape.py -df

Usage:

.. code-block:: text

    $ ./escape.py -h
      usage: escape.py [-h] [-v] [-a] [-c path] [-d] [-e] [-f] [-i] [-p] [-r]
                       [-s file] [-t file] [-x] [-V] [-4]
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
        -d, --debug           run the ESCAPE in debug mode
        -e, --environment     run ESCAPEv2 in the pre-defined virtualenv environment
        -f, --full            run the infrastructure layer also
        -i, --interactive     run an interactive shell for observing internal states
        -p, --POXlike         start ESCAPEv2 in the actual interpreter using ./pox
                              as working directory instead of using a separate shell
                              process with POX's own PYTHON env
        -r, --rosapi          start the REST-API for the Resource Orchestration
                              sublayer (ROS)
        -s file, --service file
                              skip the SAS REST-API initiation and read the service
                              request from the given file
        -t file, --topo file  read the topology from the given file explicitly
        -x, --clean           run the cleanup task standalone and kill remained
                              programs, interfaces, veth parts and junk files
        -V, --visualization   run the visualization module to send data to a remote
                              server
        -4, --cfor            start the REST-API for the Cf-Or interface
        ...                   optional POX modules

During a test or development the ``--debug`` flag is almost necessary.

If you want to run a test topology, use the ``--full`` flag to initiate the
Infrastructure layer also.
ESCAPEv2 will parse the topology description form file (``escape-mn-topo.nffg``
by default) and start the Infrastructure layer with the Mininet-based emulation.

If the request is in a file it's more convenient to give it with the ``--service``
initial parameter and not bother with the REST-API.

If you want to initiate the Mininet-based infrastructure layer and use ESCAPE as
the local orchestrator you can use the ``--agent`` flag.

With ``--agent`` flag ESCAPEv2 will initiate the ROS API for communication with
upper layers instead of initiate the upper Service Layer.
Note to mention that this flag also effects on different parts of the ESCAPEv2's
operation therefore it is not equivalent with the pair of ``--full --rosapi``!

An additional configuration file can be given with the ``--config`` flag. The
configuration file is loaded during initialization and ESCAPEv2 only updates
the default configuration instead of replaces it in order to minimize the sizes
of the additional parameters.

The most common changes in the configurations is the file path of the initial
topology which is used by the Infrastructure layer to initiate the Mininet-emulated
network. To simplify this case the topology file can be given with the ``--topo``
parameter explicitly.

If an error is occurred or need to observe the internal states you can start
ESCAPEv2 with an interactive Python shell using the ``--interactive`` flag.

With the ``--environment`` flag ESCAPEv2 can be started in a pre-defined virtualenv
environment whether the virtualenv is permanently enabled with the
``.use_virtualenv`` file or not.

With the ``--visualization`` flag ESCAPEv2 will send topologies in Virtualizer format
to a predefined remote server for the purpose of visualization.

The main layers which grouping the entities are reachable through the main POX
object called ``core`` with the names:

  * ``service`` - Service layer
  * ``orchestration`` - Resource Orchestration Sublayer
  * ``adaptation`` - Controller Adaptation Sublayer
  * ``infrastructure`` - Infrastructure layer

.. hint::

  In the interactive shell the tab-auto completion is working in most cases.

So a possible scenario for testing ESCAPEv2 with a test request given in a file
and check the state of the DoV:

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

More advanced commands (mostly advisable for testing purposes)
--------------------------------------------------------------

For more flexible control ESCAPEv2 can be started directly with POX's starting
script under the ``pox`` folder.

.. note::

  The topmost ``escape.py`` script uses this ``pox.py`` script to start ESCAPEv2.
  In debug mode the assembled POX command is printed also.

Basic command:

.. code-block:: bash

    $ ./pox.py unify

One of a basic commands for debugging:

.. code-block:: bash

    $ ./pox.py --verbose unify py

For forcing to log on DEBUG level the ``--verbose`` flag of the ``pox.py``
script can be used. Or the *log.level* POX module can be used which would be the
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
    $ ./pox.py adaptation --mapped_nffg=<path> ...

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

REST APIs
=========

ESCAPEv2 has currently 3 REST-APIs.

The Service layer has a REST-API for communication with users/GUI. This API is
initiated by default when the layer was started.

The Resource Orchestration layer has 2 API which are only initiated if the
appropriate flag is given to the starting script.
The ROS API can be used for communicating with other UNIFY layer e.g. a
Controller Adaptation Sublayer of a standalone ESCAPEv2 in a multi-level
scenario or with a GUI.
The CfOr API realizes the interface for service elasticity feature.

Common API functions
--------------------

*Operations:*   Every API has the following 3 function (defined in :any:`AbstractRequestHandler`):

+-------------------+----------------+-------------------+----------------------------------------------+
|      Path         |     Params     |     HTTP verbs    | Description                                  |
+===================+================+===================+==============================================+
| */version*        | ``None``       | GET               | Returns with the current version of ESCAPEv2 |
+-------------------+----------------+-------------------+----------------------------------------------+
| */ping*           | ``None``       | GET, POST         | Returns with the "OK" string                 |
+-------------------+----------------+-------------------+----------------------------------------------+
| */operations*     | ``None``       | GET               | Returns with the implemented operations      |
+-------------------+----------------+-------------------+----------------------------------------------+

Service API specific functions
------------------------------

The SAS API is automatically initiated by the Service layer. If the ``--service`` flag
is used the service request is loaded from the given file and the REST-API
initiation is skipped.

*Content Negotiation:* The Service layer's RESTful API accepts and returns data
only in JSON format.

The following functions are defined in :any:`ServiceRequestHandler`.

+-------------------+----------------+-------------------+----------------------------------------------------------------+
|      Path         |     Params     |     HTTP verbs    | Description                                                    |
+===================+================+===================+================================================================+
| */topology*       | ``None``       | GET, POST         | Returns with the resource view of the Service layer            |
+-------------------+----------------+-------------------+----------------------------------------------------------------+
| */sg*             | ``NFFG``       | POST              | Initiate given NFFG. Returns the initiation is accepted or not |
+-------------------+----------------+-------------------+----------------------------------------------------------------+

ROS API specific functions
--------------------------

Can be started with the ``--agent`` or ``--rosapi`` initial flags.

The following functions are defined in :any:`ROSAgentRequestHandler`.

+-------------------+----------------+-------------------+-------------------------------------------+
|      Path         |     Params     |     HTTP verbs    | Description                               |
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
|      Path         |     Params     |     HTTP verbs    | Description                                                               |
+===================+================+===================+===========================================================================+
| */get-config*     | ``None``       | GET, POST         | Returns with the resource view from the assigned Virtualizer              |
+-------------------+----------------+-------------------+---------------------------------------------------------------------------+
| */edit-config*    | ``NFFG``       | POST              | Initiate given NFFG.                                                      |
+-------------------+----------------+-------------------+---------------------------------------------------------------------------+

Configuration
=============

ESCAPEv2 has a default configuration under the `escape` package (in the
`__init__.py` file as ``cfg``). This configuration contains the necessary
information for manager/adapter initializations, remote connections, etc. and
also provides the base for the internal running configuration.

If you want to override some of the parameters you can change the default values
in the ``cfg`` directly (not preferred) or you can just define them in an
additional config file.

The default configuration file which ESCAPEv2 is looking for is ``escape.config``.
At every start ESCAPEv2 checks the presence of this file and updates/overrides
the running configuration if it's necessary.

The ``escape.py`` starting script also provides the opportunity to specify a
different configuration file with the ``--config`` initial argument.

The additional config can be added only in JSON format, but the structure of the
configuration is strictly follows the default configuration which is defined in Python
with basic data structures.

The configuration units (coherent values, single boolean flags, paths, etc.) are
handled through the main :any:`ESCAPEConfig` class so every possible configuration
entry has an assigned `getter` function in the main class.

.. important::

  The configurations is parsed during the starting process. Changes in the config
  file have no effect at runtime.

Configuration structure
-----------------------

The configurations is divided to 4 parts according to the UNIFY's / ESCAPEv2's
main layers, namely ``service``, ``orchestration``, ``adaptation`` and
``infrastructure``.

service and orchestration
^^^^^^^^^^^^^^^^^^^^^^^^^

The top 2 layer (``service`` and ``orchestration``) has similar configuration
parameters. In both layers the mapping process can be controlled with the following
entries:

  * **MAPPER** defines the mapping class which controls the mapping process
    (inherited from :any:`AbstractMapper`)
  * **STRATEGY** defines the mapping strategy class which calls the actual mapping
    algorithm (inherited from :any:`AbstractMappingStrategy`)
  * **PROCESSOR** defines the Processor class which contains the pre/post mapping
    functions for validation and other auxiliary functions (inherited from
    :any:`AbstractMappingDataProcessor`)

The values of class configurations (such the entries above) always contains the
**module** and **class** names of the actual class. With this approach ESCAPEv2 can
also instantiate and use different implementations from external Python packages.
The only requirement for these classes is to be included in the scope of ESCAPEv2
(more precisely in the PYTHONPATH of the Python interpreter which runs ESCAPEv2).

.. note::

  Every additional subdirectory in the project's root is always added to the search
  path (scope) dynamically at initial time by the main ``escape`` module.

The mapping process and pre/post processing can be enabled/disabled with the
``mapping-enabled`` (boolean) and ``enabled`` (boolean) values under the
appropriate entries.

The mapping algorithm called in the Strategy class can be initiated in a worker
thread with the ``THREADED`` flag, but this feature is still in experimental phase.

These 2 layers can initiate REST-APIs also. The initial parameters are defined
under the names of the APIs:

  * **REST-API** - top REST-API in the SAS layer
  * **Sl-Or** - Sl-Or interface in the ROS layer for external components
    i.e. for upper UNIFY entities, GUI or other ESCAPEv2 instance in a distributed,
    multi-layered scenario
  * **Cf-Or** - Cf-Or interface in the ROS layer for supporting service elasticity
    feature

These REST-API configurations consist of

  * a specific handler class which initiated for every request and handles the
    requests (inherited from :any:`AbstractRequestHandler`) defined with the
    ``module`` and ``class`` pair
  * address of the REST-API defined with the ``address`` and ``port`` (integer)
    pair
  * ``prefix`` of the API which appears in the URL right before the REST functions
  * optionally the type of used Virtualizer (``virtualizer_type``) which filters
    the data flow of the API (currently only supported the global (`GLOBAL`) and
    single BiS-BiS (`SINGLE`) Virtualizer)

adaptation
^^^^^^^^^^

The ``adaptation`` layer contains the different Manager (inherited from
:any:`AbstractDomainManager`) classes under their specific name which is defined
in the ``name`` class attribute. These configurations are used by the
:any:`ComponentConfigurator` to initiate the required components dynamically.
Every Manager use different Adapters (inherited from :any:`AbstractESCAPEAdapter`)
to hide the specific protocol-agnostic steps in the communication between the
ESCAPE orchestrator and network elements. The configurations of these Adapters
can be found under the related Manager names in order to be able to initiate
multiple Managers based on the same class with different Adapter configurations.
The class configurations can be given by the ``module`` and ``class`` pair
similar way as so far.
Other values such as path, url, keepalive, etc. will be forwarded to the
constructor of the component at initialization time so the possible config names
and types result from the constructor attributes.

The ``MANAGERS`` config value contains the Managers need to be initiated.

.. hint::

  In order to activate a manager and manage the specific domain add the config
  name of the DomainManager to the ``MANAGERS`` list. The manager will be
  initiated with other Managers at boot time of ESCAPEv2.


With the ``RESET-DOMAINS-AFTER-SHUTDOWN`` config entry can be enabled/disabled
the cleanup of the domains.

infrastructure
^^^^^^^^^^^^^^

The configuration of ``infrastructure`` layer controls the Mininet-based
emulation.

The ``TOPO`` path value defines the file which will be parsed and processed to
build the Mininet structure.

The ``FALLBACK-TOPO`` defines an inner class which can initiate a topology if
the topology file is not found.

The ``NETWORK-OPTS`` is an optional data which can be added to override the
default constructor parameters of the Mininet class.

The ``Controller``, ``EE``, ``Switch``, ``SAP`` and ``Link`` dictionaries can
contain optional parameters for the constructors of the internal Mininet-based
representation. In most cases these parameters need to be left unchanged.

Other simple values can be added too to refine the control of the emulation such
as enable/disable the xterm initiation for SAPs (``SAP-xterm``) or the cleanup
task (``SHUTDOWN-CLEAN``).

Default configuration
---------------------

The following snippet represents the default configuration of ESCAPEv2
in JSON format. An additional configuration file should be based on a subpart of
this configurations structure.

.. code-block:: json

    {
      "service":
        {
          "SERVICE-LAYER-ID": "ESCAPE-SERVICE",
          "MAPPER":
            {
              "module": "escape.service.sas_mapping",
              "class": "ServiceGraphMapper",
              "mapping-config":
                {
                  "full_remap": true
                },
              "mapping-enabled": false
            },
          "STRATEGY":
            {
              "module": "escape.service.sas_mapping",
              "class": "DefaultServiceMappingStrategy",
              "THREADED": false
            },
          "PROCESSOR":
            {
              "module": "escape.util.mapping",
              "class": "ProcessorSkipper",
              "enabled": false
            },
          "REST-API":
            {
              "module": "escape.service.sas_API",
              "class": "ServiceRequestHandler",
              "prefix": "escape",
              "address": "0.0.0.0",
              "port": 8008,
              "unify_interface": false
            }
        },
      "orchestration":
        {
          "MAPPER":
            {
              "module": "escape.orchest.ros_mapping",
              "class": "ResourceOrchestrationMapper",
              "mapping-config":
                {
                  "full_remap": true
                },
              "mapping-enabled": true
            },
          "STRATEGY":
            {
              "module": "escape.orchest.ros_mapping",
              "class": "ESCAPEMappingStrategy",
              "THREADED": false
            },
          "PROCESSOR":
            {
              "module": "escape.util.mapping",
              "class": "ProcessorSkipper",
              "enabled": true
            },
          "ESCAPE-SERVICE":
            {
              "virtualizer_type": "SINGLE"
            },
          "Sl-Or":
            {
              "module": "escape.orchest.ros_API",
              "class": "ROSAgentRequestHandler",
              "prefix": "escape",
              "address": "0.0.0.0",
              "port": 8888,
              "virtualizer_type": "GLOBAL",
              "unify_interface": true
            },
          "Cf-Or":
            {
              "module": "escape.orchest.ros_API",
              "class": "CfOrRequestHandler",
              "prefix": "cfor",
              "address": "0.0.0.0",
              "port": 8889,
              "virtualizer_type": "GLOBAL",
              "unify_interface": true
            }
        },
      "adaptation":
        {
          "MANAGERS": [
          ],
          "RESET-DOMAINS-BEFORE-INSTALL": false,
          "CLEAR-DOMAINS-AFTER-SHUTDOWN": true,
          "USE-REMERGE-UPDATE-STRATEGY": true,
          "ENSURE-UNIQUE-ID": true,
          "INTERNAL":
            {
              "module": "escape.adapt.managers",
              "class": "InternalDomainManager",
              "poll": false,
              "adapters": {
                "CONTROLLER":
                  {
                    "module": "escape.adapt.adapters",
                    "class": "InternalPOXAdapter",
                    "name": null,
                    "address": "127.0.0.1",
                    "port": 6653,
                    "keepalive": false
                  },
                "TOPOLOGY":
                  {
                    "module": "escape.adapt.adapters",
                    "class": "InternalMininetAdapter",
                    "net": null
                  },
                "MANAGEMENT":
                  {
                    "module": "escape.adapt.adapters",
                    "class": "VNFStarterAdapter",
                    "username": "mininet",
                    "password": "mininet",
                    "server": "127.0.0.1",
                    "port": 830,
                    "timeout": 5
                  }
              }
            },
          "SDN": {
            "module": "escape.adapt.managers",
            "class": "SDNDomainManager",
            "poll": false,
            "domain_name": "SDN-MICROTIK",
            "adapters": {
              "CONTROLLER":
                {
                  "module": "escape.adapt.adapters",
                  "class": "SDNDomainPOXAdapter",
                  "name": null,
                  "address": "0.0.0.0",
                  "port": 6633,
                  "keepalive": false,
                  "binding": {
                    "MT1": "0x14c5e0c376e24",
                    "MT2": "0x14c5e0c376fc6"
                  }
                },
              "TOPOLOGY":
                {
                  "module": "escape.adapt.adapters",
                  "class": "SDNDomainTopoAdapter",
                  "path": "examples/sdn-topo.nffg"
                }
            }
          },
          "REMOTE-ESCAPE":
            {
              "module": "escape.adapt.managers",
              "class": "RemoteESCAPEDomainManager",
              "poll": false,
              "adapters": {
                "REMOTE":
                  {
                    "module": "escape.adapt.adapters",
                    "class": "RemoteESCAPEv2RESTAdapter",
                    "url": "http://192.168.50.129:8888",
                    "prefix": "escape",
                    "unify_interface": true
                  }
              }
            },
          "REMOTE-ESCAPE-ext":
            {
              "module": "escape.adapt.managers",
              "class": "RemoteESCAPEDomainManager",
              "domain_name": "extESCAPE",
              "poll": false,
              "adapters": {
                "REMOTE":
                  {
                    "module": "escape.adapt.adapters",
                    "class": "RemoteESCAPEv2RESTAdapter",
                    "url": "http://192.168.50.128:8888",
                    "prefix": "escape",
                    "unify_interface": true
                  }
              }
            },
          "OPENSTACK":
            {
              "module": "escape.adapt.managers",
              "class": "OpenStackDomainManager",
              "poll": false,
              "adapters": {
                "REMOTE":
                  {
                    "module": "escape.adapt.adapters",
                    "class": "UnifyRESTAdapter",
                    "url": "http://localhost:8081",
                    "timeout": 5
                  }
              }
            },
          "UN":
            {
              "module": "escape.adapt.managers",
              "class": "UniversalNodeDomainManager",
              "poll": false,
              "adapters": {
                "REMOTE":
                  {
                    "module": "escape.adapt.adapters",
                    "class": "UnifyRESTAdapter",
                    "url": "http://localhost:8082"
                  }
              }
            },
          "DOCKER":
            {
              "module": "escape.adapt.managers",
              "class": "DockerDomainManager",
              "poll": false
            }
        },
      "infrastructure":
        {
          "TOPO": "examples/escape-mn-topo.nffg",
          "NETWORK-OPTS": {
          },
          "Controller": {
            "ip": "127.0.0.1",
            "port": 6653
          },
          "EE": null,
          "Switch": null,
          "SAP": null,
          "Link": null,
          "FALLBACK-TOPO":
            {
              "module": "escape.infr.topology",
              "class": "FallbackDynamicTopology"
            },
          "SAP-xterms": true,
          "SHUTDOWN-CLEAN": true
        },
      "additional-config-file": "escape.config",
      "visualization":
        {
          "url": "http://localhost:8081",
          "rpc": "edit-config",
          "instance_id": null
        }
    }


Development
===========

Suggested IDE: `Pycharm Community Edition <https://www.jetbrains.com/pycharm/>`__

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

.. code-block:: bash

  $ Ready.
  $ ESCAPE>
  $ ESCAPE> core.service.rest_api.stop()

One instance of the *ESCAPEInteractiveHelper* is registered by default under the
name: *helper*. An example to dump the running configuration of ESCAPEv2:

.. code-block:: bash

  $ ESCAPE> core.helper.config()
    {
        "infrastructure": {
            "NETWORK-OPTS": null,
            "FALLBACK-TOPO": {
                "class": "BackupTopology",
                "module": "escape.infr.topology"
    ...

More help and description about the useful helper functions and the *core*
object is in the comments/documentation and on the POX's
`wiki <https://openflow.stanford.edu/display/ONL/POX+Wiki#POXWiki-POXAPIs>`__
site.

API documentation
=================

This documentation contains only the Python class structure and description of
the multi-domain multi-level service orchestrator.

Our Mininet-based infrastructure, which is an extended version of
Mininet, is not documented here.

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

Contacts
========

János Czentye - janos.czentye@tmit.bme.hu

Balázs Sonkoly - balazs.sonkoly@tmit.bme.hu

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

