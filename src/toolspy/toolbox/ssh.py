"""
SSH related functions

apart of handy CLI tools for managing SSH configs
this module also providing wrappers around scp and ssh commands
which are simplifies python scripting 
"""
from pathlib import Path
from toolspy.utils import process
import os
import logging

log = logging.getLogger(__name__)

SSH_BASE_PATH = Path("~/.ssh/config.d").expanduser()
SSH_USER = os.environ.get("TOOLBOX_SSH_USER", "root")
# TODO: raise Runtime exception if password didn't set
SSH_PASSWORD = os.environ.get("TOOLBOX_SSH_PASSWORD", "none") 
SSH_TEMPLATE = """\
Host {name}
    HostName {ip}
    User {user}
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
    LogLevel ERROR
    ControlMaster auto
    ControlPath ~/.ssh/ssh_mux_%h_%p_%r
    ControlPersist 600
"""


def add_host(name: str, ip: str):
    SSH_BASE_PATH.mkdir(parents=True, exist_ok=True)
    ssh_path = SSH_BASE_PATH / name
    ssh_path.write_text(SSH_TEMPLATE.format(
        name=name,
        user=SSH_USER,
        ip=ip,
    ))

    env = process.Env(SSHPASS=SSH_PASSWORD)
    env.run(f"sshpass -e ssh-copy-id -F {ssh_path.absolute()} {name}")
    log.info(f"ssh host '{name}/{ip}' added")


def delete_host(name: str):
    ssh_path = SSH_BASE_PATH / name
    if ssh_path.exists():
        ssh_path.unlink()
    log.info(f"ssh host '{name}' deleted")


def scp(source: str, target: str):
    *target_host, target_path_str = target.split(":", maxsplit=1)
    target_path = Path(target_path_str)
    if target_host:
        log.debug("make sure that target folder exists on remote machine")
        target_host = target_host[0]
        process.run(f"ssh {target_host} mkdir -p {target_path.parent}")
    else:
        log.debug("make sure that target folder exists on local machine")
        target_path.parent.mkdir(exist_ok=True, parents=True)
    process.run(f"scp {source} {target}")


def run(host: str, cmd_str: str):
    process.run(f"ssh {host} {cmd_str}")
