#!/usr/bin/env bash

# Fail on error
trap on_error ERR

function on_error() {
    echo "Error during installation!"
    exit 1
}

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Installing ESCAPEv2 dependencies..."
sudo apt-get update

# Install dependencies
sudo apt-get -y install libxml2-dev libxslt1-dev zlib1g-dev \
python-pip python-libxml2 python-libxslt1 python-lxml python-paramiko python-dev python-networkx \
libxml2-dev libssh2-1-dev libgcrypt11-dev libncurses5-dev libglib2.0-dev libgtk2.0-dev \
gcc make automake openssh-client openssh-server ssh

echo "Install Python-specific dependencies..."
sudo pip install requests jinja2 ncclient lxml networkx py2neo networkx_viewer numpy

echo "Install OpenYuma for NETCONF capability..."
cd "$DIR/OpenYuma"
# -i flag -> got error during first run of make but it seems OK, so ignore...
make -i
sudo make install

if grep -Fxq "# --- ESCAPEv2 ---" "/etc/ssh/sshd_config"
then
    echo "Remove previous ESCAPEv2-related sshd config..."
    sudo sed -in '/.*ESCAPEv2.*/,/.*ESCAPEv2 END.*/d' "/etc/ssh/sshd_config"
fi
echo "Set sshd configuration..."
cat <<EOF | sudo tee -a /etc/ssh/sshd_config
# --- ESCAPEv2 ---
Port 830
Port 831
Port 832
Port 833
Port 834
Port 835
Port 836
Port 837
Port 838
Port 839
Subsystem netconf /usr/sbin/netconf-subsystem
# --- ESCAPEv2 END ---
EOF

echo "Restart sshd..."
#sudo /etc/init.d/ssh restart
sudo service ssh restart

echo "Installing VNF starter module for netconfd..."
cd "$DIR/Unify_ncagent/vnf_starter"
mkdir -p bin
mkdir -p lib
sudo cp vnf_starter.yang /usr/share/yuma/modules/netconfcentral/
make
sudo make install

echo "Install Click, clicky and netconfhelper.py for Infrastructure layer..."
cd "$DIR"
git clone --depth 1 https://github.com/kohler/click.git
cd click
./configure --disable-linuxmodule
CPU=$(grep -c '^processor' /proc/cpuinfo)
make -j$CPU
sudo make install

cd apps/clicky
autoreconf -i
./configure
make -j$CPU
sudo make install
cd "$DIR"
rm -rf click

# install clickhelper.py to be availble from netconfd
sudo ln -s "$DIR/mininet/mininet/clickhelper.py" /usr/local/bin/clickhelper.py

echo "Install neo4j graph database..."
sudo sh -c "wget -O - http://debian.neo4j.org/neotechnology.gpg.key | apt-key add -"
sudo sh -c "echo 'deb http://debian.neo4j.org/repo stable/' > /etc/apt/sources.list.d/neo4j.list"
sudo apt-get update
sudo apt-get -y install neo4j
# disable authentication in /etc/neo4j/neo4j-server.properties
sudo sed -i s/dbms\.security\.auth_enabled=true/dbms\.security\.auth_enabled=false/ \
    /etc/neo4j/neo4j-server.properties
sudo service neo4j-service restart

echo "Done."
