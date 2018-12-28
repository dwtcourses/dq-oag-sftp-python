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
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    while True:
        logger.info('All modules imported and I am up and running!')
        time.sleep(5)

if __name__ == '__main__':
    main()
