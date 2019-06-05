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
import sys
import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
import json
import xml.dom.minidom
import urllib.request
import paramiko
import boto3
import requests
import psycopg2
from psycopg2 import sql


SSH_REMOTE_HOST_MAYTECH = os.environ['MAYTECH_HOST']
SSH_REMOTE_USER_MAYTECH = os.environ['MAYTECH_USER']
SSH_PRIVATE_KEY         = os.environ['MAYTECH_OAG_PRIVATE_KEY_PATH']
SSH_LANDING_DIR         = os.environ['MAYTECH_OAG_LANDING_DIR']
DOWNLOAD_DIR            = '/ADT/data/oag'
STAGING_DIR             = '/ADT/stage/oag'
QUARANTINE_DIR          = '/ADT/quarantine/oag'
SCRIPT_DIR              = '/ADT/scripts'
LOG_FILE                = '/ADT/log/DQ_SFTP_OAG.log'
FAILED_PARSE_DIR        = '/ADT/failed_to_parse/oag'
BUCKET_NAME             = os.environ['S3_BUCKET_NAME']
S3_ACCESS_KEY_ID        = os.environ['S3_ACCESS_KEY_ID']
S3_SECRET_ACCESS_KEY    = os.environ['S3_SECRET_ACCESS_KEY']
S3_REGION_NAME          = os.environ['S3_REGION_NAME']
BASE_URL                = os.environ['CLAMAV_URL']
BASE_PORT               = os.environ['CLAMAV_PORT']
RDS_HOST                = os.environ['OAG_RDS_HOST']
RDS_DATABASE            = os.environ['OAG_RDS_DATABASE']
RDS_USERNAME            = os.environ['OAG_RDS_USERNAME']
RDS_PASSWORD            = os.environ['OAG_RDS_PASSWORD']
RDS_TABLE               = os.environ['OAG_RDS_TABLE']
SLACK_WEBHOOK           = os.environ['SLACK_WEBHOOK']

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
    except Exception as err:
        logger.error('SSH CONNECT ERROR')
        logger.exception(str(err))
        error = str(err)
        send_message_to_slack(error)
        sys.exit(1)
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
                logger.warning('Virus scan FAIL: %s is dangerous!', scan_file)
                warning = ("Virus scan FAIL: " + scan_file + " is dangerous!")
                send_message_to_slack(str(warning))
                file_quarantine = os.path.join(QUARANTINE_DIR, scan_file)
                logger.info('Move %s from staging to quarantine %s', processing, file_quarantine)
                os.rename(processing, file_quarantine)
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
    except Exception as err:
        logger.error('INSERT ERROR')
        logger.exception(str(err))
        error = str(err)
        send_message_to_slack(error)
        sys.exit(1)

def rds_query(table, filename):
    """
    Query table
    """
    logger = logging.getLogger()
    try:
        CUR.execute(sql.SQL("SELECT * FROM {} WHERE filename = (%s)").format(sql.Identifier(table)), (filename,))
        CONN.commit()
    except Exception as err:
        logger.error('QUERY ERROR')
        logger.exception(str(err))
        error = str(err)
        send_message_to_slack(error)
        sys.exit(1)
    if CUR.fetchone():
        return 1
    else:
        return 0

def parse_xml(file_xml_staging, file_xml):
    """
    Parse XML files
    Move failed to parse files
    """
    logger = logging.getLogger()
    try:
        xml.dom.minidom.parse("{0}".format(file_xml_staging))
        logger.info('%s has been parsed successfully', file_xml_staging)

    except Exception as err:
        logger.error('XML PARSE ERROR')
        logger.exception(str(err))
        error = str(err)
        err_message = 'Could not parse' + ' ' + file_xml_staging + ' ' + error
        send_message_to_slack(err_message)
        if err is not None:
            file_staging = os.path.join(STAGING_DIR, file_xml_staging)
            file_failed_parse = os.path.join(FAILED_PARSE_DIR, file_xml_staging)
            os.rename(file_staging, file_failed_parse)
            logger.error('Moved failed parsed file %s',
                         file_xml_staging + ' ' + 'to' + ' ' + FAILED_PARSE_DIR + '/' + file_xml)

def find_parsed_failed_xml(path, name):
    """
    Look up failed to parse file
    """
    logger = logging.getLogger()
    try:
        for files in os.walk(path):
            if name in files:
                logger.info('%s found in failed to parse directory', name)
        return 1

    except Exception as err:
        logger.error('PARSED FILE LOOKUP ERROR')
        logger.exception(str(err))
        error = str(err)
        send_message_to_slack(error)
        sys.exit(1)

