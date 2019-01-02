'''
This is a simple script printing out text to stdout every 5 seconds.
'''
from datetime import datetime
import dateutil.parser
import re
import time
import sys
import os
import argparse
import logging
import gdbm
import subprocess
import paramiko
import boto3
import requests

def main():
    parser = argparse.ArgumentParser(description='OAG SFTP Downloader')
    parser.add_argument('-D','--DEBUG',  default=False, action='store_true', help='Debug mode logging')
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
    status = 1

    while True:
        logger.info('All modules imported and I am up and running!')
        time.sleep(5)

if __name__ == '__main__':
    main()
