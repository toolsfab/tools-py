from pathlib import Path
import shutil
import hashlib
import base64
from contextlib import contextmanager
from collections.abc import Iterable
import httpx


def sha256(path: Path, blocksize=65536):
    """calculate sha256 of given file"""
    sha = hashlib.sha256()
    hashlib.sha256()
    with path.open("rb") as file:
        file_buffer = file.read(blocksize)
        while len(file_buffer) > 0:
            sha.update(file_buffer)
            file_buffer = file.read(blocksize)
    encoded_digest = base64.urlsafe_b64encode(sha.digest()).decode().strip("=")
    return encoded_digest


def from_iterable(path: Path, lines: Iterable[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


@contextmanager
def temp_dir(dir_path: Path):
    """create clean dir and remove at the end"""
    shutil.rmtree(dir_path, ignore_errors=True)
    dir_path.mkdir(parents=True)
    try:
        yield
    finally:
        shutil.rmtree(dir_path)


def download(url: str, path: Path):
    """Download a file from URL to local path

    Args:
        url: file URL to download
        path: local path to save file
    """
    with httpx.Client() as client:
        with client.stream("GET", url, follow_redirects=True) as response:
            response.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)