:orphan:

The hard way
------------

If you want to use ESCAPE as a Multi-domain Orchestrator without Mininet-based
Infrastructure Layer, you should use the easy way: :ref:`install_steps`

Obviously ESCAPE can be installed on a host machine or on a different platform too.
If the install script fails on a newer OS for some reason, the installation steps need to be carried out manually.

**Submodules**

The project uses several dependent component as a Git submodule. To acquire these
source codes a symlink have to be created in the project's root folder at first,
referring to the gitmodules config of the actual project.

Moreover, the required submodules need to be configured with the related project's gitmodules file recursively.
For this task the ``project-setup.sh`` wrapper script can be used with the referred project's name:

.. code-block:: text

    $ ./project-setup.sh -h
    Setup submodules according to given project for ESCAPE.
    If project name is not given the script tries to detect it
    from the git's local configurations.

    Usage: ./project-setup.sh [-h] [-p project]
    Parameters:
         -h, --help      show this help message and exit
         -p, --project   setup project name based on: .gitmodules.<name>

    Example: ./project-setup.sh -p 5gex

The submodule configuration can be set up and updated manually as well:

.. code-block:: bash

    $ ln -s .gitmodules.<project_name> .gitmodules
    $ git submodule update --init --remote --recursive --merge

**Dependencies**

If ESCAPE's Python dependencies are not wanted to be installed globally, follow the
hard way and setup a virtual environment step-by-step.

.. note::

    neo4j requires Java 7 which can't be found in the official Ubuntu 14.04 repositories.
    To install the Java package and the latest Python 2.7 on Ubuntu 14.04, the following
    PPA repositories can be used:

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

If ESCAPE is intended to be used on a host machine, it is recommended to create
a separate user for the netconfd server. This user's name and password will be
used for the connection establishment between ESCAPE and the Execution Environments (EE).

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