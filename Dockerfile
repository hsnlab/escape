################################################################################
# Dockerfile to build minimal ESCAPE MdO Container
################################################################################
FROM python:2.7.13
MAINTAINER Janos Czentye <czentye@tmit.bme.hu>
LABEL Description="ESCAPE" Project="5GEx" version="2.0.0+"
WORKDIR /opt/escape
COPY . ./
RUN pip install --upgrade -r requirements.txt
EXPOSE 8008 8888
ENTRYPOINT ["python", "escape.py"]
CMD ["--debug", "--rosapi", "--config", "config/escape-static-dummy.config"]