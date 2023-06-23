# kubernetes-pod-scaler
This script provides a solution for scaling down and scaling up Kubernetes deployments in a specific namespace. It uses a ConfigMap to store the replica values of the deployments and restores them when scaling up

## Prerequisites

- Python 3.x
- `kubernetes` Python package (`pip install kubernetes`)

## Usage

Create service account 

```kubectl create serviceaccount deployment-scaler -n namespace```


1. Clone the repository and navigate to the project directory:

   ```
   git clone https://github.com/your-username/kubernetes-deployment-scaler.git
   cd kubernetes-deployment-scaler
   ```

2. Configure the Kubernetes cluster access. Make sure you have the necessary permissions to manage deployments and config maps in the target namespace.

3. Modify the script as per your requirements:

Update the label selector in the `scale_down_deployments` and `scale_up_deployments` functions to match the deployments you want to scale.
Run the script with the appropriate argument to perform the desired action:

To scale down the deployments:


```python scaler.py scale-down```

To scale up the deployments and restore replica values from the ConfigMap:

```python scaler.py scale-up```

Check the script logs to monitor the scaling actions and any warnings or errors.

# How It Works

The script follows the following steps:

1. Fetches the deployments in the specified namespace based on a label selector.
2. For scaling down:
Creates a ConfigMap for each deployment, storing the current replica value.
Scales down the deployments to zero replicas.
3. For scaling up:
Retrieves the replica values from the ConfigMap created during the scaling down step.
4. Scales up the deployments to their original replica values.
5. Deletes the ConfigMap after successful scaling up.

Note: Make sure to adjust the label selector and any other parameters to match your deployment and namespace setup.

For advanced use-case please consider the advance folder
which contains more complex scripts for handeling hpa (scaledobject Keda) that can be used together with this one. 
