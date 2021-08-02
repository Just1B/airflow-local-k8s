#!/usr/bin/env bash

: "${AIRFLOW__CORE__FERNET_KEY:=${FERNET_KEY:=$(python -c "from cryptography.fernet import Fernet; FERNET_KEY = Fernet.generate_key().decode(); print(FERNET_KEY)")}}"

export AIRFLOW__CORE__FERNET_KEY

if [ -f /plugins/requirements.txt ]; then pip install -r /plugins/requirements.txt; fi

if [[ "$1" = "webserver" ]]
then

    airflow webserver
fi

if [[ "$1" = "scheduler" ]]
then
    echo "WAITING POSTGRES SERVICE 10 secs "
    
    sleep 10
    
    airflow db init
    
    alembic upgrade heads

    # Add Airflow global Variable here
    # airflow variables -s KEY VALUES
        
    airflow users create --username airflow --lastname airflow --firstname john --email airflow@apache.org --role Admin --password airflow || true

    airflow scheduler
fi
