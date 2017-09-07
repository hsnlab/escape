:orphan:

Issues with Local Orchestrator setup
------------------------------------

However ESCAPE has been developed on Ubuntu 16.04, some issues are experienced
related to SAP-xterm initiation in case ESCAPE was run on an Ubuntu 16.04 virtual
machine through an SSH channel with X11 forwarding.

.. important::

    Considering this limitation we recommend to use the older 14.04.5 LTS version
    in case ESCAPE is intended to run:

      * on a VM
      * without any graphical interface
      * as a local Domain Orchestrator.

Nevertheless the install script (``install-dep.sh``) supports both Ubuntu LTS version.

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