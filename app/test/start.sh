#!/bin/bash

# This script does the following:
# - downloads and runs 3 (three) Docker containers all from public repositories
# - builds a new container from the local repository
# - requests running user to supply values used as variables

set -e

# Set variables

# Used by local SFTP
echo "********************************************"
echo "Setup sftp-server container variables:"
echo "********************************************"
echo "Enter pubkey location (full file path) and press [ENTER]: "
read pubkey
echo "Enter privkey location (full file path) and press [ENTER]: "
read privkey
echo "Enter mountpoint location (full file path) and press [ENTER]: "
read mountpoint

# Used for S3 upload
echo "********************************************"
echo "Setup OAG container variables"
echo "********************************************"
echo "Enter bucketname and press [ENTER]: "
read bucketname
echo "Enter awskeyid and press [ENTER]: "
read awskeyid
echo "Enter awssecret and press [ENTER]: "
read awssecret
echo "Enter webhook and press [ENTER]: "
read webhook

# Build SFTP container

function sftp_server {
  run=$(docker run --rm \
        --name sftp-server \
        -v $pubkey:/home/test/.ssh/authorized_keys:ro \
        -v $mountpoint:/home/test/test \
        -p 2222:22 -d atmoz/sftp \
        test::1000
        )
        echo "Created container with SHA: $run"
}

# Build ClamAV container

function clamav {
  run=$(docker run --rm \
        --name clamav \
        -d -p 3310:3310 \
        quay.io/ukhomeofficedigital/clamav
        )
        echo "Created container with SHA: $run"
}

# Build ClamAV REST API container

function clamav_api {
  run=$(docker run --rm \
        --name clamav-api \
        -e 'CLAMD_HOST=clamav' \
        -p 8080:8080 \
        --link clamav:clamav \
        -t -i -d lokori/clamav-rest
        )
        echo "Created container with SHA: $run"
}

# Build PostgreSQL container

function postgresql {
  run=$(docker run --rm \
        --name postgresql \
        -e POSTGRES_PASSWORD='foobar' \
        -e POSTGRES_USER='root' \
        -e POSTGRES_DB='foo' \
        -d postgres
       )
       echo "Created container with SHA: $run"
}

# Build Postgres sidekick

function postgresql_sidekick {
  run=$(docker build \
       -t psql/bash --rm . && \
       docker run --rm \
       --name psql \
       --link postgresql:postgresql \
       -d psql/bash
       )
       echo "Created container with SHA: $run"
}

# Build OAG container

function oag {
  run=$(docker build -t python/oag --rm ../. && \
        docker run \
        --name oag \
        -e SSH_REMOTE_HOST_MAYTECH='sftp-server' \
        -e SSH_REMOTE_USER_MAYTECH='test' \
        -e SSH_PRIVATE_KEY='/home/runner/.ssh/id_rsa' \
        -e SSH_LANDING_DIR='test' \
        -e S3_BUCKET_NAME=$bucketname \
        -e S3_ACCESS_KEY_ID=$awskeyid \
        -e S3_SECRET_ACCESS_KEY=$awssecret \
        -e CLAMAV_URL='clamav-api' \
        -e CLAMAV_PORT='8080' \
        -e OAG_RDS_HOST='postgresql' \
        -e OAG_RDS_DATABASE='foo' \
        -e OAG_RDS_USERNAME='root' \
        -e OAG_RDS_PASSWORD='foobar' \
        -e OAG_RDS_TABLE='bar' \
        -e SLACK_WEBHOOK=$webhook \
        -v $privkey:/home/runner/.ssh/id_rsa:ro \
        --link clamav-api:clamav-api \
        --link sftp-server:sftp-server \
        --link postgresql:postgresql \
        -d python/oag
       )
       echo "Created container with SHA: $run"
}

function create_ok_file {
  DATE=`date +%Y_%m_%d_%H_%M_%S`
  run=$(
    {
        echo "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        echo "<foo>"
        echo "<foobar>foobar</foobar>"
        echo "</foo>"
    } > $mountpoint/1124_$DATE.xml && sleep 5) # wait for OAG container start PM2 and process file
  echo "Created OK test file: 1124_$DATE.xml"
}

function create_fail_file {
  DATE=`date +%Y_%m_%d_%H_%M_%S`
  run=$(echo "This is not an XML file" > $mountpoint/1124_$DATE.xml && sleep 5) # wait for OAG container start PM2 and process file
  echo "Created FAIL test file: 1124_$DATE.xml"
}

function create_virus_file {
  DATE=`date +%Y_%m_%d_%H_%M_%S`
  run=$(cat ./eicar.com > $mountpoint/1124_$DATE.xml)
  echo "Created VIRUS test file: 1124_$DATE.xml"
}

function main {
  echo "********************************************"
  echo "Building postgressql"
  postgresql
  echo "Done."
  echo "********************************************"
  echo "Building SFTP-server"
  sftp_server
  echo "Done."
  echo "********************************************"
  echo "Building clamav"
  clamav
  echo "Done."
  echo "********************************************"
  echo "Building clamav-api"
  clamav_api
  echo "Done."
  echo "********************************************"
  echo "Building and running postgresql sidekick"
  postgresql_sidekick
  echo "Done."
  echo "********************************************"
  echo "Building oag"
  oag
  echo "Done."
  echo "********************************************"
  echo "Generating test files."
  echo "Creating OK test file and wait 5 seconds so that OAG container can process it. Waiting..."
  create_ok_file
  echo "Done."
  echo "********************************************"
  echo "Creating FAIL test file and wait 5 seconds so that OAG container can process it. Waiting..."
  create_fail_file
  echo "Done."
  echo "********************************************"
  echo "Creating VIRUS test file. Waiting..."
  create_virus_file
  echo "Done."
  echo "********************************************"
  echo "Check S3 and verify test files are there also check clamav logs to see the virus being blocked"
  echo "********************************************"
}

main

exit
