#!/bin/bash

# This script does the following:
# - downloads and runs 3 (three) Docker containers all from public repositories
# - builds a new container from the local repository
# - requests running user to supply values used as variables

set -e

# Set variables

# Used by sftp_server function
echo "Setup sftp-server container variables:"
echo "Enter pubkey location (full file path) and press [ENTER]: "
read pubkey
echo "Enter mountpoint location (full file path) and press [ENTER]: "
read mountpoint

# Used by oag function
echo "Setup OAG container variables"
echo "Enter username and press [ENTER]: "
read username
echo "Enter sourcedir on SFTP server name and press [ENTER]: "
read sourcedir
echo "Enter bucketname and press [ENTER]: "
read bucketname
echo "Enter keyprefix and press [ENTER]: "
read keyprefix
echo "Enter awskeyid and press [ENTER]: "
read awskeyid
echo "Enter awssecret and press [ENTER]: "
read awssecret
echo "Enter privkey location (full file path) and press [ENTER]: "
read privkey


# Build SFTP container

function sftp_server {
  run=$(docker run --rm \
        --name sftp-server \
        -v $pubkey:/home/$username/.ssh/authorized_keys:ro \
        -v $mountpoint:/home/$username/$sourcedir \
        -p 2222:22 -d atmoz/sftp \
        $username::1000)
        echo "Created container with SHA: $run"
}

# Build ClamAV container

function clamav {
  run=$(docker run --rm \
        --name clamav \
        -d -p 3310:3310 \
        quay.io/ukhomeofficedigital/clamav)
        echo "Created container with SHA: $run"
}

# Build ClamAV REST API container

function clamav_api {
  run=$(docker run --rm \
        --name clamav-api \
        -e 'CLAMD_HOST=clamav' \
        -p 8080:8080 \
        --link clamav:clamav \
        -t -i -d lokori/clamav-rest)
        echo "Created container with SHA: $run"
}

# Build OAG container

function oag {
  run=$(docker build -t python/oag --rm ../. && \
        docker run --rm \
        --name oag \
        -e SSH_REMOTE_HOST_MAYTECH='sftp-server' \
        -e SSH_REMOTE_USER_MAYTECH=$username \
        -e SSH_PRIVATE_KEY='/home/runner/.ssh/id_rsa' \
        -e SSH_LANDING_DIR=$sourcedir \
        -e S3_BUCKET_NAME=$bucketname \
        -e S3_KEY_PREFIX=$keyprefix \
        -e S3_ACCESS_KEY_ID=$awskeyid \
        -e S3_SECRET_ACCESS_KEY=$awssecret \
        -e CLAMAV_URL='clamav-api' \
        -e CLAMAV_PORT='8080' \
        -v $privkey:/home/runner/.ssh/id_rsa:ro \
        --link clamav-api:clamav-api --link sftp-server:sftp-server \
        -d python/oag
       )
       echo "Created container with SHA: $run"
}

function create_ok_file {
  DATE=`date +%Y_%m_%d_%H_%M_%S`
  run=$(echo "Test data in file." > $mountpoint/1124_$DATE.xml && sleep 5) # wait for OAG container start PM2 and process file
  echo "Created OK test file: 1124_$DATE.xml"
}

function create_virus_file {
  DATE=`date +%Y_%m_%d_%H_%M_%S`
  run=$(cat ./eicar.com > $mountpoint/1124_$DATE.xml)
  echo "Created FAIL test file: 1124_$DATE.xml"
}

function main {
  echo "Building SFTP-server"
  sftp_server
  echo "Done."
  echo "Building clamav"
  clamav
  echo "Done."
  echo "Building clamav-api"
  clamav_api
  echo "Done."
  echo "Building oag"
  oag
  echo "Done."
  echo "Generating test files."
  echo "Creating OK test file and wait 5 seconds so that OAG container can process it. Waiting..."
  create_ok_file
  echo "Done."
  create_virus_file
  echo "Done."
  echo "Check S3 and verify test files are there also check clamav logs to see the virus being blocked"
}

main

exit
