#!/bin/bash
# Cleanup all test containers by stopping and removing them.
# The images downloaded will stay however.

set -e

docker stop $(docker ps -aq)
docker rm $(docker ps -aq)

exit
