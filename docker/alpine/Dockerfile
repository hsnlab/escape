################################################################################
# Dockerfile to build minimal ESCAPE MdO Container on Alpine Linux
#   - Numpy package is installed from Alpine's apk repository
#   - cryptography and ncclient is installed with pip where backend code is
#     compiled on-the-fly with explicitly installed gcc
################################################################################
FROM python:2.7.13-alpine
MAINTAINER Janos Czentye <czentye@tmit.bme.hu>
LABEL Description="ESCAPE" Project="5GEx" version="2.0.0+"
WORKDIR /opt/escape
COPY . ./
RUN apk add --update --no-cache \
    --repository http://dl-3.alpinelinux.org/alpine/edge/community/ \
    openssl-dev libffi-dev musl-dev libxml2-dev libxslt-dev openssh gcc py-numpy
RUN pip install --upgrade -r docker/alpine/requirements-alpine.txt
EXPOSE 8008 8888
ENV PYTHONUNBUFFERED 1
ENTRYPOINT ["python", "escape.py"]
CMD ["--debug", "--rosapi", "--config", "config/escape-static-dummy.config"]