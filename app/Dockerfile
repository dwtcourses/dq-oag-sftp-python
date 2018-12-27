FROM python:2.7

ENV USERMAP_UID 1000

WORKDIR /ADT/scripts

COPY packages.txt ./
COPY test.py ./

RUN apt-get install git wget
RUN wget http://ftp.gnu.org/gnu/gdbm/gdbm-1.8.3.tar.gz && \
   tar -xvzf gdbm-1.8.3.tar.gz && \
   cd gdbm-1.8.3 && \
   ./configure --prefix=/usr && \
   make && \
   make BINOWN=root BINGRP=root install
RUN pip install --no-cache-dir -r packages.txt
RUN groupadd -r scriptrunner && \
useradd --no-log-init -u $USERMAP_UID -r -g scriptrunner runner && \
chown runner:scriptrunner /ADT/scripts/test.py && \
chmod 700 /ADT/scripts/test.py && \
mkdir -p /ADT/log && \
mkdir -p /ADT/data/oag && \
mkdir -p /ADT/stage/oag && \
mkdir -p /ADT/quarantine/oag

USER ${USERMAP_UID}

CMD ["python", "/ADT/scripts/test.py"]
