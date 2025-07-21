from dataclasses import dataclass
import shutil
from typing import Any, Callable
from pathlib import Path
import tomlkit
from toolspy.utils import file

import sys
import importlib


BUILD_SCRIPTS_PREFIX = "tools"

class Directories:
    def __init__(self, target: Path, project: "Project"):
        # target
        self.target = target
        self.wheel_file = target / f"{project.name_version}-{project.platform}.whl"
        self.sdist_file = target/ f"{project.name_version}.tgz"

        # target/wheel
        self.wheel = target / project.name_version
        self.wheel_src = self.wheel / "src"
        self.wheel_build_scripts = self.wheel / BUILD_SCRIPTS_PREFIX
        self.wheel_PKG_INFO = self.wheel / "PKG-INFO"

        # target/wheel/{name_version}.dist-info
        self.dist_info = self.wheel / f"{project.name_version}.dist-info"
        self.dist_info_METADATA = self.dist_info / "METADATA"
        self.dist_info_WHEEL = self.dist_info / "WHEEL"
        self.dist_info_RECORD = self.dist_info / "RECORD"

        # target/wheel/{name_version}.data
        self.data = self.wheel / f"{project.name_version}.data"
        self.data_purelib = self.data / "purelib"
        self.data_purelib_src_pth = self.data_purelib / f"__editable__.{project.name_version}.pth"
        self.data_data = self.data / "data"
        self.data_include = self.data / "include"
        self.data_platinclude = self.data / "platinclude"
        self.data_platlib = self.data / "platlib"
        self.data_platstdlib = self.data / "platstdlib"
        self.data_scripts = self.data / "scripts"
        self.data_stdlib = self.data / "stdlib"

        # source
        self.source = Path(".")
        self.source_pyproject_toml = self.source / "pyproject.toml"
        self.source_src = self.source / "src"
        self.source_tools = self.source / "tools"


class Project:
    def __init__(self, target: Path, source: Path):
        pyproject_path = source / "pyproject.toml"
        pyproject = tomlkit.parse(pyproject_path.read_text())

        self.name: str = pyproject["project"]["name"]
        self.version: str = pyproject["project"]["version"]
        self.build_scripts: dict[str, Any] = pyproject.get("tool", {}).get("toolspy", {}).get("build_scripts")

        norm_name = self.name.replace("-", "_")
        norm_version = self.version.replace("-", "_")
        self.name_version = f"{norm_name}-{norm_version}"
        self.platform = "py3-none-any" # TODO: detect platform instead of hardcode

        self.source = source
        self.dirs = Directories(target, self)

    def core_metadata(self):
        yield f"Metadata-Version: 2.4"
        yield f"Name: {self.name}"
        yield f"Version: {self.version}"
        yield f""

    def wheel_metadata(self):
        yield f"Wheel-Version: 1.0"
        yield f"Generator: tools-py"
        yield f"Root-Is-Purelib: true"
        yield f""

    def records(self):
        for path in self.dirs.wheel.rglob("*"):
            if not path.is_file():
                continue
            yield f"{path.relative_to(self.dirs.wheel)},sha256={file.sha256(path)},{path.stat().st_size}"
        yield f"{self.dirs.dist_info.name}/RECORD,,"
        yield f""


    def generate_dist_info(self):
        file.from_iterable(self.dirs.dist_info_METADATA, self.core_metadata())
        file.from_iterable(self.dirs.dist_info_WHEEL, self.wheel_metadata())
        file.from_iterable(self.dirs.dist_info_RECORD, self.records())


    def wheel_archive(self):
        path_without_ext: Callable[[Path], Path] = lambda path: path.with_suffix("")
        archive_name = shutil.make_archive(
            str(path_without_ext(self.dirs.wheel_file)),
            format="zip",
            root_dir=self.dirs.wheel
        )
        wheel_file = shutil.move(
            src=archive_name,
            dst=self.dirs.wheel_file,
        )
        return wheel_file


    def run_build_scripts(self):
        if not self.build_scripts:
            return

        src_path = self.dirs.source.absolute()
        # trg_path = self.dirs.target.absolute()

        sys.path.insert(0, str(src_path))
        for script_name, script_config in self.build_scripts.items():
            module = importlib.import_module(f"{BUILD_SCRIPTS_PREFIX}.{script_name}")
            module.run(self.dirs, script_config)


    # def __init__(self, target: Path, project: Project):
    #     self.target = target
    #     self.work = target / project.name_version
    #     self.data = self.work / f"{project.name_version}.data"
    #     self.dist_info = self.work / f"{project.name_version}.dist-info"
