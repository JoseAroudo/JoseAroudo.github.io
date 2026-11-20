"""Extract: lee el TOML de contenido y calcula la huella de todas las entradas."""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path


def read(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def fingerprint(*roots: Path) -> str:
    """Hash estable de las entradas. Mismas entradas, mismo run id."""
    digest = hashlib.sha1()
    for root in roots:
        files = [root] if root.is_file() else sorted(
            p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts
        )
        for file in files:
            digest.update(file.as_posix().encode())
            digest.update(file.read_bytes())
    return digest.hexdigest()[:7]
