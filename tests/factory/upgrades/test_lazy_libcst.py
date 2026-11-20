"""libcst is only imported when the dependency-injector action actually runs."""

from __future__ import annotations

import subprocess
import sys


def test_cli_and_registry_do_not_import_libcst() -> None:
    code = (
        "import sys\n"
        "import scaffold_ca_python.cli\n"
        "from scaffold_ca_python.factory.upgrades import UPGRADE_ACTIONS\n"
        "assert UPGRADE_ACTIONS\n"
        "print('libcst' in sys.modules)\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