def send_message_to_slack(text):
    """
    Formats the text and posts to a specific Slack web app's URL
    Returns:
        Slack API repsonse
    """
    logger = logging.getLogger()
    try:
        post = {
            "text": ":fire: :sad_parrot: An error has occured in the *OAG* pod :sad_parrot: :fire:",
            "attachments": [
                {
                    "text": "{0}".format(text),
                    "color": "#B22222",
                    "attachment_type": "default",
                    "fields": [
                        {
                            "title": "Priority",
                            "value": "High",
                            "short": "false"
                        }
                    ],
                    "footer": "Kubernetes API",
                    "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png"
                }
            ]
            }
        json_data = json.dumps(post)
        req = urllib.request.Request(url=SLACK_WEBHOOK,
                                     data=json_data.encode('utf-8'),
                                     headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        return resp

    except Exception as err:
        logger.error(
            'The following error has occurred on line: %s',
            sys.exc_info()[2].tb_lineno)
        logger.error(str(err))
        sys.exit(1)


def main():
    """
    Main function
    """
# Setup logging and global variables
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
    consolehandler = logging.StreamHandler()
    consolehandler.setFormatter(form)
    logger.addHandler(consolehandler)
    logger.info("Starting")

    # Main
    os.chdir(SCRIPT_DIR)

    # downloadcount = 0
    uploadcount = 0


# Connect and GET files from SFTP
    logger.info("Connecting via SSH")
    ssh = ssh_login(SSH_REMOTE_HOST_MAYTECH, SSH_REMOTE_USER_MAYTECH, SSH_PRIVATE_KEY)
    sftp = ssh.open_sftp()
    logger.info("Connected")

    try:
        sftp.chdir(SSH_LANDING_DIR)
        files = sftp.listdir()
        for file_xml in files:
            match = re.search(r'^1124_(SH)?(\d\d\d\d)_(\d\d)_(\d\d)_(\d\d)_(\d\d)_(\d\d)(.*?)\.xml$', file_xml, re.IGNORECASE)
            download = False
            if match is None:
                send_message_to_slack("Pulling zero files! Contact the vendor")
            if match is not None:
                try:
                    result = rds_query(RDS_TABLE, file_xml)
                except Exception as err:
                    logger.error("Error running SQL query")
                    logger.exception(str(err))
                    error = str(err)
                    send_message_to_slack(error)
                    sys.exit(1)
                if result == 0:
                    download = True
                else:
                    logger.debug("Skipping %s", file_xml)
                    continue

            file_xml_staging = os.path.join(STAGING_DIR, file_xml)

# Protection against redownload
            if os.path.isfile(file_xml_staging) and os.path.getsize(file_xml_staging) > 0 and os.path.getsize(file_xml_staging) == sftp.stat(file_xml).st_size:
                download = False
                purge = rds_query(RDS_TABLE, file_xml)
                file_failed_parse = find_parsed_failed_xml(FAILED_PARSE_DIR, file_xml)
                if purge == 1 and file_failed_parse == 0:
                    sftp.remove(file_xml)
                    logger.info("Purge %s from SFTP", file_xml)
            if download:
                sftp.get(file_xml, file_xml_staging) # remote, local
                logger.info("Downloaded %s to %s", file_xml, file_xml_staging)
                rds_insert(RDS_TABLE, file_xml)
                logger.info("File %s added to RDS", file_xml)
                try:
                    if run_virus_scan(STAGING_DIR):
                        for obj in os.listdir(STAGING_DIR):
                            scanner = rds_query(RDS_TABLE, obj)
                            if scanner == 1:
                                if parse_xml(file_xml_staging, file_xml):
                                    os.rename(file_xml_staging, file_download)
                                    logger.info("Moved %s from staging to download %s", file_xml_staging, file_download)
                            else:
                                logger.error("Could not run virus scan on %s", obj)
                        # downloadcount += 1
                        # logger.info("Downloaded %s files", downloadcount)

                except Exception as err:
                    logger.exception(str(err))
                    error = str(err)
                    send_message_to_slack(error)

                try:
                    for obj in os.listdir(DOWNLOAD_DIR):
                        file_download = os.path.join(DOWNLOAD_DIR, obj)
                        if os.path.isfile(file_download) and os.path.getsize(file_download) > 0 and os.path.getsize(file_download) == sftp.stat(file_xml).st_size:
                            purge = rds_query(RDS_TABLE, file_xml)
                                # file_failed_parse = find_parsed_failed_xml(FAILED_PARSE_DIR, file_xml)
                                # if purge == 1 and file_failed_parse == 0:
                            if purge == 1:
                                sftp.remove(file_xml)
                                logger.info("Deleted %s from SFTP", file_xml)
                        else:
                            logger.error("Local file size" + ' ' + obj + ' ' + "does not match" + file_xml)

                except Exception as err:
                    logger.exception(str(err))
                    error = str(err)
                    error_message = "Could not delete" + file_xml + " " + " " + "from SFTP" + " " + error
                    send_message_to_slack(error_message)

        sftp.close()
        ssh.close()

    except Exception as err:
        logger.error("Failure getting files from SFTP")
        logger.exception(str(err))
        error = str(err)
        send_message_to_slack(error)
        sys.exit(1)


# Move files to S3
    processed_oag_file_list = [filename for filename in os.listdir(DOWNLOAD_DIR)]
    boto_s3_session = boto3.Session(
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        region_name=S3_REGION_NAME
    )
    if processed_oag_file_list:
        for filename in processed_oag_file_list:
            s3_conn = boto_s3_session.client("s3")
            full_filepath = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.isfile(full_filepath):
                try:
                    time = datetime.datetime.now()
                    bucket_key_prefix = time.strftime("%Y-%m-%d/%H:%M:%S.%f")
                    logger.info("Copying %s to S3", filename)
                    s3_conn.upload_file(full_filepath, BUCKET_NAME,
                                        bucket_key_prefix + "/" + filename)
                    uploadcount += 1
                except Exception as err:
                    logger.error(
                        "Failed to upload %s, exiting...", filename)
                    logger.exception(str(err))
                    error = str(err)
                    send_message_to_slack(error)
                    sys.exit(1)
        logger.info("Uploaded %s files to %s", uploadcount, BUCKET_NAME)

# Cleaning up
    for filename in processed_oag_file_list:
        try:
            full_filepath = os.path.join(DOWNLOAD_DIR, filename)
            os.remove(full_filepath)
            logger.info("Cleaning up local file %s", filename)
        except Exception as err:
            logger.error("Failed to delete file %s", filename)
            logger.exception(str(err))
            error = str(err)
            send_message_to_slack(error)
            sys.exit(1)

if __name__ == '__main__':
    main()
