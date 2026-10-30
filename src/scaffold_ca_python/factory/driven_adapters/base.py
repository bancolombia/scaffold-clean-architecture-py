"""Base class for driven-adapter factories."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.core.wiring_utils import find_existing_test_function_names

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class DrivenAdapterFactory(ABC):
    """Abstract base for driven-adapter factories."""

    fixed_name: ClassVar[str | None] = None

    def module_name(self, name: str | None) -> str | None:
        """Return the module directory name: fixed_name if set, else the user-supplied name."""
        return self.fixed_name or name

    @abstractmethod
    def build(self, builder: ModuleBuilder) -> None:
        """Populate *builder* with file and dependency operations."""

    @staticmethod
    def append_wiring_test(builder: ModuleBuilder, ctx_dict: dict[str, Any]) -> None:
        """Append ``test_container_resolves_<module>`` to test_wiring.py when a gateway is bound."""
        if not ctx_dict.get("gateway"):
            return
        wiring_test_path = resolve_tests_root(builder.project_root) / "application" / "config" / "test_wiring.py"
        fn_name = f"test_container_resolves_{ctx_dict['module_name']}"
        existing = wiring_test_path.read_text(encoding="utf-8") if wiring_test_path.exists() else ""
        if fn_name in find_existing_test_function_names(existing):
            return
        builder.append_to_file(
            wiring_test_path,
            builder.render("driven_adapter/wiring_test_stub.py.jinja2", ctx_dict),
        )
