"""Settings module - used to import the configuration settings from the
environment variables"""

import os

"""DQ OAG file ingest"""
PROCESS_INTERVAL        = int(os.environ.get('PROCESS_INTERVAL', 60))
SSH_REMOTE_HOST_MAYTECH = os.environ.get('SSH_REMOTE_HOST_MAYTECH')
SSH_REMOTE_USER_MAYTECH = os.environ.get('SSH_REMOTE_USER_MAYTECH')
SSH_PRIVATE_KEY         = os.environ.get('SSH_PRIVATE_KEY')
SSH_LANDING_DIR         = os.environ.get('SSH_LANDING_DIR')
S3_BUCKET_NAME          = os.environ.get('S3_BUCKET_NAME')
S3_ACCESS_KEY_ID        = os.environ.get('S3_ACCESS_KEY_ID')
S3_SECRET_ACCESS_KEY    = os.environ.get('S3_SECRET_ACCESS_KEY')
CLAMAV_URL              = os.environ.get('CLAMAV_URL')
CLAMAV_PORT             = os.environ.get('CLAMAV_PORT')
