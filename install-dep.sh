#!/usr/bin/env bash
# Copyright 2017 Janos Czentye
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Install Python and system-wide packages, required programs and configurations
# for ESCAPEv2 on pre-installed Mininet VM
# Tested on: Ubuntu 14.04.4 LTS and 16.04 LTS

### Initial setup

# Constants for colorful logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

set -euo pipefail

# Fail on error
trap "on_error 'Got signal: SIGHUP'" SIGHUP
trap "on_error 'Got signal: SIGINT'" SIGINT
trap "on_error 'Got signal: SIGTERM'" SIGTERM
trap on_error ERR

function on_error() {
    echo -e "\n${RED}Error during installation! ${1-}${NC}"
    exit 1
}

function info() {
    echo -e "${GREEN}${1-INFO}${NC}"
}

function warn() {
    echo -e "\n${YELLOW}WARNING: ${1-WARNING}${NC}"
}

function env_setup {
    # Set environment
    set +u
    # If LC_ALL is not set up
    if [[ ! "$LC_ALL" ]]; then
        if [[ "$LANG" ]]; then
            # Set LC_ALL as LANG
            info "=== Set environment ==="
            sudo locale-gen $LANG
            export LC_ALL=$LANG
            locale
        fi
    fi
    set -u
}

### Constants
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

BINDIR=/usr/bin
MNEXEC=mnexec
MNUSER=mininet
MNPASSWD=mininet

# Distributor constants
if [ -f /etc/lsb-release ]; then
    source /etc/lsb-release # DISTRIB_ID, DISTRIB_RELEASE
    info "Detected platform is $DISTRIB_ID, version: $DISTRIB_RELEASE!"
    if [ "$DISTRIB_RELEASE" = "14.04" ]; then
        warn "Platform: Ubuntu $DISTRIB_RELEASE is no longer supported!"
        read -p "Press any key to continue..."
    fi
else
    warn "Detected platform is NOT Ubuntu! This may lead to skip some installation steps!"
fi

### Menu point functions

function install_core {
    env_setup
    info "================================="
    info "==  Install core dependencies  =="
    info "================================="
    echo "ESCAPEv2 version: $(./escape.py -v 2>&1)"

    info "=== Setup project ==="
    # Git return error during submodule change -> disable error catching
    set +ue
    if [ -f "project-setup.sh" ]; then
        if [ -z "$PROJECT" ]; then
            . ./project-setup.sh
        else
            . ./project-setup.sh -p "$PROJECT"
        fi
    else
        on_error "Project setup script is missing!"
    fi
    set -ue

    sudo apt-get install -y software-properties-common

    if [ "$DISTRIB_ID" = "Ubuntu" ]; then
        if [ "$DISTRIB_RELEASE" = "14.04" ]; then
            info "=== Add 3rd party PPA repo for most recent Python2.7 ==="
            sudo add-apt-repository -y ppa:fkrull/deadsnakes-python2.7
        elif [ "$DISTRIB_RELEASE" = "16.04" ]; then
            info "=== Add 3rd party PPA repo for most recent Python2.7 ==="
            sudo add-apt-repository -y ppa:jonathonf/python-2.7
        else
            warn "Unsupported Ubuntu version: $DISTRIB_RELEASE"
        fi
    fi

    info "=== Install ESCAPEv2 core dependencies ==="
    sudo apt-get update
    # Install Python 2.7.13 explicitly
    sudo apt-get install -y python2.7 python-dev python-pip

    info "=== Install ESCAPEv2 Python dependencies ==="
    sudo -H pip install --upgrade -r requirements.txt
}

