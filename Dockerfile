################################################################################
# Dockerfile to build minimal ESCAPE MdO Container
################################################################################
FROM python:2.7.14-alpine
MAINTAINER Janos Czentye <czentye@tmit.bme.hu>
ARG GIT_REVISION=unknown
LABEL git-revision=$GIT_REVISION    
LABEL Description="ESCAPE" Project="5GEx" version="2.0.0+"
WORKDIR /opt/escape
ENV PYTHONUNBUFFERED=1 LANG=C.UTF-8
COPY . ./
# Install py-numpy from APK repo to avoid using gcc to compile C extension code
RUN apk add --repository http://dl-3.alpinelinux.org/alpine/edge/community/ \
            --no-cache py-numpy bash git openssh
RUN pip install --no-cache-dir -U $(grep -v -e \# -e numpy requirements.txt)
# Setup git and pull the latest updates
RUN cp -r docker/demo ~/.ssh && \
    ln -vfs .gitmodules.5gex .gitmodules && \
    git remote set-url origin git@5gexgit.tmit.bme.hu:unify/escape.git && \
    chmod 600 ~/.ssh/*
EXPOSE 8888 9000
STOPSIGNAL SIGINT
ENTRYPOINT ["./docker_startup.sh"]
CMD ["--debug", "--rosapi", "--config", "config/escape-static-dummy.yaml"]