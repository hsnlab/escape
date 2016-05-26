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
## Installation
The preferred way:
1. Download one of pre-build Mininet image which has already had the necessary tools (Mininet scripts and Open vSwitch).
     * https://github.com/mininet/mininet/wiki/Mininet-VM-Images

    The images is in an open virtual format (.ovf) which can import most of the
    virtualization manager. Username/password: mininet/mininet

    Our implementation relies on Mininet 2.1.0, but ESCAPEv2 has been tested on
    the newest image too (Mininet 2.2.1 on Ubuntu 14.04 - 64 bit) and no problem
    has occurred yet!

2. Create the *.ssh* folder in the home directory and copy your private RSA key
    which you gave on the *fp7-unify.eu GitLab* site into the VM with the name
    id_rsa. If you use the Mininet image then the following command can be used
    in the VM to copy your RSA key from your host:
    ```bash
    cd
    mkdir .ssh
    scp <your_user>@<host_ip>:~/.ssh/<your_ssh_key> ~/.ssh/id_rsa
    ```
3. Clone the shared escape repository in a folder named: escape.
    ```bash
    git clone git@gitlab.fp7-unify.eu:Balazs.Sonkoly/escape-shared.git escape
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

5. Run ESCAPEv2 with one of the commands listed in a later section. To see the
    available arguments of the top stating script check the help menu:
    ```bash
    ./escape.py --help
    ```

For more information see: https://sb.tmit.bme.hu/escape/

To setup virtualizer library as a subtree module, use the following commands from
the project's root directory:
```bash
git submodule update --init --recursive --merge
```