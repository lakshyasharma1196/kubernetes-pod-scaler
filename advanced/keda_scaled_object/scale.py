import time
from kubernetes import client, config
import kubernetes.client.exceptions as k8s_exceptions
from kubernetes.client.exceptions import ApiException


import logging

KEDA_GROUP = "keda.sh"


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def create_configmap(deployment_name, namespace, scaled_object, replicas):
    config.load_incluster_config()
    api = client.CoreV1Api()

    configmap_name = f"{deployment_name}-configmap"
    metadata = client.V1ObjectMeta(name=configmap_name)
    data = {"scaled_object": str(scaled_object), "replicas": str(replicas)}
    body = client.V1ConfigMap(data=data, metadata=metadata)

    try:
        api.create_namespaced_config_map(namespace=namespace, body=body)
        logging.info(f"ConfigMap created: {configmap_name}")
    except ApiException as e:
        if e.status == 409:
            logging.warning(f"ConfigMap {configmap_name} already exists. Skipping creation.")
        else:
            logging.error(f"Error creating ConfigMap: {e}")




def get_deployments_with_label(label_selector, namespace):
    config.load_incluster_config()
    api = client.AppsV1Api()

    deployments = api.list_namespaced_deployment(
        namespace=namespace,
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

def delete_scaled_object(deployment_name, namespace):
    config.load_incluster_config()
    api = client.CustomObjectsApi()

    api.delete_namespaced_custom_object(
        group=KEDA_GROUP,
        version="v1alpha1",
        namespace=namespace,
        plural="scaledobjects",
        name=deployment_name,
        body=client.V1DeleteOptions()
    )
    logging.info(f"Deleted ScaledObject: {deployment_name}")

def scale_down_deployments(namespace):
    label_selector = "environment=non-production"
    deployments = get_deployments_with_label(label_selector, namespace)

    for deployment in deployments:
        deployment_name = deployment.metadata.name
        namespace = deployment.metadata.namespace
        replicas = deployment.spec.replicas
        scaled_object = get_scaled_object(deployment_name, namespace)
        if scaled_object:
            create_configmap(deployment_name, namespace, scaled_object, replicas)
            delete_scaled_object(deployment_name, namespace)
            time.sleep(5)
            scale_deployment(0, deployment_name, namespace)
        else:
            create_configmap(deployment_name, namespace, None, replicas)
            scale_deployment(0, deployment_name, namespace)
            logging.warning(f"Scaled object not found for deployment: {deployment_name}")


def scale_up_deployments(namespace):
    label_selector = "environment=non-production"
    deployments = get_deployments_with_label(label_selector, namespace)

    for deployment in deployments:
        deployment_name = deployment.metadata.name
        namespace = deployment.metadata.namespace

        configmap_name = f"{deployment_name}-configmap"
        configmap = get_configmap(configmap_name, namespace)

        if configmap:
            scaled_object = eval(configmap.data.get("scaled_object", ""))
            replicas = scaled_object.get("spec", {}).get("minReplicaCount", 0) if scaled_object else int(configmap.data.get("replicas", 0))
            if replicas > 0:
                scale_deployment(replicas, deployment_name, namespace)
            try:
                create_scaled_object(scaled_object, namespace)  # Create the scaled object back using the saved configuration
            except k8s_exceptions.ApiException as e:
                logging.warning(f"Scaled object already exists for deployment: {deployment_name}")
                delete_configmap(configmap_name, namespace)
                continue
            delete_configmap(configmap_name, namespace)
        else:
            replicas = 0  # Set a default value for replicas when configmap is None
            if replicas > 0:
                scale_deployment(replicas, deployment_name, namespace)
            logging.warning(f"ConfigMap not found for deployment: {deployment_name}")

def create_scaled_object(scaled_object, namespace):
    if scaled_object is not None:
        config.load_incluster_config()
        api = client.CustomObjectsApi()

        if "resourceVersion" in scaled_object.get("metadata", {}):
            del scaled_object["metadata"]["resourceVersion"]

        api.create_namespaced_custom_object(
            group=KEDA_GROUP,
            version="v1alpha1",
            namespace=namespace,
            plural="scaledobjects",
            body=scaled_object
        )
        logging.info(f"Scaled object created: {scaled_object['metadata']['name']}")
    else:
        logging.warning("Scaled object is None. Skipping creation.")





def get_scaled_object(deployment_name, namespace):
    config.load_incluster_config()
    api = client.CustomObjectsApi()

    try:
        scaled_object = api.get_namespaced_custom_object(
            group=KEDA_GROUP,
            version="v1alpha1",
            namespace=namespace,
            plural="scaledobjects",
            name=deployment_name
        )
        return scaled_object
    except client.rest.ApiException as e:
        if e.status == 404:
            return None
        else:
            raise

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
    if len(sys.argv) > 2 and sys.argv[1] == "scale-down":
        namespace = sys.argv[2]
        logging.info(f"Scaling down deployments in namespace {namespace}...")
        scale_down_deployments(namespace)
    elif len(sys.argv) > 2 and sys.argv[1] == "scale-up":
        namespace = sys.argv[2]
        logging.info(f"Scaling up deployments in namespace {namespace}...")
        scale_up_deployments(namespace)
    else:
        logging.error("Invalid argument. Specify 'scale-down' or 'scale-up'.")
