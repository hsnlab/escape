#!/usr/bin/env bash

echo "Installing ESCAPEv2 dependencies..."
sudo apt-get update

# Install dependencies
sudo apt-get -y install libxml2-dev libxslt1-dev zlib1g-dev \
python-pip python-libxml2 python-libxslt1 python-lxml python-paramiko \
libxml2-dev libssh2-1-dev libgcrypt11-dev libncurses5-dev make gcc automake \
openssh-client openssh-server ssh

echo "Install Python-specific dependencies..."
sudo pip install requests jinja2 ncclient lxml networkx

echo "Install OpenYuma for NETCONF capability..."
cd OpenYuma
make 
sudo make install

echo "Set sshd configuration..."
cat <<EOF | sudo tee -a /etc/ssh/sshd_config
# ----- ESCAPEv2 -----
Port 830
Port 831
Port 832
Subsystem netconf /usr/sbin/netconf-subsystem
# -----END ESCAPEv2 -----
EOF

echo "Restart sshd..."
sudo /etc/init.d/ssh restart

echo "Installing VNF starter module for netconfd..."
cd Unify_ncagent/vnf_starter
mkdir -p bin
mkdir -p lib
sudo cp vnf_starter.yang /usr/share/yuma/modules/netconfcentral/
make
sudo make install

echo "Done."