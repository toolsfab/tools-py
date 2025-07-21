from pathlib import Path
import os


def user_defaults(path: str = "~/.default_env", **envs: dict[str, str]):
    """
    this function meant to be used in shell scripting
    without arguments it returns list of env vars
    with arguments it overrides existing env vars
    Usage:
        # apply user defined env vars to the shell
        source $(toolbox x tools.env.user_defaults)

        # override KUBECONFIG env var
        toolbox x tools.env.user_defaults KUBECONFIG=/root/.kube/new-config
    """
    if not envs:
        return __get_defaults(path)

    __set_defaults(path, **envs)


def __get_defaults(path):
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return

    envs_file = p.read_text()
    for line in envs_file.splitlines():
        line = line.strip()
        if not line:
            continue

        name, value = line.split("=")
        if name in os.environ:
            continue

        print(f"export {name}={value}")


def __set_defaults(path, **envs: dict[str, str]):
    p = Path(path).expanduser().resolve()
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch(exist_ok=True)

    envs_file = p.read_text()
    full_envs = {}
    for line in envs_file.splitlines():
        line = line.strip()
        if not line:
            continue
        name, value = line.split("=")
        full_envs[name] = value

    updated = False
    for name in envs:
        if name not in full_envs:
            full_envs[name] = envs[name]
            updated = True
            continue
        if full_envs[name] != envs[name]:
            full_envs[name] = envs[name]
            updated = True
            continue

    if updated:
        envs_text = "\n".join([f"{name}={value}" for name, value in full_envs.items()])
        envs_text += "\n"
        p.write_text(envs_text)
