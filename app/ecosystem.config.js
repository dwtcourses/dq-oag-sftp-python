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
        MAYTECH_HOST : process.argv[5],
        MAYTECH_USER : process.argv[6],
        MAYTECH_OAG_PRIVATE_KEY_PATH : process.argv[7],
        MAYTECH_OAG_LANDING_DIR : process.argv[8],
        S3_BUCKET_NAME : process.argv[9],
        S3_KEY_PREFIX : process.argv[10],
        S3_ACCESS_KEY_ID : process.argv[11],
        S3_SECRET_ACCESS_KEY : process.argv[12],
        SECONDARY_BUCKET_NAME : process.argv[13],
        SECONDARY_S3_ACCESS_KEY_ID : process.argv[14],
        SECONDARY_S3_SECRET_ACCESS_KEY : process.argv[15],
        S3_REGION_NAME : "eu-west-2",
        CLAMAV_URL : process.argv[16],
        CLAMAV_PORT : process.argv[17],
        OAG_RDS_HOST : process.argv[18],
        OAG_RDS_DATABASE : process.argv[19],
        OAG_RDS_USERNAME : process.argv[20],
        OAG_RDS_PASSWORD : process.argv[21],
        OAG_RDS_TABLE : process.argv[22]
      }
    }
  ]
};
