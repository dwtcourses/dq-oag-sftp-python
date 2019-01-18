# dq-oag-sftp-python

A collection of Docker containers running a data pipeline.
Tasks include:
- SFTP GET from a remote SFTP server
- Running virus check on each file pulled from SFTP by sending them to ClamAV API
- AWS S3 PUT files to an S3 bucket

## Dependencies

- Docker
- Python2.7
- Drone
- AWS CLI
- AWS Keys with PUT access to S3
- Kubernetes

## Structure

- **app/**
  - *Dockerfile*: describe what is installed in the container and the Python file that needs to run
  - *docker-entrypoint.sh*: bash scripts running at container startup
  - *packages.txt*: Python custom Modules
  - *ecosystem.config.js*: declare variables used by PM2 at runtime
  - **bin/**
    - *DQ_OAG_file_ingest*: Python script used with PM2 to declare imported files to PM2 at runtime
  - **scripts/**
    - *__init__.py*: declare Python module import
    - *DQ_OAG_file_ingest.py*: Python2.7 script running within the container
    - *settings.py*: declare variables passed to the *DQ_OAG_file_ingest.py* file at runtime
  - **test/**
    - *Dockerfile*: PostgreSQL sidekick container config
    - *test.py*: Test Python2.7 script
    - *start.sh*: Download, build and run Docker containers
    - *stop.sh*: Stop and remove **all** Docker containers
    - *eicar.com*: File containing a test virus string
- **kube/**
  - *deployment.yml*: describe a Kubernetes POD deployment
  - *pvc.yml*: declare a Persistent Volume in Kubernetes
  - *secret.yml*: list the Drone secrets passed to the containers during deployment  
- *.drone.yml*: CI deployment configuration
- *LICENSE*: MIT license file
- *README.md*: readme file

## Kubernetes POD connectivity

The POD consists of 3 (three) Docker containers responsible for handling data.

| Container Name | Function | Language | Exposed port | Managed by |
| :--- | :---: | :---: | ---: | --- |
| dq-oag-data-ingest | Data pipeline app| Python2.7 | N/A | DQ Devops |
| clamav-api | API for virus checks | N/A | 8080 |ACP |
| clamav | Database for virus checks | N/A | 3310 |ACP |

Data flow:

- *dq-oag-data-ingest* pulls files from an external SFTP server
- sending these files to *clamav-api* with destination *localhost:8080*
- files are being sent from *clamav-api* to *clamav* with destination *localhost:3310*
- *OK* or *!OK* response text is sent back to *dq-oag-data-ingest*
  - *IF OK* file is uploaded to S3
  - *IF !OK* file is moved to quarantine on the PVC

## Drone secrets

Environmental variables are set in Drone based on secrets listed in the *.drone.yml* file and they are passed to Kubernetes as required.

## Local Test suite

Testing the OAG Python script can be done by having access to AWS S3 and Docker.
The full stack comprise of 6 Docker containers within the same network linked to each other so DNS name resolution works between the components.

The containers can be started and a couple of test files generated using the *start.sh* script located in **app/test**.
The script will require the following variables passed in at runtime.

|Name|Value|Required|Description|
| --- |:---:| :---:| --- |
| pubkey | /local/path/id_rsa.pub | True | Public SSH key used by the SFTP server|
| privkey | /local/path/id_rsa | True | Private SSH used to connect to the SFTP server|
| mountpoint|  /local/path/mountpoint-dir | True | SFTP source directory|
| bucketname | s3-bucket-name | True | S3 bucket name |
| keyprefix | prefix | True | S3 folder name |
| awskeyid | ABCD | True | AWS access key ID |
| awssecret | abcdb1234 | True | AWS Secret access key |
| postgresdb | db | True | Name of the PostgreSQL database |
| postgrestable | table | True | Name of a table in the database |
| postgresuser | user | True | Name of the PostgreSQL user |
| postgrespass | pass | True | Password for _postgresuser_ |

- Components:
  - SFTP container
  - ClamAV container
  - ClamAV REST API container
  - PostgreSQL container
  - PostgreSQL sidekick container
  - OAG Python container

After the script has completed - for the first time it will take around 5 minutes to download all images - there should be a couple of test files in the S3 bucket:

```
1124_YYYY_MM_DD_HH_MM_SS.xml
1124_YYYY_MM_DD_HH_MM_SS.xml.done
```
The other test file contains a test virus string and it will be located under:

```
/ADT/quarantine/oag/1124_YYYY_MM_DD_HH_MM_SS.xml
```

- Launching the test suite

NOTE: navigate to **app/test** first.

```
sh start.sh
```

- When done with testing stop the test suite

NOTE: **all** running containers will be stopped

```
sh stop.sh
```
