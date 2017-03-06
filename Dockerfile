################################################################################
# Dockerfile to build minimal ESCAPE MdO Container
################################################################################

FROM python:2.7.13
MAINTAINER Janos Czentye <czentye@tmit.bme.hu>
LABEL Description="ESCAPE: Multi-domain Orchestrator" Project="5GEx" version="2.0.0+"
COPY . /home/escape/
WORKDIR /home/escape
RUN pip install --upgrade -r requirements.txt
EXPOSE 8008 8888
ENTRYPOINT ["./escape.py"]
CMD ["-drc", "config/escape-static-dummy.config"]