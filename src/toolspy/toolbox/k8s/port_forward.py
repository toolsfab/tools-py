from toolspy.utils.process import Env
import yaml
from pathlib import Path
from dataclasses import dataclass
from subprocess import Popen
from time import sleep
import logging

log = logging.getLogger(__name__)


@dataclass
class PortForwardConf:
    endpoint: str
    namespace: str
    port: int
    localPort0: int
    kubeconfig: str = None


@dataclass
class Pod:
    name: str
    namespace: str
    port: int
    localPort: int = None

    @classmethod
    def from_config(cls, config: PortForwardConf, env: Env = None):
        if not env:
            env = Env()
        endpoint_yaml = env.run(
            f"kubectl get endpoints -n {config.namespace} {config.endpoint} -o yaml"
        )
        endpoint = yaml.safe_load(endpoint_yaml)
        pods: list["Pod"] = []
        for subset in endpoint["subsets"]:
            ports = subset["ports"]
            if len(ports) != 1:
                log.warning(
                    f"Endpoint {config.namespace}/{config.name}: expected only one port, but got {len(ports)}"
                )
            port = ports[0]["port"]
            for address in subset["addresses"]:
                target_ref = address.get("targetRef", {})
                if target_ref.get("kind") != "Pod":
                    log.warning(
                        f"Endpoint {config.namespace}/{config.name}: address targetRef kind is not 'Pod'"
                    )
                    continue
                pod = cls(
                    name=target_ref["name"],
                    namespace=config.namespace,
                    port=port,
                )
                pods.append(pod)
        pods.sort(key=lambda pod: pod.name)
        for index, pod in enumerate(pods):
            pod.localPort = config.localPort0 + index
        return pods


def parse_port_forward_config(name: str) -> PortForwardConf:
    toolbox_conf_file = Path("toolbox.yaml").absolute()
    if not toolbox_conf_file.exists():
        raise FileNotFoundError(f"toolbox.yaml not found: {toolbox_conf_file}")

    toolbox_conf = yaml.safe_load(toolbox_conf_file.read_text())
    ports_forward_conf = toolbox_conf.get("kube", {}).get("port-forward", {})
    if not ports_forward_conf:
        raise ValueError(f"port-forward config not found in {toolbox_conf_file} file")

    ps_f_conf: dict[str, PortForwardConf] = {}
    for pf_name, pf_conf in ports_forward_conf.items():
        ps_f_conf[pf_name] = PortForwardConf(**pf_conf)
        ps_f_conf[pf_name].name = pf_name

    return ps_f_conf[name]


def port_forward(name: str = None, tag: str = None):
    port_forward_config = parse_port_forward_config(name)
    env = Env()
    if port_forward_config.kubeconfig:
        kubeconfig = Path(port_forward_config.kubeconfig)
        kubeconfig = kubeconfig.expanduser().absolute()
        print(f"Using kubeconfig: {kubeconfig}")
        env.env_vars["KUBECONFIG"] = str(kubeconfig)
    pods = Pod.from_config(port_forward_config, env)

    processes: dict[str, Popen] = {}
    while True:
        for pod in pods:
            if pod.name not in processes or processes[pod.name].poll() is not None:
                processes[pod.name] = env.run_non_block(
                    f"kubectl port-forward -n {pod.namespace} {pod.name} {pod.localPort}:{pod.port}"
                )
        sleep(0.1)