function install_nfib_dep {
    env_setup
    info "=== Install Neo4j and bindings for NFIB component ==="
    # Component versions
    local JAVA_VERSION=7
    local NEO4J_VERSION=2.2.7

    if [[ ! $(sudo apt-cache search openjdk-${JAVA_VERSION}-jdk) ]]; then
        info "=== Add OpenJDK repository and install Java $JAVA_VERSION ==="
        sudo add-apt-repository -y ppa:openjdk-r/ppa
    fi

    info "=== Add neo4j repository ==="
    sudo sh -c "wget -O - http://debian.neo4j.org/neotechnology.gpg.key | apt-key add -"
    sudo sh -c "echo 'deb http://debian.neo4j.org/repo stable/' | tee /etc/apt/sources.list.d/neo4j.list"

    sudo apt-get update
    # Install Java 8 explicitly
    sudo apt-get install -y openjdk-${JAVA_VERSION}-jdk neo4j=${NEO4J_VERSION}

    info "=== Configure neo4j graph database ==="
    # Disable authentication in /etc/neo4j/neo4j.conf <-- neo4j >= 3.0
    if [ -f /etc/neo4j/neo4j.conf ]; then
        # neo4j >= 3.0
        sudo sed -i /dbms\.security\.auth_enabled=false/s/^#//g /etc/neo4j/neo4j.conf
        sudo service neo4j restart
    elif [ -f /etc/neo4j/neo4j-server.properties ]; then
        # neo4j <= 2.3.4
        sudo sed -i s/dbms\.security\.auth_enabled=true/dbms\.security\.auth_enabled=false/ /etc/neo4j/neo4j-server.properties
        sudo service neo4j-service restart
    else
        on_error "=== neo4j server configuration file was not found! ==="
    fi
    # Freeze neo4j version
    echo "Mark current version of neo4j: $NEO4J_VERSION as held back..."
    sudo apt-mark hold neo4j

    # Install dependencies for Python libs
    sudo apt-get install -y python-crypto zlib1g-dev libxml2-dev libxslt1-dev \
                            libssl-dev libffi-dev

    # Install Python dependencies
    sudo -H pip install --no-cache-dir Jinja2 py2neo ncclient cryptography==1.3.1
}

function install_mn_dep {
    env_setup
    info "=== Install Mininet dependencies ==="
    # Copied from /mininet/util/install.sh
    sudo apt-get install -y gcc make socat psmisc xterm ssh iperf iproute telnet \
    python-setuptools cgroup-bin ethtool net-tools xorg help2man pyflakes pylint pep8
    info "=== Install Open vSwitch ==="
    sudo apt-get install -y openvswitch-switch
    info "=== Compile and install 'mnexec' execution utility  ==="
    cd "$DIR/mininet"
    make mnexec
    sudo install -v ${MNEXEC} ${BINDIR}
    if id -u ${MNUSER} >/dev/null 2>&1; then
        info "=== User: $MNUSER already exist. Skip user addition... ==="
    else
        info "=== Create user: mininet passwd: mininet for communication over NETCONF ==="
        sudo adduser --system --shell /bin/bash --no-create-home ${MNUSER}
        sudo addgroup ${MNUSER} sudo
        echo "$MNUSER:$MNPASSWD" | sudo chpasswd
    fi
    if [ "$DISTRIB_RELEASE" = "14.04" ]; then
        if grep -Fxq "# --- ESCAPE-mininet ---" "/etc/ssh/sshd_config"; then
            info "=== Remove previous ESCAPEv2-related mininet config ==="
            sudo sed -in '/.*ESCAPE-mininet.*/,/.*ESCAPE-mininet END.*/d' "/etc/ssh/sshd_config"
        fi
        info "=== Restrict user: mininet to be able to establish SSH connection only from: localhost ==="
        # Only works with OpenSSH_6.6.1p1 and tested on Ubuntu 14.04
        cat <<EOF | sudo tee -a /etc/ssh/sshd_config
# --- ESCAPE-mininet ---
# Restrict mininet user to be able to login only from localhost
Match Host *,!localhost
  DenyUsers  mininet
# --- ESCAPE-mininet END---
EOF
    # Restrict mininet user to be able to login only from localhost
    elif [ "$DISTRIB_RELEASE" = "16.04" ]; then
        info "=== Restrict user: mininet to be able to establish SSH connection only from: localhost ==="
        cat <<EOF | sudo tee -a /etc/ssh/sshd_config
# --- ESCAPE-mininet ---
# Restrict mininet user to be able to login only from localhost
Match User mininet
	AllowUsers mininet@127.0.0.1
# --- ESCAPE-mininet END---
EOF
    else
        warn "\nIf this installation was not performed on an Ubuntu 14.04 VM, limit the SSH connections only to localhost due to security issues!\n"
    fi
}

