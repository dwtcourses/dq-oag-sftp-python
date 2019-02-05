#!/usr/bin/python3
"""
# SFTP OAG Script
# Version 3 - maytech copy

# Move files from SFTP to local drive
# Scan them using ClamAV
# Upload to S3
# Remove from local drive
"""
import re
import os
import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
import paramiko
import boto3
import requests
import psycopg2
from psycopg2 import sql


SSH_REMOTE_HOST_MAYTECH        = os.environ['MAYTECH_HOST']
SSH_REMOTE_USER_MAYTECH        = os.environ['MAYTECH_USER']
SSH_PRIVATE_KEY                = os.environ['MAYTECH_OAG_PRIVATE_KEY_PATH']
SSH_LANDING_DIR                = os.environ['MAYTECH_OAG_LANDING_DIR']
DOWNLOAD_DIR                   = '/ADT/data/oag'
STAGING_DIR                    = '/ADT/stage/oag'
QUARANTINE_DIR                 = '/ADT/quarantine/oag'
SCRIPT_DIR                     = '/ADT/scripts'
BUCKET_NAME                    = os.environ['S3_BUCKET_NAME']
BUCKET_KEY_PREFIX              = os.environ['S3_KEY_PREFIX']
S3_ACCESS_KEY_ID               = os.environ['S3_ACCESS_KEY_ID']
S3_SECRET_ACCESS_KEY           = os.environ['S3_SECRET_ACCESS_KEY']
S3_REGION_NAME                 = os.environ['S3_REGION_NAME']
SECONDARY_BUCKET_NAME          = os.environ['SECONDARY_BUCKET_NAME']
SECONDARY_S3_ACCESS_KEY_ID     = os.environ['SECONDARY_S3_ACCESS_KEY_ID']
SECONDARY_S3_SECRET_ACCESS_KEY = os.environ['SECONDARY_S3_SECRET_ACCESS_KEY']
BASE_URL                       = os.environ['CLAMAV_URL']
BASE_PORT                      = os.environ['CLAMAV_PORT']
RDS_HOST                       = os.environ['OAG_RDS_HOST']
RDS_DATABASE                   = os.environ['OAG_RDS_DATABASE']
RDS_USERNAME                   = os.environ['OAG_RDS_USERNAME']
RDS_PASSWORD                   = os.environ['OAG_RDS_PASSWORD']
RDS_TABLE                      = os.environ['OAG_RDS_TABLE']
LOG_FILE                       = '/ADT/log/sftp_oag.log'

# Setup RDS connection

CONN = psycopg2.connect(host=RDS_HOST,
                        dbname=RDS_DATABASE,
                        user=RDS_USERNAME,
                        password=RDS_PASSWORD)
CUR = CONN.cursor()

def ssh_login(in_host, in_user, in_keyfile):
    """
    Login to SFTP
    """
    logger = logging.getLogger()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key_file(in_keyfile)
    try:
        ssh.connect(in_host, username=in_user, pkey=privkey)
    except Exception:
        logger.exception('SSH CONNECT ERROR')
    return ssh

def run_virus_scan(filename):
    """
    Send a file to scanner API
    """
    logger = logging.getLogger()
    logger.info("Virus Scanning %s folder", filename)
    # do quarantine move using via the virus scanner
    file_list = os.listdir(filename)
    for scan_file in file_list:
        processing = os.path.join(STAGING_DIR, scan_file)
        with open(processing, 'rb') as scan:
            response = requests.post('http://' + BASE_URL + ':' + BASE_PORT + '/scan',
                                     files={'file': scan}, data={'name': scan_file})
            if not 'Everything ok : true' in response.text:
                logger.error('Virus scan FAIL: %s is dangerous!', scan_file)
                file_quarantine = os.path.join(QUARANTINE_DIR, scan_file)
                logger.info('Move %s from staging to quarantine %s', processing, file_quarantine)
                os.rename(processing, file_quarantine)
                return False
            else:
                logger.info('Virus scan OK: %s', scan_file)
    return True

def rds_insert(table, filename):
    """
    Insert into table
    """
    logger = logging.getLogger()
    try:
        CUR.execute(sql.SQL("INSERT INTO {} values (%s)").format(sql.Identifier(table)), (filename,))
        CONN.commit()
    except Exception:
        logger.exception('INSERT ERROR')

def rds_query(table, filename):
    """
    Query table
    """
    logger = logging.getLogger()
    try:
        CUR.execute(sql.SQL("SELECT * FROM {} WHERE filename = (%s)").format(sql.Identifier(table)), (filename,))
        CONN.commit()
    except Exception:
        logger.exception('QUERY ERROR')
    if CUR.fetchone():
        return 1
    else:
        return 0

