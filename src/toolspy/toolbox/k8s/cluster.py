"""functions in this module helps to manage multiple k8s clusters"""
from pathlib import Path
from toolspy.toolbox import ssh
from toolspy.toolbox.k8s.config import K8sConfig
from toolspy.toolbox.k8s.helpers import env as k8s_env
from subprocess import CalledProcessError
from toolspy.utils.tasks import run_in_parallel
from functools import partial
from time import time
from typing import Iterable, Tuple


import logging
log = logging.getLogger(__name__)


def add(name: str, ip: str):
    """
    make cluster accessible via ssh and kubectl

    it is assumed that you have installed a new k8s cluster
    and you have the IP address of the master
    on which there is a k8s config (located in ~/.kube/config)

    this function tries to
    - add a new ssh host (see `ssh.add_host`)
    - copy the k8s config via scp

    Args:
        name: easy to remember name (don't use spaces)
        ip: master ip
    """
    log.info(f"adding new k8s master <{name} {ip}> to ssh config")
    ssh.add_host(name, ip)

    log.info(f"coping k8s config from {name} host")

    k8s_config = K8sConfig.from_config_name(name)
    ssh.scp(f"{name}:~/.kube/config", str(k8s_config.path))
    k8s_config.path.chmod(0o600)
    k8s_config.rename_current_context(name)


def delete(name: str):
    """
    delete ssh and k8s config of previously added cluster
    """
    ssh.delete_host(name)
    K8sConfig.from_config_name(name).path.unlink()
    log.info(f"k8s config '{name}' deleted")


def check(k8s_cfg: K8sConfig, timeout: int):
    """check if cluster is available"""
    cmd = (
        f"kubectl version "
        f"--output yaml "
        f"--request-timeout={timeout}s "
    )
    try:
        k8s_cfg.env().run(cmd)
    except CalledProcessError:
        return (k8s_cfg, False)
    return (k8s_cfg, True)


def cleanup(timeout: int = 10):
    """
    check if there are unavailable clusters.
    if there are, suggest removing them
    """
    check_funcs = [
        partial(check, k8s_cfg, timeout)
        for k8s_cfg in K8sConfig.find_all()
    ]
    clusters_availability, _ = run_in_parallel(check_funcs)

    k8s_cfg: K8sConfig
    non_working_k8s_configs = [
        k8s_cfg
        for k8s_cfg, is_working in clusters_availability
        if not is_working
    ]
    if not non_working_k8s_configs:
        log.info("all clusters are available")
        return
    do_cleanup = False
    if non_working_k8s_configs:
        print(f"The following clusters didn't respond within {timeout} seconds:")
        for k8s_cfg in non_working_k8s_configs:
            print(f" {k8s_cfg.name}")
        print()
        # TODO: formerly, this was rich.prompt.Confirm
        # needs to be replaced with built-in `input()`
        answer = input("Do you want to remove them? [y/n]")
        do_cleanup = answer == "y"
    if do_cleanup:
        for k8s_cfg in non_working_k8s_configs:
            delete(k8s_cfg.name)


    #     try:
    #         check(config_name)
    #     except CalledProcessError:
    #         non_working_clusters.append(config_name)
    # for cluster in non_working_clusters:
    #     print(f"removing {cluster}")
