from dataclasses import dataclass, asdict
import yaml
from toolspy.toolbox import k8s
from collections import defaultdict
import logging

log = logging.getLogger(__name__)


@dataclass
class Address:
    hostname: str
    ip: str


@dataclass
class Port:
    name: str
    port: int
    protocol: str

    def __hash__(self) -> int:
        return hash((self.port, self.protocol))


@dataclass
class Subset:
    addresses: list[Address]
    ports: set[Port]

    @classmethod
    def from_services(cls, services: list):
        subset = cls(addresses=[], ports=set())
        ports = set()
        for service in services:
            address = Address(
                hostname=service["metadata"]["name"],
                ip=service["spec"]["clusterIP"],
            )
            subset.addresses.append(address)
            for port in service["spec"]["ports"]:
                subset.ports.add(
                    Port(
                        name=port["name"],
                        port=port["port"],
                        protocol=port["protocol"],
                    )
                )
        return subset

    @classmethod
    def from_dict(cls, subset_dict: dict):
        subset = cls(addresses=[], ports=set())
        subset.addresses = [
            Address(hostname=address.get("hostname"), ip=address.get("ip"))
            for address in subset_dict.get("addresses", [])
        ]
        subset.ports = set(
            Port(
                name=port.get("name"),
                port=port.get("port"),
                protocol=port.get("protocol"),
            )
            for port in subset_dict.get("ports", [])
        )
        return subset

    def __comparable_value(self) -> set:
        value = set()
        for address in self.addresses:
            value.add((address.hostname, address.ip))
        for port in self.ports:
            value.add((port.port, port.protocol))
        return value

    def __eq__(self, other: "Subset") -> bool:
        return self.__comparable_value() == other.__comparable_value()


@dataclass
class Endpoint:
    name: str
    namespace: str
    subsets: list[Subset]

    def __str__(self) -> str:
        endpoints = {
            "apiVersion": "v1",
            "kind": "Endpoints",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace,
            },
            "subsets": [asdict(subset) for subset in self.subsets],
        }
        return yaml.dump(endpoints)

    @classmethod
    def list(cls, namespace: str, kubeconfig_name: str = None):
        env = k8s.helpers.env(kubeconfig_name)
        endpoints_yaml = env.run(
            f"kubectl --namespace {namespace} get endpoints -o yaml"
        )
        endpoints_list = yaml.safe_load(endpoints_yaml)["items"]
        endpoints = {}
        for endpoint in endpoints_list:
            name = endpoint["metadata"]["name"]
            subsets = [
                Subset.from_dict(subset) for subset in endpoint.get("subsets", [])
            ]
            endpoints[name] = Endpoint(
                name=name,
                namespace=namespace,
                subsets=subsets,
            )
        return endpoints


def services_with_labels(namespace: str, labels: dict, kubeconfig_name: str = None):
    env = k8s.helpers.env(kubeconfig_name)
    services_yaml = env.run(f"kubectl --namespace {namespace} get services -o yaml")
    services = yaml.safe_load(services_yaml)
    sub_services = []
    for service in services["items"]:
        if k8s.helpers.match_labels(service, labels):
            sub_services.append(service)
    return sub_services


def update_multi_cluster_proxy_endpoints(namespace: str, kubeconfig_name: str = None):
    labels = {
        "app.kubernetes.io/part-of": "multi-cluster-proxy",
    }
    proxy_services = services_with_labels(namespace, labels, kubeconfig_name)
    if not proxy_services:
        log.info(f"No services found in {namespace} with labels: {labels}")
        return
    grouped_services = defaultdict(list)
    for service in proxy_services:
        component = (
            service["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        )
        if not component:
            log.warning(
                f"Service {service['metadata']['name']} has no component label. Skipping"
            )
            continue
        grouped_services[component].append(service)

    existing_endpoints = Endpoint.list(namespace, kubeconfig_name)
    endpoints = []
    for service_name, services in grouped_services.items():
        subset = Subset.from_services(services)
        endpoint = Endpoint(
            name=service_name,
            namespace=namespace,
            subsets=[subset],
        )

        if service_name not in existing_endpoints:
            log.info(f"Endpoint {namespace}/{service_name} not found. Creating")
            endpoints.append(endpoint)
            continue

        existing_endpoint = existing_endpoints[service_name]
        if len(existing_endpoint.subsets) > 1:
            log.warning(
                f"Endpoint {namespace}/{service_name} has more than one subset. Skipping"
            )
            continue

        current_subset = existing_endpoint.subsets[0]
        if subset != current_subset:
            log.info(f"Endpoint {namespace}/{service_name} is outdated. Updating")
            endpoints.append(endpoint)
            continue

        log.info(f"Endpoint {namespace}/{service_name} is up-to-date. Nothing to do")

    endpoints_manifest = "---".join(map(str, endpoints))
    if not endpoints_manifest:
        log.info("No endpoints to apply")
        return

    k8s.helpers.apply(endpoints_manifest, namespace, kubeconfig_name)

