# ESCAPEv2: Extensible Service ChAin Prototyping Environment using Mininet, Click, NETCONF and POX

## Introduction
On the one hand, ESCAPE (Extensible Service ChAin Prototyping Environment) is a
general prototyping framework which supports the development of several parts of
the service chaining architecture including VNF implementation, traffic steering,
virtual network embedding, etc.  On the other hand, ESCAPE is a proof of concept
prototype implementing a novel SFC (Service Function Chaining) architecture
proposed by EU FP7 UNIFY project: https://www.fp7-unify.eu/.
It is a realization of the UNIFY service programming and orchestration framework
which enables the joint programming and virtualization of cloud and networking
resources.

## Installation
Dependencies:
```bash
sudo apt -y install python2.7 python-dev python-pip zlib1g-dev libxml2-dev libxslt1-dev \
    libssl-dev libffi-dev python-crypto openjdk-7-jdk neo4j=2.2.7 gcc make socat psmisc xterm \
    ssh iperf iproute telnet python-setuptools cgroup-bin ethtool help2man pyflakes pylint pep8 \
    openvswitch-switch automake ssh libssh2-1-dev libgcrypt11-dev libncurses5-dev libglib2.0-dev \
    libgtk2.0-dev graphviz texlive-latex-extra

sudo pip -H install numpy jinja2 py2neo networkx requests ncclient cryptography==1.3.1 tornado \
    sphinx networkx_viewer
```
Because the core ESCAPEv2 relies on POX and written in Python there is no need
for explicit compiling or installation. The only requirement need to be
pre-installed is a Python interpreter.

The recommended Python version, in which the development and mostly the testing
are performed, is the standard CPython **2.7.11**.

The best choice of platform on wich ESCAPEv2 is recommended to install and the
*install-dep.sh* is tested is **Ubuntu 14.04.4 LTS**.

However ESCAPEv2 is developed on Kubuntu 16.04, some issues are experienced
related to SAP-xterm initiation in case the platform was an Ubuntu 16.04 server
image and ESCAPEv2 was started through an SSH channel.
Considering this limitation we recommend to use the older 14.04 LTS version in
case ESCAPEv2 is intended to run on a VM without any graphical interface.

The preferred way:

1. Download one of pre-build Ubuntu LTS image or create one in your VM manager.

2. Create the *.ssh* folder in the home directory and copy your private RSA key
    which you gave on the *fp7-unify.eu GitLab* site into the VM with the name
    `id_rsa`. If you use a VM image then the following commands can be used
    in the VM to copy your RSA key from your host:
    ```bash
    cd
    mkdir .ssh
    scp <your_user>@<host_ip>:~/.ssh/<your_ssh_key> ~/.ssh/id_rsa
    ```
3. Clone the shared escape repository in a folder named: *escape*.
    ```bash
    git clone git@5gexgit.tmit.bme.hu:unify/escape.git escape
    ```

4. Install the necessary dependencies with the *install_dep.sh* script (system
    and Python packages, OpenYuma with VNFStarter module):

    ```bash
    cd escape
    escape$ ./install_dep.sh
    ```
    In a high level the script above does the following things:
    
    * Install the necessary system and Python packages
    * Compile and install the `OpenYuma` tools with our `VNF_starter` module
    * Compile and install `Click` modular router and `The Click GUI`.
    * Install `neo4j` graph database for NFIB
      
    See help menu for further parameters:
    ```bash
    ./install-dep.sh -h
    Usage: ./install-dep.sh [-a] [-c] [-d] [-g] [-h] [-i]
    Install script for ESCAPEv2

    options:
        -a:   (default) install (A)ll ESCAPEv2 components (identical with -cgi)
        -c:   install (C)ore dependencies for Global Orchestration
        -d:   install additional dependencies for (D)evelopment and test tools
        -g:   install dependencies for our rudimentary (G)UI
        -h:   print this (H)elp message
        -i:   install components of (I)nfrastructure Layer for Local Orchestration
    ```

5. Run ESCAPEv2 with one of the commands listed in a later section. To see the
    available arguments of the top stating script check the help menu:
    ```bash
    ./escape.py --help
    ```
    To verify ESCAPEv2's components are installed and set up correctly you can run
    the following command and test the reachability of the initiated SAPs (``xterm``)
    with `ping`:
    ```bash
    ./escape.py -df -s examples/escape-mn-req.nffg
    # on SAP1 xterm
    $ ping sap2
    # on SAP2 xterm
    $ ping sap1
    ```

To setup virtualizer library as a subtree module manually, use the following commands from
the project's root directory:
```bash
git submodule update --init --recursive --merge
```

For more information see: https://sb.tmit.bme.hu/escape/