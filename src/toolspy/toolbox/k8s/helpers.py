from toolspy.toolbox.k8s.config import K8sConfig
from toolspy.utils.process import Env


def match_labels(item: dict, labels: dict) -> bool:
    item_labels = item.get("metadata", {}).get("labels")
    if not item_labels:
        return False

    for key, value in labels.items():
        if key not in item_labels:
            return False
        if item_labels[key] != value:
            return False

    return True


def env(kubeconfig_name: str = None):
    env = Env()
    if kubeconfig_name:
        k8s_config = K8sConfig.find(kubeconfig_name)
        env.env_vars["KUBECONFIG"] = str(k8s_config.path)
    return env


def apply(manifests: str, namespace: str = None, kubeconfig_name: str = None):
    e = env(kubeconfig_name)
    args = ""
    if namespace:
        args = f"--namespace {namespace}"
    e.run(f"kubectl apply {args} -f -", input=manifests)
