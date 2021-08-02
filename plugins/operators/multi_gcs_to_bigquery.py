"""
    Author: Justin Baroux
    Email: hello@justinbaroux.com
    Description: Load Multiple bucket files with the same schema fields into differents Big Query partitions
    Version: 1.1
"""

import os
import json
import time
import logging
import datetime

import pandas as pd

from airflow.contrib.hooks.bigquery_hook import BigQueryHook
from airflow.contrib.hooks.gcs_hook import GoogleCloudStorageHook

from airflow.models import BaseOperator
from airflow.contrib.operators.gcs_to_bq import GoogleCloudStorageToBigQueryOperator

from airflow.utils.decorators import apply_defaults


class MultiGoogleCloudStorageToBigQueryOperator(BaseOperator):
    """
    Loads Multiples bucket from Google Cloud Storage into BigQuery.

        :param bucket: The bucket to load from. (templated)
        :type bucket: str

        :param source_objects_directory : the bucket directory with a DYNAMIC PART ( %DATE_VARIABLE% )
        :example : Facebook/%DATE_VARIABLE%/accounts
        :type source_objects_directory str

        :param source_objects_files : files name in the directory
        :example : account_*.json
        :type source_objects_files str

        :param destination_project_dataset_table: BigQuery table to load data into with a DYNAMIC PART.
        :example : tmp_accounts$%DATE_VARIABLE%
        :type destination_project_dataset_table: str

        :param schema_fields: the big query schema field list as defined here:
            https://cloud.google.com/bigquery/docs/reference/v2/jobs#configuration.load
        :type schema_fields: list

        :param source_format: File format to export.
        :type source_format: str

        :param create_disposition: The create disposition if the table doesn't exist.
        :type create_disposition: str

        :param write_disposition: The write disposition if the table already exists.
        :type write_disposition: str

        :param bigquery_conn_id: The connection ID used to connect to Google Cloud Platform and
            interact with the BigQuery service.
        :type bigquery_conn_id: str

        :param google_cloud_storage_conn_id: The connection ID used to connect to Google Cloud
            Platform and interact with the Google Cloud Storage service.
        :type google_cloud_storage_conn_id: str

        :param start_day : the DYNAMIC PART starting point for itterate on bucket urls ( templated )
        :example : 20180101
        :type start_day str

        :param end_day : the DYNAMIC PART ending point for itterate on bucket urls ( templated )
        :example : 20200101
        :type end_day str

    """

    template_fields = (
        "start_day",
        "end_day",
    )

    # Heritage from the default dag args, useful for the retry policy
    @apply_defaults
    def __init__(
        self,
        bucket,
        source_objects_directory,
        source_objects_files,
        destination_project_dataset_table,
        schema_fields,
        source_format,
        create_disposition,
        write_disposition,
        bigquery_conn_id,
        google_cloud_storage_conn_id,
        start_day,
        end_day,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.bucket = bucket

        self.source_objects_directory = source_objects_directory
        self.source_objects_files = source_objects_files
        self.destination_project_dataset_table = destination_project_dataset_table

        self.schema_fields = schema_fields

        self.source_format = source_format
        self.create_disposition = create_disposition
        self.write_disposition = write_disposition

        self.bigquery_conn_id = bigquery_conn_id
        self.google_cloud_storage_conn_id = google_cloud_storage_conn_id

        # Dates Variables
        self.start_day = start_day
        self.end_day = end_day

        # BQ init HOOK
        self.bq_hook = BigQueryHook(
            bigquery_conn_id=bigquery_conn_id,
            delegate_to=None,
            location=None,
        )

        # GCS init HOOK
        self.gcs_hook = GoogleCloudStorageHook(
            google_cloud_storage_conn_id=google_cloud_storage_conn_id,
            delegate_to=None,
        )

    def execute(self, context):

        try:

            datelist = pd.date_range(
                start=datetime.datetime.strptime(self.start_day, "%Y%m%d"),
                end=datetime.datetime.strptime(self.end_day, "%Y%m%d"),
            ).sort_values(ascending=False)

            for date in datelist:

                d = date.strftime("%Y%m%d")

                """
                    Build bucket directory url replacement
                        from:  Facebook/%DATE_VARIABLE%/accounts
                        to  :  Facebook/20180101/accounts
                """

                source_objects_directory = self.source_objects_directory.replace(
                    "%DATE_VARIABLE%", d
                )

                """
                    Destination table replacement
                        from:  tmp_accounts$%DATE_VARIABLE%
                        to  :  tmp_accounts$20180101
                """

                destination_project_dataset_table = (
                    self.destination_project_dataset_table.replace("%DATE_VARIABLE%", d)
                )

                self.sync_in_bq(
                    source_objects_directory=source_objects_directory,
                    source_objects_files=self.source_objects_files,
                    destination_project_dataset_table=destination_project_dataset_table,
                )

        except Exception as err:
            logging.error("Error during Big Query insertion %s: ", err)

    def sync_in_bq(
        self,
        source_objects_directory: str,
        source_objects_files: str,
        destination_project_dataset_table: str,
    ):

        """
        Sync a bucket with Big Query
        """

        try:

            source_uris = [
                f"gs://{self.bucket}/{source_objects_directory}/{source_objects_files}"
            ]

            # Check if there are some files in the bucket
            if self.not_empty(prefix=source_objects_directory):

                logging.info(f"Starting Sync into Big Query from {source_uris}")

                conn = self.bq_hook.get_conn()
                cursor = conn.cursor()

                cursor.run_load(
                    destination_project_dataset_table=destination_project_dataset_table,
                    schema_fields=self.schema_fields,
                    source_uris=source_uris,
                    source_format=self.source_format,
                    create_disposition=self.create_disposition,
                    write_disposition=self.write_disposition,
                    autodetect=False,  # Indicates if we should automatically infer the options and schema for CSV and JSON sources
                    skip_leading_rows=0,  # Number of rows to skip when loading from a CSV
                    field_delimiter=",",  # The delimiter to use when loading from a CSV
                    max_bad_records=0,  # The maximum number of bad records that BigQuery can ignore when running the job
                    quote_character=None,  # The value that is used to quote data sections in a CSV file
                    ignore_unknown_values=True,  # Indicates if BigQuery should allow extra values that are not represented in the table schema
                    allow_quoted_newlines=False,  # Whether to allow quoted newlines (true) or not (false)
                    allow_jagged_rows=False,  # Accept rows that are missing trailing optional columns. The missing values are treated as nulls
                    schema_update_options=(),  # Allows the schema of the destination table to be updated as a side effect of the load job
                    src_fmt_configs=None,  # configure optional fields specific to the source format
                    time_partitioning=None,  # configure optional time partitioning fields
                    cluster_fields=None,  # Request that the result of this load be stored sorted by one or more columns. This is only available in conjunction with time_partitioning
                )

                # SLEEP FOR BQ RATE LIMIT
                time.sleep(0.5)

        except Exception as err:
            logging.error("Error during Big Query insertion %s: ", err)

    def not_empty(self, prefix: str) -> bool:

        """
        Check if the directory contains files

        Return : Boolean
        """

        try:

            files = self.gcs_hook.list(
                bucket=self.bucket, prefix=prefix, delimiter=".json"
            )

            if files:

                logging.info(f"Found : {len(files)} files to sync in {prefix}")

                return True

            else:
                return False

        except Exception as err:
            logging.error("Cannot check if bucket is empty %s: ", err)
