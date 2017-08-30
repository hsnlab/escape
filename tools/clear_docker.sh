#!/usr/bin/env bash
# Exited containers
EXITED=$(docker ps --no-trunc -aqf status=exited)
# Clear containers
if [ -n "$EXITED" ]; then sudo docker rm ${EXITED}; fi
# Clear images
DANGLING=$(docker images -q -f "dangling=true")
if [ -n "$DANGLING" ]; then sudo docker rmi ${DANGLING}; fi
sudo docker images