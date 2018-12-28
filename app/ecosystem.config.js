module.exports = {
  /**
   * Application configuration
   * Note: all environment variables are required.
   *
   */
  apps : [
    {
      name      : "DQ-OAG-file-ingest",
      script    : "/ADT/bin/DQ_OAG_file_ingest",
      interpreter: "python",
      env: {
        PROCESS_INTERVAL: 60,
        SSH_REMOTE_HOST_MAYTECH : process.argv[5],
        SSH_REMOTE_USER_MAYTECH : process.argv[6],
        SSH_PRIVATE_KEY : process.argv[7],
        SSH_LANDING_DIR : process.argv[8],
        S3_BUCKET_NAME : process.argv[9],
        S3_ACCESS_KEY_ID : process.argv[10],
        S3_SECRET_ACCESS_KEY : process.argv[11],
        S3_REGION_NAME : "eu-west-2",
        CLAMAV_URL : process.argv[13],
        CLAMAV_PORT : process.argv[14]
      }
    }
  ]
}
