FROM ubuntu:14.04.5
MAINTAINER Janos Czentye <czentye@tmit.bme.hu>
LABEL Description="ESCAPE: Multi-domain Orchestrator" Project="UNIFY" version="2.0"
# Default install parameter
ARG ESC_INSTALL_PARAMS=c
# Copy escape files (without submodules and binaries defined in .dockerignore)
COPY . /home/escape/
COPY docker/.ssh/ /root/.ssh/
# Default dir
WORKDIR /home/escape
# Install required packages, set locale , install ESCAPE's dependencies and cleanup
RUN apt-get update && apt-get install -y git wget && \
    # Set locale to avoid annoying warnings
    locale-gen en_US.UTF-8 && \
    export LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 && \
    ./install-dep.sh -${ESC_INSTALL_PARAMS} && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
# REST-APIs:  Service Layer  |  Resource Orchestration Layer  |  Cf-Or
EXPOSE 8008 8888 8889
# Set starting script which start required services and init a shell
ENTRYPOINT ["docker/startup.sh"]
## Start ESCAPE by default
#ENTRYPOINT ["./escape.py"]
## Default parameter is debug logging
#CMD ["-d", "-c", "docker/default-docker.config"]