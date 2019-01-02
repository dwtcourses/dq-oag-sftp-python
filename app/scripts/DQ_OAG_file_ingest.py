#!/usr/bin/python
"""
# SFTP OAG Script
# Version 3 - maytech copy

# Move files from SFTP to local drive
# Scan them using ClamAV
# Upoad to S3
# Remove from local drive
"""
import re
import os
import argparse
import logging
import gdbm
import paramiko
import boto3
import requests


SSH_REMOTE_HOST_MAYTECH = os.environ['MAYTECH_HOST']
SSH_REMOTE_USER_MAYTECH = os.environ['MAYTECH_USER']
SSH_PRIVATE_KEY         = os.environ['MAYTECH_OAG_PRIVATE_KEY_PATH']
SSH_LANDING_DIR         = os.environ['MAYTECH_OAG_LANDING_DIR']
DOWNLOAD_DIR            = '/ADT/data/oag'
STAGING_DIR             = '/ADT/stage/oag'
QUARANTINE_DIR          = '/ADT/quarantine/oag'
BUCKET_NAME             = os.environ['S3_BUCKET_NAME']
BUCKET_KEY_PREFIX       = os.environ['S3_KEY_PREFIX']
S3_ACCESS_KEY_ID        = os.environ['S3_ACCESS_KEY_ID']
S3_SECRET_ACCESS_KEY    = os.environ['S3_SECRET_ACCESS_KEY']
S3_REGION_NAME          = os.environ['S3_REGION_NAME']
BASE_URL                = os.environ['CLAMAV_URL']
BASE_PORT               = os.environ['CLAMAV_PORT']

def ssh_login(in_host, in_user, in_keyfile):
    logger = logging.getLogger()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.client.AutoAddPolicy()) ## This line can be removed when the host is added to the known_hosts file
    privkey = paramiko.RSAKey.from_private_key_file(in_keyfile)
    try:
        ssh.connect(in_host, username=in_user, pkey=privkey)
    except Exception, e:
        logger.exception('SSH CONNECT ERROR')
        os._exit(1)
    return ssh


def run_virus_scan(filename):
    logger = logging.getLogger()
    logger.debug("Virus Scanning %s folder", filename)
    # do quarantine move using via the virus scanner
    file_list = os.listdir(filename)
    for scan_file in file_list:
        processing = os.path.join(STAGING_DIR, scan_file)
        with open(processing, 'rb') as scan:
            response = requests.post('http://' + BASE_URL + ':' + BASE_PORT + '/scan', files={'file': scan}, data={'name': scan_file})
            if not 'Everything ok : true' in response.text:
                logger.error('File %s is dangerous, preventing upload', scan_file)
                file_quarantine = os.path.join(QUARANTINE_DIR, scan_file)
                logger.info('Move %s from staging to quarantine %s', processing, file_quarantine)
                os.rename(processing, file_quarantine)
                return False
            else:
                logger.info('Virus scan OK')
    return True
# end def run_virus_scan


def main():
    parser = argparse.ArgumentParser(description='OAG SFTP Downloader')
    parser.add_argument('-D', '--DEBUG', default=False, action='store_true', help='Debug mode logging')
    args = parser.parse_args()
    if args.DEBUG:
        logging.basicConfig(
            filename='/ADT/log/sftp_oag_maytech.log',
            format="%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s",
            datefmt='%Y-%m-%d %H:%M:%S',
            level=logging.DEBUG
        )
    else:
        logging.basicConfig(
            filename='/ADT/log/sftp_oag_maytech.log',
            format="%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s",
            datefmt='%Y-%m-%d %H:%M:%S',
            level=logging.INFO
        )

    logger = logging.getLogger()
    logger.info("Starting")

    # Main
    os.chdir('/ADT/scripts')
    oaghistory = gdbm.open('/ADT/scripts/oaghistory.db', 'c')
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    if not os.path.exists(STAGING_DIR):
        os.makedirs(STAGING_DIR)
    if not os.path.exists(QUARANTINE_DIR):
        os.makedirs(QUARANTINE_DIR)

    # Note: do not archive the files - the OAG Import script will do the archiving

    downloadcount = 0
    uploadcount = 0
    logger.info("Connecting via SSH")
    ssh = ssh_login(SSH_REMOTE_HOST_MAYTECH, SSH_REMOTE_USER_MAYTECH, SSH_PRIVATE_KEY)
    logger.info("Connected")
    sftp = ssh.open_sftp()

    try:
        sftp.chdir(SSH_LANDING_DIR)
        files = sftp.listdir()
        for file_xml in files:
            match = re.search('^1124_(SH)?(\d\d\d\d)_(\d\d)_(\d\d)_(\d\d)_(\d\d)_(\d\d)(.*?)\.xml$', file_xml, re.I)
            download = False
            if match is not None:
                if file_xml not in oaghistory.keys():
                    oaghistory[file_xml] = 'N' # new

                if oaghistory[file_xml] == 'N':
                    download = True
            else:
                logger.info("Skipping %s", file_xml)
                continue

            file_xml_staging = os.path.join(STAGING_DIR, file_xml)

            #protection against redownload
            if os.path.isfile(file_xml_staging) and os.path.getsize(file_xml_staging) > 0 and os.path.getsize(file_xml_staging) == sftp.stat(file_xml).st_size:
                logger.info("File exists")
                download = False
                oaghistory[file_xml] = 'R' # ready
                logger.debug("purge %s", file_xml)
                sftp.remove(file_xml)
            if download:
                logger.info("Downloading %s to %s", file_xml, file_xml_staging)
                sftp.get(file_xml, file_xml_staging) # remote, local
                if os.path.isfile(file_xml_staging) and os.path.getsize(file_xml_staging) > 0 and os.path.getsize(file_xml_staging) == sftp.stat(file_xml).st_size:
                    logger.debug("purge %s", file_xml)
                    sftp.remove(file_xml)
        # end for
    except:
        logger.exception("Failure")
# end with

# batch virus scan on STAGING_DIR for OAG
    if run_virus_scan(STAGING_DIR):
        for f in os.listdir(STAGING_DIR):
            oaghistory[f] = 'R'
            file_download = os.path.join(DOWNLOAD_DIR, f)
            file_staging = os.path.join(STAGING_DIR, f)
            logger.info("Move %s from staging to download %s", file_staging, file_download)
            os.rename(file_staging, file_download)
            file_done_download = file_download + '.done'
            open(file_done_download, 'w').close()
            downloadcount += 1

    oaghistory.close()
    logger.info("Downloaded %s files", downloadcount)


# Move files to S3
    logger.info("Starting to move files to S3")
    processed_oag_file_list = [f for f in os.listdir(DOWNLOAD_DIR)]
    boto_s3_session = boto3.Session(
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        region_name=S3_REGION_NAME
    )
    if processed_oag_file_list:
        for filename in processed_oag_file_list:
            s3 = boto_s3_session.client("s3")
            full_filepath = os.path.join(DOWNLOAD_DIR, filename)
            logger.info("Copying %s to S3", filename)
            if os.path.isfile(full_filepath):
                s3.upload_file(full_filepath, BUCKET_NAME, BUCKET_KEY_PREFIX + "/" + filename)
                os.remove(full_filepath)
                logger.info("Deleting local file: %s", filename)
                uploadcount += 1
                logger.info("Uploaded %s files", uploadcount)

# end def main

if __name__ == '__main__':
    main()
