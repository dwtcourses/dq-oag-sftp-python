# dq-oag-sftp-docker

Docker container that runs a single Python2.7 script.

## Components

- app/
  - Dockerfile: describe what is installed in the container and the Python file that needs to run
  - packages.txt: Python custom Modules
  - test.py: mock script that is running in the container

- .drone.yml: CI deployment configuration

## Local Test suite

- Components:
  - SFTP container

  ```
  docker run --rm \
  --name sftp-server \
  -v /local/path/id_rsa.pub:/home/sftp_user/.ssh/authorized_keys:ro \
  -v /local/path/homeshare:/home/sftp_user/sftp \
  -p 2222:22 -d atmoz/sftp \
  sftp_user::1000
  ```
  - ClamAV container

  ```
  docker run --name clamav -d -p 3310:3310 quay.io/ukhomeofficedigital/clamav
  ```
  - ClamAV REST API container

  ```
  docker run --rm \
  --name clamav-api \
  -e 'CLAMD_HOST=clamav' \
  -p 8080:8080 \
  --link clamav:clamav \
  -t -i -d lokori/clamav-rest
  ```
  - OAG SFTP container

  Build it first using the Dockerfile in the repo:

  ```
  docker build -t python/oag --rm .
  ```
  Run the container adding in all required variables:

  ```
  docker run --rm \
  --name oag \
  -e SSH_REMOTE_HOST_MAYTECH='sftp-server' \
  -e SSH_REMOTE_USER_MAYTECH='sftp_user' \
  -e SSH_PRIVATE_KEY='/home/runner/.ssh/id_rsa' \
  -e SSH_LANDING_DIR='sftp' \
  -e S3_BUCKET_NAME='bucket-name' \
  -e S3_KEY_PREFIX='bucket-prefix' \
  -e S3_ACCESS_KEY_ID='foo' \
  -e S3_SECRET_ACCESS_KEY='bar' \
  -e CLAMAV_URL='clamav-api' \
  -e CLAMAV_PORT='8080' \
  -v /local/path/id_rsa:/home/runner/.ssh/id_rsa:ro \
  --link clamav-api:clamav-api --link sftp-server:sftp-server \
  -d python/oag
  ```

  After all containers are up add a file matching the *regex* to `/local/path/homeshare` and verify it being uploaded to S3.
