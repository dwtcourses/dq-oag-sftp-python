FROM centos:8

ENV USERMAP_UID 1000
ENV PYTHONPATH="$PYTHONPATH:/ADT"

# Setup folder structure and copy files
RUN mkdir -p \
             /tmp/ADT/scripts \
             /tmp/ADT/data/oag \
             /tmp/ADT/stage/oag \
             /tmp/ADT/quarantine/oag \
             /tmp/ADT/failed_to_parse/oag \
             /tmp/ADT/log \
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
RUN yum update -y
RUN yum install -y wget make gcc openssl-devel zlib-devel pcre-devel bzip2-devel libffi-devel epel-release python3

# Install modules with pip
RUN pip3 install --no-cache-dir -r /tmp/ADT/scripts/packages.txt

# Install PM2
RUN curl -sL https://raw.githubusercontent.com/nodesource/distributions/master/rpm/setup_12.x -o setup_12.x && bash setup_12.x && rm setup_12.x && \
    yum install -y nodejs && \
    npm install -g pm2

VOLUME ["/ADT"]
RUN chown -R runner:runner /ADT

RUN chown runner:runner /docker-entrypoint.sh && \
chmod +x /docker-entrypoint.sh

USER ${USERMAP_UID}

WORKDIR /ADT

ENTRYPOINT ["/docker-entrypoint.sh"]

# Start PM2
CMD pm2-docker /ADT/scripts/ecosystem.config.js  -- --config $SSH_REMOTE_HOST_MAYTECH $SSH_REMOTE_USER_MAYTECH $SSH_PRIVATE_KEY \
    $SSH_LANDING_DIR $S3_BUCKET_NAME $S3_ACCESS_KEY_ID $S3_SECRET_ACCESS_KEY \
    $CLAMAV_URL $CLAMAV_PORT $OAG_RDS_HOST $OAG_RDS_DATABASE $OAG_RDS_USERNAME $OAG_RDS_PASSWORD \
    $OAG_RDS_TABLE $SLACK_WEBHOOK

# Save PM2 configuration
RUN pm2 save
