"""Add @wireup.injectable to legacy driven adapters."""

from __future__ import annotations

import re


def injectable_transform(content: str) -> tuple[str, bool]:
    """Return updated source and whether a decorator was added."""
    if "@injectable" in content or "@wireup.injectable" in content:
        return content, False
    if not re.search(r"^class\s+\w+", content, re.MULTILINE):
        return content, False
    gateway_match = re.search(r"from\s+[\w.]+\.gateways\.(\w+)\s+import\s+(\w+)", content)
    decorator = "@wireup.injectable\n"
    if gateway_match:
        gw_class = gateway_match.group(2)
        decorator = f"@wireup.injectable(as_type={gw_class})\n"
    if "import wireup" not in content:
        content = "import wireup\n\n" + content
    new_content = re.sub(r"(^class\s+)", decorator + r"\1", content, count=1, flags=re.MULTILINE)
    return new_content, new_content != content
