import subprocess
import os
from pathlib import Path
import shlex
from subprocess import CompletedProcess
import logging

log = logging.getLogger(__name__)


class Env:
    _cwd: Path

    def __init__(self, **kwargs) -> None:
        self.env_vars = {**os.environ, **kwargs}
        self._cwd = Path().absolute()
        self.last_result: CompletedProcess = None

    @property
    def cwd(self) -> Path:
        return self._cwd

    @cwd.setter
    def cwd(self, value: str):
        self._cwd = Path(value)

    def run(
        self,
        *cmds: str,
        input: str = None,
        ignore_errors=None,
        exit_on_first_error=False,
        verbose=False,
    ):
        stdout = ""
        for cmd in cmds:
            log.debug(f"run: '{cmd}'")
            result = subprocess.run(
                shlex.split(cmd),
                input=input,
                encoding="utf-8",
                capture_output=True,
                env=self.env_vars,
                cwd=self._cwd,
            )
            self.last_result = result
            if result.stdout:
                if verbose:
                    print(result.stdout)
                if stdout:
                    stdout += "\n"
                stdout += result.stdout
            if result.stderr and verbose:
                print(result.stderr)
            if not ignore_errors:
                if result.returncode != 0:
                    print(result.stderr)
                result.check_returncode()
            if exit_on_first_error and result.returncode != 0:
                break

        return stdout

    def run_non_block(
        self, cmd: str, ignore_errors=None, exit_on_first_error=False, verbose=False
    ):
        log.debug(f"run: '{cmd}'")
        p = subprocess.Popen(
            shlex.split(cmd),
            encoding="utf-8",
            env=self.env_vars,
            cwd=self._cwd,
        )
        return p
