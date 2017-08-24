#!/usr/bin/env bash

# Clear containers
sudo docker rm $(docker ps --no-trunc -aqf status=exited)
# Clear images
sudo docker rmi $(docker images -q -f "dangling=true")
sudo docker images