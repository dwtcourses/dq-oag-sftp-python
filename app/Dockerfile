FROM python:2.7

ENV USERMAP_UID 1000
ENV PYTHONPATH="$PYTHONPATH:/ADT"

# Setup folder structure and copy files
RUN mkdir -p \
             /tmp/ADT/scripts \
             /tmp/ADT/data/oag \
             /tmp/ADT/stage/oag \
             /tmp/ADT/quarantine/oag \
             /tmp/ADT/bin \
             /ADT \
             /home/runner/.pm2 \
             /home/runner/.ssh

COPY packages.txt /tmp/ADT/scripts
COPY ecosystem.config.js /tmp/ADT/scripts
COPY docker-entrypoint.sh /
ADD bin /tmp/ADT/bin
ADD scripts /tmp/ADT/scripts

# Add user
RUN groupadd -r runner && \
    useradd --no-log-init -u $USERMAP_UID -r -g runner runner && \
    groupadd docker && \
    usermod -aG docker runner && \
    chown -R runner:runner /ADT && \
    chown -R runner:runner /home/runner/.pm2 && \
    chown -R runner:runner /home/runner/.ssh

# Install script dependencies
RUN apt-get install git wget
RUN apt-get update -y && apt-get upgrade -y
RUN wget http://ftp.gnu.org/gnu/gdbm/gdbm-1.8.3.tar.gz && \
    tar -xvzf gdbm-1.8.3.tar.gz && \
    cd gdbm-1.8.3 && \
    ./configure --prefix=/usr && \
    make && \
    make BINOWN=root BINGRP=root install
RUN pip install --no-cache-dir -r /tmp/ADT/scripts/packages.txt

# Install PM2
RUN apt-get update \
    && apt-get upgrade -y \
    && curl -sL https://deb.nodesource.com/setup_8.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pm2

# Get script files
RUN git clone https://github.com/UKHomeOffice/dq-ssm_ingest.git

VOLUME ["/ADT"]
RUN chown -R runner:runner /ADT

RUN chown runner:runner /docker-entrypoint.sh && \
chmod +x /docker-entrypoint.sh

USER ${USERMAP_UID}

WORKDIR /ADT

ENTRYPOINT ["/docker-entrypoint.sh"]

# Start PM2
CMD pm2-docker /ADT/scripts/ecosystem.config.js  -- --config $SSH_REMOTE_HOST_MAYTECH $SSH_REMOTE_USER_MAYTECH $SSH_PRIVATE_KEY $SSH_LANDING_DIR $S3_BUCKET_NAME $S3_ACCESS_KEY_ID $S3_SECRET_ACCESS_KEY $CLAMAV_URL $CLAMAV_PORT

# Save PM2 configuration
RUN pm2 save
