"""SHA-256 fingerprints of unmodified 0.5.0 scaffold outputs."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

COMPOSITION_CANDIDATES = (
    "main.py",
    "application/app.py",
    "application/generic_app.py",
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_starter_main(path: Path) -> bool:
    """True when main matches the default 0.5.0 hello-world entrypoint."""
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if "dependency_injector" in text or "Container(" in text:
        return False
    return bool(re.search(r"def main\(\)\s*->\s*None:", text)) and 'print("Hello, World!")' in text


def composition_root_status(path: Path) -> str:
    """Return 'starter', 'modified', or 'missing'."""
    if not path.is_file():
        return "missing"
    if is_starter_main(path):
        return "starter"
    if "dependency_injector" in path.read_text(encoding="utf-8"):
        return "modified"
    return "modified"
