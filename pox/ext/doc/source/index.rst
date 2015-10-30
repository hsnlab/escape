Welcome to ESCAPEv2's documentation!
====================================

Welcome! This is the API documentation for **ESCAPEv2**.

Overview
--------

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

.. hint::

   For more information on the concept, motivation and demo use-cases, we
   suggest the following papers.

   **UNIFY Architecture:**

   * Balázs Sonkoly, Robert Szabo, Dávid Jocha, János Czentye, Mario
     Kind, and Fritz-Joachim Westphal, *UNIFYing Cloud and Carrier
     Network Resources: An Architectural View*, in Proc. IEEE Global
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

API documentation
-----------------
This documentation contains only the Python class structure and description of
the multi-domain multi-level service orchestrator.

Our Mininet-based infrastructure, which is an extended version of
Mininet, is not documented here.

ESCAPEv2 class structure
++++++++++++++++++++++++

.. toctree::
    :maxdepth: 6
    :titlesonly:

    escape

Topmost POX modules for UNIFY's layers/sublayers
++++++++++++++++++++++++++++++++++++++++++++++++

.. toctree::
    :maxdepth: 2
    :titlesonly:

    UNIFY <unify>

Installation
------------

Because ESCAPEv2 relies on POX and written in Python there is no need for
explicit compiling or installation. The only requirement need to be pre-installed
is a Python interpreter.

The recommended Python version in which the development and mostly the testing are
performed is the standard CPython **2.7.9** but the 2.7.6 (pre-build Mininet VM)
and 2.7.10 versions are also supported.

.. warning::

  Only the standard CPython interpreter is supported!

If you want to use a different and separated Python version check the Virtual
Environment section below.

The preferred way
+++++++++++++++++

1. Download one of pre-build Mininet image which has already had the necessary
tools (Mininet scripts and Open vSwitch).

  https://github.com/mininet/mininet/wiki/Mininet-VM-Images

  The images are in an open virtual format (``.ovf``) which can be imported by
  most of the virtualization managers.

  Username/password: **mininet/mininet**

  Our implementation relies on Mininet 2.1.0, but ESCAPEv2 has been tested on
  the newest image too (Mininet 2.2.1 on Ubuntu 14.04 - 64 bit) and no problem
  has occurred yet!

2. Create the ``.ssh`` folder in the home directory and copy your private RSA key
which you gave on the *fp7-unify.eu GitLab* site into the VM with the name
``id_rsa``. If you use the Mininet image then the following command can be used
in the VM to copy your RSA key from your host:

  .. code-block:: bash

    $ cd
    $ mkdir .ssh
    $ scp <your_user>@<host_ip>:~/.ssh/<your_ssh_key> ~/.ssh/id_rsa

3. Clone the shared escape repository in a folder named:
*escape*.

  .. code-block:: bash

    $ git clone git@gitlab.fp7-unify.eu:Balazs.Sonkoly/escape-shared.git escape

4. Install the necessary dependencies with the ``install_dep.sh`` script (system
and Python packages, OpenYuma with VNFStarter module):

  .. code-block:: bash

    $ cd escape
    $ ./install_dep.sh


  In a high level the script above does the following things:
    * Install the necessary system and Python packages
    * Compile and install the `OpenYuma <https://github.com/OpenClovis/OpenYuma>`__
      tools with our `VNF_starter` module
    * Compile and install `Click <http://read.cs.ucla.edu/click/click>`__ modular
      router and The Click GUI: `Clicky <http://read.cs.ucla.edu/click/clicky>`__
    * Install `neo4j <http://neo4j.com/>`__ graph database for NFIB

5. Run ESCAPEv2 with one of the commands listed in a later section. To see the
available arguments of the top stating script check the help menu:

  .. code-block:: bash

    $ ./escape.py --help

The hard way
++++++++++++

Obviously you can install ESCAPEv2 on your host or on an empty VM too. For that
you need to install the requirements manually.

To install the Python dependencies and other system packages you can use the
dependency installation script mentioned above or do it manually.

**Dependencies**

If you don't want to install the Python dependencies globally you can follow the
hard way and can setup a virtual environment. Otherwise just run the following
command(s):

Required system and Python packages:

