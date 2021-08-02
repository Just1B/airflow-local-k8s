# Presentation

Create a dev environment to test dags in an ephemeral local kube context ( docker-machine or minikube )

## Requirements

- OSX or Linux bash system ( Ubuntu bash may work on windows ) with SED ( Stream Editor )
- Kubectl command line ( alias with microk8s )
- Skaffold https://skaffold.dev/
- Docker intallation + write access in this directory
- An active Kubernetes context ( kube in docker-for-desktop , minikube , microK8s )

## First Deployment

This script will overwrite `logs, dags, plugins` paths in the k8s deployment files 

Build the airflow image, deploy webserver + scheduler + postgres database

Init the database tabkes & create a default user for airflow

```sh
  ./starting.sh
```

## Futur Deployment

If your already generated `k8s/airflow-scheduler.yaml` and `k8s/airflow-webserver.yaml` just :

```sh
  skaffold dev
```

## The Airflow Dashboard

When the airflow deployement is running, open a terminal and get the `EXTERNAL-IP` for the airflow webserver service

    kubectl get svc

Then navigate to `http://{EXTERNAL-IP}:8080`

Default account credentials : 
  - User : `airflow`
  - Password : `airflow`

</br>

![index](/images/dashboard.png)

![index](/images/k8s_test_dag.png)

## Clean all "Status" pod command

You can replace Pending with differentes status :

- For Waiting containers

  - ContainerCreating
  - CrashLoopBackOff
  - ErrImagePull
  - ImagePullBackOff
  - CreateContainerConfigError
  - InvalidImageName
  - CreateContainerError

- For Terminated container

  - OOMKilled
  - Error
  - Completed
  - ContainerCannotRun
  - DeadlineExceeded

```sh
kubectl get pods | grep Pending | awk '{print $1}' | xargs kubectl delete pod
```

## Purge the default namespace

```sh
./scripts/purge.sh
```

## Todo

- [ ] Persist Postgres Database or connect to cloud DB ( cloud sql etc .. )