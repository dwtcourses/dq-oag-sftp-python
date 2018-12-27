# dq-oag-sftp-docker

Docker container that runs a single Python2.7 script.

## Components

- app/
  - Dockerfile: describe what is installed in the container and the Python file that needs to run
  - packages.txt: Python custom Modules
  - test.py: mock script that is running in the container

- .drone.yml: CI deployment configuration
