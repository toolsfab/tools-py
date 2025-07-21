from pathlib import Path
import shutil
import sys
import importlib


REQUIREMENTS = ["tomlkit", "httpx"]
IGNORE_SRC_PATTERNS = ("__pycache__", "*.pyc")


def _get_requires(settings: dict = None):
    return REQUIREMENTS

get_requires_for_build_wheel = _get_requires
get_requires_for_build_sdist = _get_requires
get_requires_for_build_editable = _get_requires


def build_sdist(wheel_dir: str, settings: dict = None, metadata_dir: str = None):
    from toolspy.project.project import Project
    from toolspy.utils import file

    sdist_path: Path = None
    project = Project(Path(wheel_dir), Path())

    with file.temp_dir(project.dirs.wheel):
        # SOURCE
        shutil.copy(project.dirs.source_pyproject_toml, project.dirs.wheel)
        if project.dirs.source_src.exists():
            shutil.copytree(
                project.dirs.source_src,
                project.dirs.wheel_src,
                ignore=shutil.ignore_patterns(*IGNORE_SRC_PATTERNS)
            )
        for build_script_name in project.build_scripts.keys():
            script_path = project.dirs.source_tools / f"{build_script_name}.py"
            if not script_path.exists():
                raise RuntimeError(f"cannot find {build_script_name} in 'tools' folder")
            project.dirs.wheel_build_scripts.mkdir(exist_ok=True, parents=True)
            shutil.copy(script_path, project.dirs.wheel_build_scripts)

        # METADATA
        file.from_iterable(project.dirs.wheel_PKG_INFO, project.core_metadata())

        # PACKAGE
        sdist_path_str = shutil.make_archive(
            str(project.dirs.sdist_file.with_suffix("").absolute()),
            format="gztar",
            root_dir=project.dirs.target,
            base_dir=project.dirs.wheel.name,
        )
        sdist_path = Path(sdist_path_str)

    return sdist_path.name


def build_editable(wheel_dir: str, settings: dict = None, metadata_dir: str = None):
    return _build_wheel(wheel_dir, editable=True)


def build_wheel(wheel_dir: str, settings: dict = None, metadata_dir: str = None):
    return _build_wheel(wheel_dir, editable=False)

def _build_wheel(wheel_dir: str, editable: bool):
    from toolspy.project.project import Project
    from toolspy.utils import file

    wheel_path: Path = None
    project = Project(Path(wheel_dir), Path())

    with file.temp_dir(project.dirs.wheel):
        if editable:
            # put link to project's src folder
            src_pth = project.dirs.data_purelib_src_pth
            src_pth.parent.mkdir(parents=True, exist_ok=True)
            src_pth.write_text(str(project.dirs.source_src.absolute()))
        else:
            if project.dirs.source_src.exists():
                shutil.copytree(project.dirs.source_src, project.dirs.data_purelib)

        project.run_build_scripts()
        project.generate_dist_info()

        # PACKAGE
        wheel_path = project.wheel_archive()

    return wheel_path.name