function install_infra {
    env_setup
    info "==================================================================="
    info "==  Install dependencies for Mininet-based Infrastructure Layer  =="
    info "==================================================================="
    sudo apt-get install -y gcc make automake ssh libxml2-dev libssh2-1-dev libgcrypt11-dev libncurses5-dev libglib2.0-dev libgtk2.0-dev

    info "=== Install OpenYuma for NETCONF capability ==="
    cd "$DIR/OpenYuma"
    #make clean
    make -i
    sudo make install

    if grep -Fxq "# --- ESCAPE-sshd ---" "/etc/ssh/sshd_config"; then
        info "=== Remove previous ESCAPEv2-related sshd config ==="
        sudo sed -in '/.*ESCAPE-sshd.*/,/.*ESCAPE-sshd END.*/d' "/etc/ssh/sshd_config"
    fi

    info "=== Set sshd configuration ==="
    cat <<EOF | sudo tee -a /etc/ssh/sshd_config
# --- ESCAPE-sshd ---
# Only 8 Port can be used as a listening port for SSH daemon.
# The default Port 22 has already reserved one port.
# To overcome this limitation the openssh-server needs to be
# modified and recompiled from source.
Port 830
Port 831
Port 832
Port 833
Port 834
Port 835
Port 836
Subsystem netconf /usr/sbin/netconf-subsystem
# --- ESCAPEv2-sshd END ---
EOF

    info "=== Restart sshd ==="
    sudo service ssh restart

    # sudo apt-get install libglib2.0-dev
    info "=== Installing VNF starter module for netconfd ==="
    cd "$DIR/Unify_ncagent/vnf_starter"
    mkdir -p bin
    mkdir -p lib
    sudo cp vnf_starter.yang /usr/share/yuma/modules/netconfcentral/

    # Docker workaround
    if [ ! -f /usr/include/glib-2.0/glib/glib-autocleanups.h ]; then
        sudo wget -vP /usr/include/glib-2.0/glib/ https://github.com/GNOME/glib/blob/master/glib/glib-autocleanups.h
    fi

    make clean
    make
    sudo make install

    info "=== Install click for VNFs ==="
    cd ${DIR}
    if [ ! -d click ]; then
        git clone --depth 1 https://github.com/kohler/click.git
    fi
    cd click
    ./configure --disable-linuxmodule
    CPU=$(grep -c '^processor' /proc/cpuinfo)
    make clean
    make -j${CPU}
    sudo make install

    # sudo apt-get install libgtk2.0-dev
    info "=== Install clicky for graphical VNF management ==="
    cd apps/clicky
    autoreconf -i
    ./configure
    make clean
    make -j${CPU}
    sudo make install

    # Remove click codes
     cd ${DIR}
     rm -rf click

    info "=== Install clickhelper.py ==="
    # install clickhelper.py to be available from netconfd
    sudo ln -vfs "$DIR/mininet/mininet/clickhelper.py" /usr/local/bin/clickhelper.py

    if [ ! -f /usr/bin/mnexec ]; then
        info "=== Pre-installed Mininet not detected! Try to install mn dependencies... ==="
        install_mn_dep
    fi

    install_nfib_dep
}

# Install development dependencies as tornado for scripts in ./tools,
# for doc generations, etc.
function install_dev {
    env_setup
    info "=========================================================="
    info "==  Installing additional dependencies for development  =="
    info "=========================================================="
    sudo apt-get install -y graphviz texlive-latex-extra latexmk
    sudo -H pip install sphinx
    # Install test requirements
    . ${DIR}/test/install_requirements.sh
}

# Install GUI dependencies
function install_gui {
    env_setup
    info "==========================================================="
    info "==  Installing additional dependencies for internal GUI  =="
    info "==========================================================="
    sudo apt-get install -y python-tk
    sudo -H pip install networkx_viewer
}

# Install all main component
function all {
    env_setup
    install_core
    install_gui
    install_infra
}

# Print help
function print_usage {
    echo -e "Usage: $0 [-c] [-d] [-g] [-h] [-i] [-p project]"
    echo -e "Install script for ESCAPEv2\n"
    echo -e "options:"
    echo -e "\t-c:   (default) install (C)ore dependencies for Global Orchestration"
    echo -e "\t-d:   install additional dependencies for (D)evelopment and test tools"
    echo -e "\t-g:   install dependencies for our rudimentary (G)UI (deprecated)"
    echo -e "\t-h:   print this (H)elp message"
    echo -e "\t-i:   install components of (I)nfrastructure Layer\n\t\tfor Local Orchestration (deprecated)"
    echo -e "\t-p:   explicitly setup project name based on: .gitmodules.<name>\n\t\tinstead of automatic detection"
    exit 2
}

if [ $# -eq 0 ]; then
    # No param was given, call all with default project
    install_core
else
    # Parse optional project parameter
    while getopts ':p:' OPTION; do
        case ${OPTION} in
            p)  PROJECT=$OPTARG;;
        esac
    done
    OPTIND=1    # Reset getopts
    info "User project config: ${PROJECT:-N/A}"
    while getopts 'cdghip:' OPTION; do
        case ${OPTION} in
            c)  install_core;;
            d)  install_dev;;
            g)  install_gui;;
            h)  print_usage;;
            i)  install_infra;;
            # If only -p was set, call install_core else skip
            p)  if [ $# -eq 2 ]; then install_core; fi;;
            \?)  print_usage;;
        esac
    done
    #shift $(($OPTIND - 1))
fi

info "============"
info "==  Done  =="
info "============"
# Force to return with 0 for docker build
exit 0