.. code-block:: bash

    $ sudo apt-get -y install libxml2-dev libxslt1-dev zlib1g-dev libsqlite3-dev \
        python-pip python-libxml2 python-libxslt1 python-lxml python-paramiko python-dev \
        python-networkx libxml2-dev libssh2-1-dev libgcrypt11-dev libncurses5-dev \
        libglib2.0-dev libgtk2.0-dev gcc make automake openssh-client openssh-server ssh \
        libssl-dev

    $ sudo pip install requests jinja2 ncclient lxml networkx py2neo networkx_viewer \
        numpy

For doc generations:

.. code-block:: bash

    $ sudo pip install sphinx

For domain emulation scripts:

.. code-block:: bash

    $ sudo pip install tornado

Other required programs (OpenYuma, click, neo4j, etc.) are also need to be installed
manually which will be installed by the `install_dep.sh` script by default.

In extreme cases, e.g. the `install_dep.sh` ran into an error, you should install
these dependencies one by one according to your OS, distro or development environment.
For that you can check the steps in the install script and/or the online documentations
referenced in entry 4. of the previous subsection.

To use the Infrastructure Layer of ESCAPEv2, Mininet must be installed on the
host (more precisely the **Open vSwitch** implementation and the specific
**mnexec** utility script is need to be installed globally).

If one version of Mininet has already been installed, there should be nothing to
do. ESCAPEv2 uses the specifically-modified Mininet files in the project folder
(*Mininet v2.1.0mod-ESCAPE*) which use the globally installed Mininet utility
scripts (mnexec).

