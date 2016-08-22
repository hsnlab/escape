#!/usr/bin/env bash

# Clear containers
docker rm $(docker ps --no-trunc -aq)
# Clear imaged
docker rmi $(docker images -q -f "dangling=true")
docker rmi escape/mdo