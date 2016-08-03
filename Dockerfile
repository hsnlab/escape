FROM ubuntu:14.04.4
MAINTAINER Janos Czentye <czentye@tmit.bme.hu>
COPY . /home/escape/
COPY .ssh/ /root/.ssh/
WORKDIR /home/escape
RUN apt-get update && apt-get install -y git wget
# Set locale to avoid annoying warnings
RUN locale-gen en_US.UTF-8 && export LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
# Install MdO dependencies
RUN ./install-dep.sh -c
# Service Layer REST-API
EXPOSE 8008
# Resource Orchestration Layer REST-API
EXPOSE 8888
# Cf-Or REST-API
EXPOSE 8889
ENTRYPOINT ["/bin/bash"]
#RUN ["./escape.py", "-d"]