#!/usr/bin/env python

"""
    Author: Justin Baroux
    Email: hello@justinbaroux.com
    Description: Load GoogleSheet Sheet range in a Big Query Partition
    Version: 1.0
"""

import json
import logging
import datetime

import pandas as pd
import numpy as np

from airflow.models import BaseOperator
from airflow.contrib.hooks.bigquery_hook import BigQueryHook

from google.cloud import bigquery
from google.cloud.bigquery import TimePartitioning

# https://airflow.readthedocs.io/en/latest/_modules/airflow/gcp/hooks/discovery_api.html
from hooks.google_discovery_api_hook import GoogleDiscoveryApiHook


class GoogleSheetsToBigQueryOperator(BaseOperator):
    """
    Google Sheets To Big Query Operator

    :param google_conn_id:    The Google connection id.
    :type google_conn_id:     string

    :param sheet_id:          The id for associated report.
    :type sheet_id:           string

    :param sheet_name:       The name for the relevent sheets in the report.
    :type sheet_name:        string/array

    :param range:             The range of of cells containing the relevant data.
                              This must be the same for all sheets if multiple
                              are being pulled together.
                              Example: Sheet1!A2:E80
    :type range:              range

    :param project_id:        Gcp Project ID.
    :type project_id:         string

    :param bq_dataset:        The big query dataset name.
    :type bq_dataset:         string

    :param bq_table:          The big query table name in the dataset.
    :type bq_table:           string

    :param bq_schema_path:    The big query type schema.
    :type bq_schema_path:     Path to the JSON schema

    :param write_disposition:  Big Query write_disposition : https://cloud.google.com/bigquery/docs/reference/auditlogs/rest/Shared.Types/WriteDisposition
    :type write_disposition:   string in ["WRITE_DISPOSITION_UNSPECIFIED", "WRITE_EMPTY", "WRITE_TRUNCATE", "WRITE_APPEND"]

    :param partitioning:       Will indicate if the output table should be partition or not
    :type partitioning:        boolean

    :param parse_dates:        Input columns to be parse as dates by pandas
    :type parse_dates:         list of string
    """

    def __init__(
        self,
        google_conn_id,
        sheet_id,
        bq_schema_path,
        sheet_name,
        range=None,
        project_id=None,
        bq_dataset=None,
        bq_table=None,
        write_disposition="WRITE_APPEND",
        partitioning=True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.google_conn_id = google_conn_id
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        self.range = range

        self.project_id = project_id
        self.bq_dataset = bq_dataset
        self.bq_table = bq_table
        self.bq_schema = self._parse_bq_json_schema(bq_schema_path)
        self.write_disposition = write_disposition

        self.partitioning = partitioning

        # Temp test before reformating
        self.type_schema = self._return_type(bq_schema_path)

        if self.bq_dataset is None:
            raise Exception("Please specify the big query dataset.")

        if self.bq_table is None:
            raise Exception("Please specify the big query destination table.")

        if self.write_disposition not in [
            "WRITE_DISPOSITION_UNSPECIFIED",
            "WRITE_EMPTY",
            "WRITE_TRUNCATE",
            "WRITE_APPEND",
        ]:
            raise Exception("Write Disposition not supported.")

    def _return_type(self, schema_filename):
        types = {}

        switcher = {
            "STRING": str,
            "INTEGER": int,
            "FLOAT": float,
            "DATETIME": "datetime64",
            "DATE": "date",
        }

        with open(schema_filename, "r") as infile:
            json_schema = json.load(infile)

        for field in json_schema:
            name = field["name"]
            field_type = field.get("type", "STRING")

            types[name] = switcher.get(field_type, str)

        return types

    def _get_field_schema(self, field):
        name = field["name"]
        field_type = field.get("type", "STRING")
        mode = field.get("mode", "NULLABLE")
        fields = field.get("fields", ())

        if fields:
            sub_schema = []
            for f in fields:
                fields_res = self._get_field_schema(f)
                sub_schema.append(fields_res)
        else:
            sub_schema = []

        field_schema = bigquery.SchemaField(
            name=name, field_type=field_type, mode=mode, fields=sub_schema
        )

        return field_schema

    def _parse_bq_json_schema(self, schema_filename):
        schema = []
        with open(schema_filename, "r") as infile:
            json_schema = json.load(infile)

        for field in json_schema:
            schema.append(self._get_field_schema(field))

        return schema

    def execute(self, context):

        try:
            logging.info(self.bq_schema)

            # Instanciate the discovery API
            g_conn = GoogleDiscoveryApiHook(
                api_service_name="sheets",
                api_version="v4",
                gcp_conn_id=self.google_conn_id,
            )

            # Build the connection
            sheets_object = g_conn.get_conn()

            response = (
                sheets_object.spreadsheets()
                .get(spreadsheetId=self.sheet_id, includeGridData=True)
                .execute()
            )

            sheets = response.get("sheets")

            final_output = dict()

            total_sheets = []
            for sheet in sheets:
                name = sheet.get("properties").get("title")
                total_sheets.append(name)

                table_name = name
                data = sheet.get("data")[0].get("rowData")
                output = []

                for row in data:
                    row_data = []
                    values = row.get("values")

                    if values is not None:
                        for value in values:
                            ev = value.get("effectiveValue")

                            if ev is None:
                                row_data.append("")
                            else:
                                for v in ev.values():
                                    row_data.append(v)

                    output.append(row_data)

                headers = output.pop(0)
                output = [dict(zip(headers, row)) for row in output]

                final_output[table_name] = output

                logging.info(final_output)

            self.create_file_in_gcs(context, final_output)

        except Exception as err:
            logging.error("Error during Sheet Treatment %s: ", err)

            raise

    def create_file_in_gcs(self, context, data):

        logging.info(f"Starting copy to cloud storage")

        try:

            df = pd.DataFrame(data[self.sheet_name], columns=self.type_schema.keys())

            for types in self.type_schema:

                logging.info(self.type_schema[types])

                if self.type_schema[types] == "date":

                    df[types] = df[types].apply(
                        lambda x: (
                            datetime.datetime(1899, 12, 30)
                            + datetime.timedelta(days=int(x))
                        ).strftime("%Y-%m-%d")
                        if x != ""
                        else x
                    )

                elif self.type_schema[types] == str:
                    df[types] = df[types].astype(str)

            file_obj = f"/home/airflow/gcs/data/{self.bq_dataset}_{self.bq_table}_{context['ds_nodash']}.json"

            df.to_json(file_obj, orient="records", lines=True)

            self.insert_in_big_query(context, file_obj)

        except Exception as err:
            logging.error("Error during Big Query insertion %s: ", err)

            raise

    def insert_in_big_query(self, context, file_obj):

        logging.info(f"Starting insertion in Big Query")

        bq_client = bigquery.Client(project=self.project_id)

        bq_dataset = bq_client.dataset(self.bq_dataset)

        if self.partitioning:
            bq_table = bq_dataset.table(self.bq_table + "$" + context["ds_nodash"])

            job_config = bigquery.LoadJobConfig(
                autodetect=True,
                write_disposition=self.write_disposition,
                schema=self.bq_schema,
                time_partitioning=TimePartitioning(),
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            )
        else:
            bq_table = bq_dataset.table(self.bq_table)

            job_config = bigquery.LoadJobConfig(
                autodetect=True,
                schema=self.bq_schema,
                write_disposition=self.write_disposition,
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            )

        try:

            with open(file_obj, "rb") as source_file:

                job = bq_client.load_table_from_file(
                    file_obj=source_file,
                    destination=bq_table,
                    num_retries=3,
                    job_config=job_config,
                    location="EU",
                )

            """
                Start the job and wait for results
            """
            job.result()

        except Exception as err:
            logging.error("Error during Big Query insertion %s: ", err)

            raise
