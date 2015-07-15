#!/usr/bin/env bash

echo "Installing ESCAPEv2 dependencies..."
sudo apt-get update
# Install dependencies
sudo apt-get -y install libxml2-dev libxslt1-dev zlib1g-dev \
python-pip python-libxml2 python-libxslt1 python-lxml python-paramiko
sudo pip install requests jinja2 ncclient lxml
