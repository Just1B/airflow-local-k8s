FROM python:slim

# install deps
RUN apt-get update -y && apt-get install -y \
    wget \
    libczmq-dev \
    curl \
    libssl-dev \
    libffi-dev \
    git \
    libpq-dev \
    inetutils-telnet \
    bind9utils \
    zip \
    unzip \
    gcc \
    && apt-get clean

# RUN pip install --upgrade pip

# Since we install vanilla Airflow, we also want to have support for Postgres and Kubernetes
RUN pip install -U setuptools && \
    pip install GitPython && \
    pip install kubernetes && \
    pip install cryptography && \
    pip install psycopg2-binary && \
    pip install apache-airflow[gcp,celery,postgres,kubernetes,redis]

WORKDIR /root/airflow

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY bootstrap.sh /bootstrap.sh
RUN chmod +x /bootstrap.sh

ENTRYPOINT ["/bootstrap.sh"]
