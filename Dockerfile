################################################################################
# Dockerfile to build minimal ESCAPE MdO Container
################################################################################
FROM python:2.7.14-alpine
MAINTAINER Janos Czentye <czentye@tmit.bme.hu>
ARG GIT_REVISION=unknown
LABEL git-revision=$GIT_REVISION    
LABEL Description="ESCAPE" Project="5GEx" version="2.0.0+"
WORKDIR /opt/escape
COPY . ./
# Install py-numpy from APK repo to avoid using gcc to compile C extension code
RUN apk add --repository http://dl-3.alpinelinux.org/alpine/edge/community/ \
            --no-cache py-numpy
RUN pip install --no-cache-dir -U $(grep -v -e \# -e numpy requirements.txt)
EXPOSE 8008 8888 9000
ENV PYTHONUNBUFFERED 1
ENTRYPOINT ["python", "escape.py"]
CMD ["--debug", "--rosapi", "--config", "config/escape-static-dummy.config"]