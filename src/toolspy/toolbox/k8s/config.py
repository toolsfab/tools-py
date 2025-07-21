from toolspy.utils.process import Env
from pathlib import Path
from dataclasses import dataclass
from typing import Iterator


KUBECONFIG_DIR = Path("~/.kube/config.d").expanduser()
FOLDERS_TO_SEARCH = [
    Path("~/.kube/config.d"),
    Path("~/.kube/"),
    Path("."),
]


@dataclass
class K8sConfig:
    path: Path

    @classmethod
    def from_config_name(cls, name: str) -> "K8sConfig":
        return K8sConfig(path=KUBECONFIG_DIR / name)

    @classmethod
    def find(cls, name: str) -> "K8sConfig":
        for folder in FOLDERS_TO_SEARCH:
            kubeconfig = folder.expanduser().absolute() / name
            if kubeconfig.exists():
                return K8sConfig(path=kubeconfig)
        raise RuntimeError(f"cannot find kubeconfig '{name}'")
    
    @classmethod
    def find_all(cls) -> Iterator["K8sConfig"]:
        for kubeconfig in KUBECONFIG_DIR.iterdir():
            yield K8sConfig(path=kubeconfig)

    @property
    def name(self) -> str:
        return self.path.name
    
    def env(self):
        env = K8sEnv(KUBECONFIG=str(self.path))
        return env

    def rename_current_context(self, new_name: str):
        k8s_env = self.env()

        current_context = k8s_env.kubectl("config current-context").strip()
        k8s_env.kubectl(f"config rename-context {current_context} {new_name}")


class K8sEnv(Env):
    namespace: str = None

    def kubectl(self, args: str, **kwargs):
        if self.namespace:
            args = f"--namespace {self.namespace} {args}"
        return self.run(f"kubectl {args}", **kwargs)

    def apply(self, manifests: str):
        self.kubectl(f"apply -f -", input=manifests)