Otherwise these assets have to be install manually which could be done from our
Mininet folder (escape/mininet) or from the official Mininet git repository
(https://github.com/mininet/mininet/ ). Mininet has an install script for the
installations (see the help with the ``-h`` flag):

.. code-block:: bash

    $ sudo mininet/util/install.sh -en

But the script occasionally **NOT** works correctly, especially on newer
distributions because the ``sudo apt-get install openvswitch-switch`` command
will not install the newest version of OVS due some major changes in OVS
architecture!

Run the following command to check the installation was correct:

.. code-block:: bash

    $ sudo mn --test pingall

However you can install the Open vSwitch packages manually:

.. code-block:: bash

    $ sudo apt-get install openvswitch-common openvswitch-switch openvswitch-testcontroller

If the command complains about the Open vSwitch not installed then you have to
install it from source. See more on http://openvswitch.org/download/ . On the
newest distributions (e.g. Ubuntu 15.04) more steps and explicit patching is
required. For that the only way is sadly to use google and search for it based
on your distro. But a good choice to start here:
https://github.com/mininet/mininet/wiki/Installing-new-version-of-Open-vSwitch

.. hint::

  If your intention is to run ESCAPEv2 in a virtual machine, you should really
  consider to use one of the pre-build Mininet VM images.

If you want to develop on your host machine, you should take care of a user for
the netconfd server. This user's name and password will be used for the
connection establishment between the ESCAPE and the Execution Environments (EE).

.. note::

  This parameters could be change in the global config under the config entry of
  *VNFStarter Adapter* conveniently.

An another solution is to define a system user for the netconfd. To create a user
(advisable to use `mininet` as in the Mininet-based VM) use the following commands:

.. code-block:: bash

    $ sudo adduser --system --shell /bin/bash --no-create-home mininet
    $ sudo addgroup mininet sudo

For security reasons it's highly recommended to limit the SSH connections for the
`mininet` user only to localhost.

.. code-block:: bash

    $ sudo echo "AllowUsers    <your_user1> <other_user...> mininet@localhost" >> /etc/ssh/sshd_config
    $ sudo service ssh reload

Check the created user with the following command:

.. code-block:: bash

    $ ssh mininet@localhost

Setup a Virtual environment (optional)
++++++++++++++++++++++++++++++++++++++

ESCAPEv2 also supports Python-based virtual environment in order to setup a
different Python version or even a different interpreter (not recommended) for
ESCAPEv2 or to separate dependent packages from system-wide Python.

To setup a virtual environment based on `virtualenv <https://virtualenv.readthedocs.org/en/latest/>`__
Python package with a standalone CPython 2.7.10 interpreter run the following script:

.. code-block:: bash

    $ ./set_virtualenv.sh

This script does the following steps:
  * Install additional dependencies
  * Download, compile and install the 2.7.10 (currently the newest) interpreter
    in a separated folder
  * Setup a virtual environment in the main project directory independently from
    the system-wide Python packages
  * Install the Python dependencies in this environment
  * and finally create a ``.use_virtualenv"`` file to enable the newly created
    virtual environment for the topmost ``escape.py`` starting script.

Usage:

.. code-block:: bash

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

The virtualenv can be enabled by the ``--environment`` flag of the topmost
``escape.py`` script.

To setup the environment manually in order to define other Python version or interpreter,
enable system-wide Python / ``pip`` packages

.. code-block:: bash

    $ virtualenv --python=<python_dir> --no-site-packages/system-site-packages <...> escape

or activate/deactivate the environment manually

.. code-block:: bash

    $ cd escape
    $ source bin/activate # activate virtual environment
    $ deactivate  # deactivate

check the content of the setup script or see the
`Virtualenv User Guide <https://virtualenv.readthedocs.org/en/latest/userguide.html>`_.

ESCAPEv2 example commands
-------------------------

**The simplest use-case:**

Run ESCAPEv2 with the Mininet-based Infrastructure layer and debug logging mode:

.. code-block:: bash

    $ ./escape.py -df

Usage:

.. code-block:: bash

    $ ./escape.py -h
      usage: escape.py [-h] [-v] [-a] [-c path] [-d] [-e] [-f] [-i] [-r] [-s file]
                       [-x] [-4]
                       ...

      ESCAPEv2: Extensible Service ChAin Prototyping Environment using Mininet,
      Click, NETCONF and POX

      optional arguments:
        -h, --help            show this help message and exit
        -v, --version         show program's version number and exit

      ESCAPEv2 arguments:
        -a, --agent           run in agent mode: start the ROS REST-API (without the
                              Service sublayer (SAS))
        -c path, --config path
                              override default config filename
        -d, --debug           run the ESCAPE in debug mode
        -e, --environment     run ESCAPEv2 in the pre-defined virtualenv
        -f, --full            run the infrastructure layer also
        -i, --interactive     run an interactive shell for observing internal states
        -r, --rosapi          start the REST-API for the Resource Orchestration
                              sublayer (ROS)
        -s file, --service file
                              skip the SAS REST-API initiation and read the service
                              request from the given file
        -x, --clean           run the cleanup task standalone and kill remained
                              programs, interfaces, veth parts and junk files
        -4, --cfor            start the REST-API for the Cf-Or interface
        ...                   optional POX modules

During a test or development the ``--debug`` flag is almost necessary.

If you want to run a test request on a test topology, use the ``--full`` flag.
ESCAPEv2 will parse the topology description form file (``escape-mn-topo.nffg``
by default) and start the Infrastructure layer with the Mininet-based emulation.

If the request is in a file it's more convenient to give it with the ``--service``
initial parameter and not bother with the REST-API.

If an error is occurred or need to observe the internal states you can start
ESCAPEv2 with an interactive Python shell using the ``--interactive`` flag.

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

    $ ./escape.py -dfi -s pox/escape-mn-req.nffg
    Starting ESCAPEv2...
    Command: sudo /home/czentye/escape/pox/pox.py unify --full --sg_file=/home/czentye/escape/pox/escape-mn-req.nffg py --completion

    ...

    ESCAPE> print core.adaptation.controller_adapter.domainResManager._dov.get_resource_info().dump()
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

**More advanced commands (mostly advisable for testing purposes):**

For more flexible control ESCAPEv2 can be started directly with POX's starting
script under the ``pox`` folder.

.. note::

  The topmost ``escape.py`` script use this ``pox.py`` script to start ESCAPEv2.
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
---------

ESCAPEv2 has currently 3 REST-APIs.

The Service layer has a REST-API for communication with users/GUI. This API is
initiated by default when the layer was started.

The Resource Orchestration layer has 2 API which are only initiated if the
appropriate flag is given to the starting script.
The ROS API can be used for communicating with other UNIFY layer e.g. a
Controller Adaptation Sublayer of a standalone ESCAPEv2 in a multi-level
scenario or with a GUI.
The CfOr API realizes the interface for service elasticity.


Common API functions
++++++++++++++++++++

*Operations:*   Every API has the following 3 function (defined in :any:`AbstractRequestHandler`):

+-------------------+----------------+-------------------+---------------------------------------------------------------------------+
|      Path         |     Params     |     HTTP verbs    | Description                                                               |
+===================+================+===================+===========================================================================+
| */version*        | ``None``       | GET               | Returns with the current version of ESCAPEv2                              |
+-------------------+----------------+-------------------+---------------------------------------------------------------------------+
| */ping*           | ``None``       | ALL               | Returns with the "OK" string                                              |
+-------------------+----------------+-------------------+---------------------------------------------------------------------------+
| */operations*     | ``None``       | GET               | Returns with the implemented operations assigned to the HTTP verbs        |
+-------------------+----------------+-------------------+---------------------------------------------------------------------------+

Service API specific function:
++++++++++++++++++++++++++++++

The SAS API is automatically initiated by the Service layer. If the ``--service`` flag
is used the service request is loaded from the given file and the REST-API
initiation is skipped.

*Content Negotiation:* The Service layer's RESTful API accepts and returns data
only in JSON format.

+-------------------+----------------+-------------------+---------------------------------------------------------------------------+
|      Path         |     Params     |     HTTP verbs    | Description                                                               |
+===================+================+===================+===========================================================================+
| */topology*       | ``None``       | GET               | Returns with the resource view of the Service layer                       |
+-------------------+----------------+-------------------+---------------------------------------------------------------------------+
| */sg*             | ``NFFG``       | ALL               | Initiate given NFFG. Returns the given NFFG initiation is accepted or not |
+-------------------+----------------+-------------------+---------------------------------------------------------------------------+

ROS API specific function:
++++++++++++++++++++++++++

Can be started with the ``--agent`` or ``--rosapi`` initial flags.

+-------------------+----------------+-------------------+---------------------------------------------------------------------------+
|      Path         |     Params     |     HTTP verbs    | Description                                                               |
+===================+================+===================+===========================================================================+
| */get-config*     | ``None``       | GET               | Returns with the resource view of the Resource Orchestration Sublayer     |
+-------------------+----------------+-------------------+---------------------------------------------------------------------------+
| */edit-config*    | ``NFFG``       | ALL               | Initiate given NFFG.                                                      |
+-------------------+----------------+-------------------+---------------------------------------------------------------------------+

Cf-Or API specific function:
++++++++++++++++++++++++++++

Can be started with the ``--cfor`` flag.

+-------------------+----------------+-------------------+---------------------------------------------------------------------------+
|      Path         |     Params     |     HTTP verbs    | Description                                                               |
+===================+================+===================+===========================================================================+
| */get-config*     | ``None``       | GET               | Returns with the resource view from the assigned Virtualizer              |
+-------------------+----------------+-------------------+---------------------------------------------------------------------------+
| */edit-config*    | ``NFFG``       | ALL               | Initiate given NFFG.                                                      |
+-------------------+----------------+-------------------+---------------------------------------------------------------------------+

Configuration
-------------

ESCAPEv2 has a default configuration under the `escape` package (in the
`__init__.py` file as ``cfg``). This configuration contains the necessary
information for manager/adapter initialization, remote connections, etc. and
also used as the running config.

To override some of the parameters you can change it in the `cfg` directly (not
preferred) or you can define it in the additional config file: ``escape.config``.
The ESCAPEv2 checks this file at every start, and update/override the internal
config if it's necessary.

The config file path can be changed during start with the ``--config`` initial
parameter.

The additional config can be added only in JSON format, but the structure of the
configuration is strictly follows the default configuration.

The configuration values is derived from the initial attributes of the
adapter/managers constructors. Other values are single data, paths or flags which
are taken out by helper functions of the :any:`ESCAPEConfig` class.

Development
-----------

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
---------

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

Contacts
--------

János Czentye - janos.czentye@tmit.bme.hu

Balázs Sonkoly - balazs.sonkoly@tmit.bme.hu

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