def main():
    """
    Main function
    """
    logformat = '%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s'
    form = logging.Formatter(logformat)
    logging.basicConfig(
        format=logformat,
        level=logging.INFO
    )
    logger = logging.getLogger()
    if logger.hasHandlers():
           logger.handlers.clear()
    loghandler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
    loghandler.suffix = "%Y-%m-%d"
    loghandler.setFormatter(form)
    logger.addHandler(loghandler)
    logger.info("Starting")

    # Main
    os.chdir(SCRIPT_DIR)
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    if not os.path.exists(STAGING_DIR):
        os.makedirs(STAGING_DIR)
    if not os.path.exists(QUARANTINE_DIR):
        os.makedirs(QUARANTINE_DIR)

    # Note: do not archive the files - the OAG Import script will do the archiving

    downloadcount = 0
    uploadcount = 0
    secondary_uploadcount = 0
    logger.info("Connecting via SSH")
    ssh = ssh_login(SSH_REMOTE_HOST_MAYTECH, SSH_REMOTE_USER_MAYTECH, SSH_PRIVATE_KEY)
    logger.info("Connected")
    sftp = ssh.open_sftp()

    try:
        sftp.chdir(SSH_LANDING_DIR)
        files = sftp.listdir()
        for file_xml in files:
            match = re.search(r'^1124_(SH)?(\d\d\d\d)_(\d\d)_(\d\d)_(\d\d)_(\d\d)_(\d\d)(.*?)\.xml$', file_xml, re.IGNORECASE)
            download = False
            if match is not None:
                try:
                    result = rds_query(RDS_TABLE, file_xml)
                except Exception:
                    logger.exception("Error running SQL query")
                if result == 0:
                    download = True
                    rds_insert(RDS_TABLE, file_xml)
                    logger.info("File %s added to RDS", file_xml)
                else:
                    logger.info("Skipping %s", file_xml)
                    continue

            file_xml_staging = os.path.join(STAGING_DIR, file_xml)

            #protection against redownload
            if os.path.isfile(file_xml_staging) and os.path.getsize(file_xml_staging) > 0 and os.path.getsize(file_xml_staging) == sftp.stat(file_xml).st_size:
                download = False
                purge = rds_query(RDS_TABLE, file_xml)
                if purge == 1:
                    sftp.remove(file_xml)
                    logger.info("Purge %s", file_xml)
            if download:
                logger.info("Downloaded %s to %s", file_xml, file_xml_staging)
                sftp.get(file_xml, file_xml_staging) # remote, local
                if os.path.isfile(file_xml_staging) and os.path.getsize(file_xml_staging) > 0 and os.path.getsize(file_xml_staging) == sftp.stat(file_xml).st_size:
                    logger.info("Purge %s", file_xml)
                    sftp.remove(file_xml)
                else:
                    logger.error("Could not purge %s from SFTP", file_xml)
                    continue
        sftp.close()
        ssh.close()
        # end for
    except Exception:
        logger.exception("Failure")
# end with

# batch virus scan on STAGING_DIR for OAG
    if run_virus_scan(STAGING_DIR):
        for obj in os.listdir(STAGING_DIR):
            scanner = rds_query(RDS_TABLE, obj)
            if scanner == 1:
                file_download = os.path.join(DOWNLOAD_DIR, obj)
                file_staging = os.path.join(STAGING_DIR, obj)
                logger.info("Move %s from staging to download %s", file_staging, file_download)
                os.rename(file_staging, file_download)
                file_done_download = file_download + '.done'
                open(file_done_download, 'w').close()
                downloadcount += 1
            else:
                logger.error("Could not run virus scan on %s", obj)
                break
    logger.info("Downloaded %s files", downloadcount)

# Move files to S3
    logger.info("Starting to move files to S3")
    processed_oag_file_list = [filename for filename in os.listdir(DOWNLOAD_DIR)]
    boto_s3_session = boto3.Session(
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        region_name=S3_REGION_NAME
    )
    boto_secondary_s3_session = boto3.Session(
        aws_access_key_id=SECONDARY_S3_ACCESS_KEY_ID,
        aws_secret_access_key=SECONDARY_S3_SECRET_ACCESS_KEY,
        region_name=S3_REGION_NAME
    )
    if processed_oag_file_list:
        for filename in processed_oag_file_list:
            s3_conn = boto_s3_session.client("s3")
            full_filepath = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.isfile(full_filepath):
                logger.info("Copying %s to S3", filename)
                s3_conn.upload_file(full_filepath, BUCKET_NAME, BUCKET_KEY_PREFIX + "/" + filename)
            else:
                logger.error("Failed to upload %s, exiting...", filename)
                break
        uploadcount += 1
        logger.info("Uploaded %s files to %s", uploadcount, BUCKET_NAME)
# Moving files to Secondary S3 bucket
        for filename in processed_oag_file_list:
            match = re.search(r'^1124_(SH)?(\d\d\d\d)_(\d\d)_(\d\d)_(\d\d)_(\d\d)_(\d\d)(.*?)\.xml$', filename, re.IGNORECASE)
            if match is not None:
                try:
                    time = datetime.datetime.now()
                    secondary_bucket_key_prefix = time.strftime("%Y-%m-%d/%H:%M:%S.%f")
                    secondary_full_filepath = os.path.join(DOWNLOAD_DIR, filename)
                    secondary_s3_conn = boto_secondary_s3_session.client("s3")
                    logger.info("Copying %s to S3 secondary bucket", filename)
                    secondary_s3_conn.upload_file(secondary_full_filepath,
                                                  SECONDARY_BUCKET_NAME,
                                                  secondary_bucket_key_prefix + "/" + filename)
                except Exception:
                    logger.exception("Failed to upload %s, exiting...", filename)
                    break
        secondary_uploadcount += 1
        logger.info("Uploaded %s files to %s secondary", secondary_uploadcount, SECONDARY_BUCKET_NAME)
# Cleaning up
    for filename in processed_oag_file_list:
        try:
            full_filepath = os.path.join(DOWNLOAD_DIR, filename)
            os.remove(full_filepath)
            logger.info("Cleaning up local file %s", filename)
        except Exception:
            logger. exception("Failed to delete file %s", filename)
# end def main

if __name__ == '__main__':
    main()
