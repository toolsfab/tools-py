from pathlib import Path
from toolspy.project import Project


if __name__ == "__main__":
    tmp_dir = Path("/tmp/tmp_build_wheel")
    Project.build(tmp_dir, editable=True)
