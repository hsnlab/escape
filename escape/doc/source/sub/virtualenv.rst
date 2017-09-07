:orphan:

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

:orphan:
