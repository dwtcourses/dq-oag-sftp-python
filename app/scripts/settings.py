"""Settings module - used to import the configuration settings from the
environment variables"""

import os

"""DQ OAG file ingest"""
PROCESS_INTERVAL               = int(os.environ.get('PROCESS_INTERVAL', 60))
MAYTECH_HOST                   = os.environ.get('SSH_REMOTE_HOST_MAYTECH')
MAYTECH_USER                   = os.environ.get('SSH_REMOTE_USER_MAYTECH')
MAYTECH_OAG_PRIVATE_KEY_PATH   = os.environ.get('SSH_PRIVATE_KEY')
MAYTECH_OAG_LANDING_DIR        = os.environ.get('SSH_LANDING_DIR')
S3_BUCKET_NAME                 = os.environ.get('S3_BUCKET_NAME')
S3_ACCESS_KEY_ID               = os.environ.get('S3_ACCESS_KEY_ID')
S3_SECRET_ACCESS_KEY           = os.environ.get('S3_SECRET_ACCESS_KEY')
CLAMAV_URL                     = os.environ.get('CLAMAV_URL')
CLAMAV_PORT                    = os.environ.get('CLAMAV_PORT')
OAG_RDS_HOST                   = os.environ.get('OAG_RDS_HOST')
OAG_RDS_DATABASE               = os.environ.get('OAG_RDS_DATABASE')
OAG_RDS_USERNAME               = os.environ.get('OAG_RDS_USERNAME')
OAG_RDS_PASSWORD               = os.environ.get('OAG_RDS_PASSWORD')
OAG_RDS_TABLE                  = os.environ.get('OAG_RDS_TABLE')
SLACK_WEBHOOK                  = os.environ.get('SLACK_WEBHOOK')
