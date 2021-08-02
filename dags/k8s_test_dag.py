import logging

from airflow import DAG

from datetime import datetime, timedelta

from kubernetes.client import models as k8s
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

logger = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2021, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(days=1),
}

with DAG(
    "k8s_test_dag",
    default_args=default_args,
    schedule_interval=timedelta(days=1),
    catchup=False,
) as dag:

    pod_test = KubernetesPodOperator(
        name="pod-test-task",
        task_id="pod-test-task",
        namespace="default",
        image="hello-world",
        is_delete_operator_pod=True,
        in_cluster=True,
        get_logs=True,
    )

    pod_test_2 = KubernetesPodOperator(
        name="pod-test-task-2",
        task_id="pod-test-task-2",
        namespace="default",
        image="ubuntu:16.04",
        cmds=["bash", "-cx"],
        arguments=["echo test 1"],
        is_delete_operator_pod=True,
        in_cluster=True,
        get_logs=True,
    )


pod_test >> pod_test_2
