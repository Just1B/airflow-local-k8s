#!/usr/bin/env bash

# ****************************************************************************
#                                                                             
#                         RESET THE DEFAULT NAMESPAE                                    
#                                                                             
# ****************************************************************************

export CURRENT_CONTEXT=$(kubectl config current-context)

GREEN='\033[0;32m'

YELLOW='\033[1;33m'

NOCOLOR='\033[0m'

DOCKER_IMAGE='airflow'

printf "\n\n${YELLOW}‼️   WARNING THIS SCRIPT WILL PURGE YOUR DEFAULT NAMESPACE FOR ${CURRENT_CONTEXT} ‼️  ${NOCOLOR}\n\n"

sleep 1

echo -n -e "${YELLOW}ARE YOUR SURE ( y / n ) ? ${NOCOLOR}"

read answer

if [ "$answer" != "${answer#[Yy]}" ] ;then

    printf "\n\n${GREEN} ** Starting the purge, may take some time ** \n\n${NOCOLOR}"

    kubectl get pods -n default | awk '{ if( NR > 1 ) print $1 }' | xargs kubectl delete pods

    kubectl get deployments -n default | awk '{ if( NR > 1 ) print $1 }' | xargs kubectl delete deployments

    kubectl get services -n default | awk '{ if( NR > 1 ) print $1 }' | xargs kubectl delete services

    # kubectl get secrets -n default | awk '{ if( NR > 1 ) print $1 }' | xargs kubectl delete secrets
    
    kubectl get pvc -n default | awk '{ if( NR > 1 ) print $1 }' | xargs kubectl delete pvc

    kubectl get pv -n default | awk '{ if( NR > 1 ) print $1 }' | xargs kubectl delete pv

    kubectl get cm -n default | awk '{ if( NR > 1 ) print $1 }' | xargs kubectl delete cm

    printf "\n\n${GREEN} ** Deleting the local image build ** \n\n${NOCOLOR}"

    docker images ${DOCKER_IMAGE} | awk '{ if( NR > 1 ) print $3 }' | xargs docker rmi '$3'

    yes | docker system prune

    printf "\n\n${GREEN} ** Done, Your are good to go ** \n\n${NOCOLOR}"

fi