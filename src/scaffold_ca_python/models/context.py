"""ProjectContext and ModuleContext Pydantic v2 models."""

from pathlib import Path

from pydantic import BaseModel, computed_field, field_validator

from scaffold_ca_python.core.name_utils import NAME_RE, to_kebab_case, to_pascal_case, to_snake_case


class ProjectContext(BaseModel):
    name: str
    scaffold_version: str | None = None
    project_root: Path | None = None

    @property
    def is_legacy(self) -> bool:
        """Return True when the project was generated without scaffold-ca-python ≥ 0.6.0."""
        return self.scaffold_version is None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not NAME_RE.match(v):
            raise ValueError(
                f"Project name '{v}' is invalid. "
                "Use kebab-case (e.g., 'my-project') or snake_case (e.g., 'my_project')."
            )
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def python_package(self) -> str:
        """Derive the Python import root: snake_case of name."""
        return to_snake_case(self.name)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def python_package_script(self) -> str:
        """Kebab-case name for ``[project.scripts]`` keys (PEP 508 normalized name)."""
        return to_kebab_case(self.name)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def class_name(self) -> str:
        """PascalCase class name derived from name (safe for Python identifiers)."""
        return to_pascal_case(self.name)

    @property
    def src_pkg_root(self) -> Path:
        """Package root under src/ (requires project_root when used)."""
        if self.project_root is None:
            raise ValueError("project_root must be set on ProjectContext to use src_pkg_root")
        return self.project_root / "src" / self.python_package


class ModuleContext(BaseModel):
    name: str
    project: ProjectContext

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not NAME_RE.match(v):
            raise ValueError(
                f"Module name '{v}' is invalid. Use kebab-case (e.g., 'my-module') or snake_case (e.g., 'my_module')."
            )
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def class_name(self) -> str:
        """PascalCase class name derived from name."""
        return to_pascal_case(self.name)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def module_name(self) -> str:
        """snake_case file name (without .py) derived from name."""
        return to_snake_case(self.name)
