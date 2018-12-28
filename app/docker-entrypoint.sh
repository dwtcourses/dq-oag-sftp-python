#!/bin/bash

# Copy all files and folders from the staging area to PVC
cp -R /tmp/ADT/data /ADT
cp -R /tmp/ADT/stage /ADT
cp -R /tmp/ADT/scripts /ADT
cp -R /tmp/ADT/quarantine /ADT

# Set permissions
chown -R scriptrunner:runner /ADT/data
chown -R scriptrunner:runner /ADT/stage
chown -R scriptrunner:runner /ADT/scripts
chown -R scriptrunner:runner /ADT/quarantine

exec "$@"
