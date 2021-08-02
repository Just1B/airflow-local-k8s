#!/usr/bin/env bash

# set -x

# ****************************************************************************
#                                                                             
#                 CREATE THE DEV ENVIRONMENT IN DEFAULT NAMESPACE                                    
#                                                                             
# ****************************************************************************

export DIRNAME=$(cd "$(dirname "$0")" || exit 1; pwd)

export TEMPLATE_DIRNAME="${DIRNAME}/templates"

export DAGS_VOLUMES="${DIRNAME}/dags"
export LOGS_VOLUMES="${DIRNAME}/logs"
export PLUGINS_VOLUMES="${DIRNAME}/plugins"

_UNAME_OUT=$(uname -s)
case "${_UNAME_OUT}" in
    Linux*)     _MY_OS=linux;;
    Darwin*)    _MY_OS=darwin;;
    *)          echo "${_UNAME_OUT} is unsupported."
                exit 1;;
esac

case ${_MY_OS} in
  linux)
    SED_COMMAND="sed"
  ;;

  darwin)
    SED_COMMAND="gsed"
    if ! type "${SED_COMMAND}" &> /dev/null ; then
      echo "Could not find \"${SED_COMMAND}\" binary, please install it. On OSX brew install gnu-sed" >&2
      exit 1
    fi
  ;;
  *)
    echo "${_UNAME_OUT} is unsupported."
    exit 1
  ;;
esac

for file in {"airflow-webserver.yaml","airflow-scheduler.yaml"}
do
  
  OUTPUT=${DIRNAME}/k8s/$file

  # Check if weberserve or scheduler deployments files exist
  if test -f "$OUTPUT"; then
    rm $OUTPUT
  fi

  echo "Processing $file file ..."

  cp $TEMPLATE_DIRNAME/$file $OUTPUT

  ${SED_COMMAND} -i "s|{ { DAGS_VOLUMES } }|${DAGS_VOLUMES}|g" "$OUTPUT"
  ${SED_COMMAND} -i "s|{ { LOGS_VOLUMES } }|${LOGS_VOLUMES}|g" "$OUTPUT"
  ${SED_COMMAND} -i "s|{ { PLUGINS_VOLUMES } }|${PLUGINS_VOLUMES}|g" "$OUTPUT"
done

skaffold dev --tail