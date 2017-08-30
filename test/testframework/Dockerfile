################################################################################
# Dockerfile to build minimal ESCAPE MdO Container for testing
################################################################################
FROM python:2.7.13-alpine
MAINTAINER Janos Czentye <czentye@tmit.bme.hu>
LABEL Description="ESCAPE test image" Project="5GEx" version="2.0.0+"
COPY . /opt/escape
WORKDIR /opt/escape/test
# Install py-numpy from APK repo to avoid using gcc to compile C extension code
RUN apk add --update --no-cache \
    --repository http://dl-3.alpinelinux.org/alpine/edge/community/ py-numpy
RUN pip install --no-cache-dir --upgrade \
    $(grep -v -e \# -e numpy ../requirements.txt) pexpect unittest-xml-reporting
ENV PYTHONUNBUFFERED 1
ENTRYPOINT ["python", "run_tests.py" ]