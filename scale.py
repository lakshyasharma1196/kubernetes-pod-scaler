from kubernetes import client, config
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def create_configmap(deployment_name, namespace, replicas):
    config.load_incluster_config()
    api = client.CoreV1Api()

    metadata = client.V1ObjectMeta(name=f"{deployment_name}-configmap")
    data = {"replicas": str(replicas)}
    body = client.V1ConfigMap(data=data, metadata=metadata)

    api.create_namespaced_config_map(namespace=namespace, body=body)
    logging.info(f"ConfigMap created: {deployment_name}-configmap")

def get_deployments_with_label(label_selector):
    config.load_incluster_config()
    api = client.AppsV1Api()

    deployments = api.list_namespaced_deployment(
        namespace="development",
        label_selector=label_selector
    ).items

    return deployments

def scale_deployment(replicas, deployment_name, namespace):
    config.load_incluster_config()
    api = client.AppsV1Api()

    api.patch_namespaced_deployment_scale(
        name=deployment_name,
        namespace=namespace,
        body={"spec": {"replicas": replicas}}
    )
    logging.info(f"Scaled deployment {deployment_name} in namespace {namespace} to {replicas} replicas")

def delete_configmap(configmap_name, namespace):
    config.load_incluster_config()
    api = client.CoreV1Api()

    api.delete_namespaced_config_map(
        name=configmap_name,
        namespace=namespace,
        body=client.V1DeleteOptions()
    )
    logging.info(f"Deleted ConfigMap: {configmap_name}")

def scale_down_deployments():
    label_selector = "environment=non-production"
    deployments = get_deployments_with_label(label_selector)

    for deployment in deployments:
        deployment_name = deployment.metadata.name
        namespace = deployment.metadata.namespace
        replicas = deployment.spec.replicas

        create_configmap(deployment_name, namespace, replicas)
        scale_deployment(0, deployment_name, namespace)

def scale_up_deployments():
    label_selector = "environment=non-production"
    deployments = get_deployments_with_label(label_selector)

    for deployment in deployments:
        deployment_name = deployment.metadata.name
        namespace = deployment.metadata.namespace

        configmap_name = f"{deployment_name}-configmap"
        configmap = get_configmap(configmap_name, namespace)

        if configmap:
            replicas = int(configmap.data["replicas"])
            if replicas > 0:
                scale_deployment(replicas, deployment_name, namespace)
            delete_configmap(configmap_name, namespace)
        else:
            logging.warning(f"ConfigMap not found for deployment: {deployment_name}")

def get_configmap(configmap_name, namespace):
    config.load_incluster_config()
    api = client.CoreV1Api()

    try:
        configmap = api.read_namespaced_config_map(name=configmap_name, namespace=namespace)
        return configmap
    except client.rest.ApiException as e:
        if e.status == 404:
            return None
        else:
            raise

if __name__ == "__main__":
    # Determine the cron job to execute
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "scale-down":
        logging.info("Scaling down deployments...")
        scale_down_deployments()
    elif len(sys.argv) > 1 and sys.argv[1] == "scale-up":
        logging.info("Scaling up deployments...")
        scale_up_deployments()
    else:
        logging.error("Invalid argument. Specify 'scale-down' or 'scale-up'.")
