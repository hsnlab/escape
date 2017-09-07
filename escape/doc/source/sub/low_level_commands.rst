:orphan:

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