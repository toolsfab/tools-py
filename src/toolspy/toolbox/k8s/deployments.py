from toolspy.toolbox.k8s.config import K8sConfig
import yaml
from pathlib import Path

DEPLOYMENTS_PATH = Path("deployments.yaml")

def store(config_name: str, namespace: str):
    k8s_env = K8sConfig.from_config_name(config_name).env()
    k8s_env.namespace = namespace
    
    # collect replicas info
    replicas_info = {}
    deployments = yaml.safe_load(k8s_env.kubectl("get deployments -o yaml"))
    for deployment in deployments["items"]:
        name = deployment["metadata"]["name"]
        replicas = deployment["spec"]["replicas"]
        replicas_info[name] = replicas

    # load deployments info if exists
    deployments_info = {}
    if DEPLOYMENTS_PATH.exists():
        deployments_info = yaml.safe_load(DEPLOYMENTS_PATH.read_text())

    # update deployments info
    deployments_info[namespace] = replicas_info
    DEPLOYMENTS_PATH.write_text(yaml.dump(deployments_info))
    # breakpoint()

def scale_down(config_name: str, namespace: str):
    k8s_env = K8sConfig.from_config_name(config_name).env()
    k8s_env.namespace = namespace

    deployments_info = yaml.safe_load(DEPLOYMENTS_PATH.read_text())
    replicas_info: dict[str, int] = deployments_info[namespace]

    for deployment, replicas in replicas_info.items():
        k8s_env.kubectl(f"scale deployment {deployment} --replicas=0")

def scale_up(config_name: str, namespace: str):
    k8s_env = K8sConfig.from_config_name(config_name).env()
    k8s_env.namespace = namespace

    deployments_info = yaml.safe_load(DEPLOYMENTS_PATH.read_text())
    replicas_info: dict[str, int] = deployments_info[namespace]

    for deployment, replicas in replicas_info.items():
        k8s_env.kubectl(f"scale deployment {deployment} --replicas={replicas}")