"""ModuleBuilder orchestration layer for factory-based module generation."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from scaffold_ca_python.core.file_writer import FileWriter, append_text, insert_after_text
from scaffold_ca_python.core.pyproject_writer import (
    inject_dependencies,
    inject_group_dependencies,
    update_project_scripts,
)
from scaffold_ca_python.core.template_renderer import TemplateRenderer
from scaffold_ca_python.models.file_operation import (
    AppendToFile,
    CreateFile,
    DeleteFile,
    FileOperation,
    GeneratedFile,
    InsertAfter,
)

if TYPE_CHECKING:
    from scaffold_ca_python.models.context import ModuleContext, ProjectContext


class ModuleBuilder:
    """Collect and persist module generation operations.

    Factory implementations should only interact with this class, not with lower-level
    infrastructure helpers such as FileWriter/TemplateRenderer/pyproject_writer.
    """

    def __init__(
        self,
        *,
        project_root: Path,
        project_ctx: ProjectContext,
        module_ctx: ModuleContext | None = None,
        dry_run: bool = False,
        file_writer: FileWriter | None = None,
        template_renderer: TemplateRenderer | None = None,
    ) -> None:
        self.project_root = project_root
        if project_ctx.project_root is None:
            project_ctx = project_ctx.model_copy(update={"project_root": project_root})
        self.project_ctx = project_ctx
        self.module_ctx = module_ctx
        self.dry_run = dry_run

        self._file_writer = file_writer or FileWriter()
        self._renderer = template_renderer or TemplateRenderer()

        self._operations: list[FileOperation] = []
        self._dependencies: list[str] = []
        self._group_dependencies: dict[str, list[str]] = {}
        self._params: dict[str, object] = {}
        self._pending_project_script: str | None = None

    def add_file(
        self,
        path: Path,
        content: str,
        *,
        overwrite: bool = False,
    ) -> None:
        """Queue a file creation operation."""
        self._operations.append(CreateFile(file=GeneratedFile(path=path, content=content, overwrite=overwrite)))

    def delete_file(self, path: Path) -> None:
        """Queue a file deletion operation."""
        self._operations.append(DeleteFile(path=path))

    def insert_after(self, path: Path, anchor: str, content: str) -> None:
        """Queue an insert-after operation on an existing file.

        *content* will be inserted on a new line immediately after the first
        line in *path* that contains *anchor*.  In dry-run mode the path is
        included in the preview list without modifying the file.
        """
        self._operations.append(InsertAfter(path=path, anchor=anchor, content=content))

    def append_to_file(self, path: Path, content: str, *, marker: str | None = None) -> None:
        """Queue an append-to-file operation.

        *content* will be appended to the end of *path*. If *path* does not exist,
        it will be created. When the file exists, its trailing blank lines are
        normalized to a single newline before appending. In dry-run mode the path
        is included in the preview list without modifying the file.
        """
        self._operations.append(AppendToFile(path=path, content=content, marker=marker))

    def render(self, template_name: str, context: BaseModel | dict[str, Any]) -> str:
        """Render a template through the shared renderer."""
        return self._renderer.render(template_name, context)

    def base_context(self) -> dict[str, object]:
        """Shared template context: project fields plus module fields (when available)."""
        ctx: dict[str, object] = {
            **self.project_ctx.model_dump(),
            "pkg": self.project_ctx.python_package,
            "project_root": str(self.project_root),
        }
        if self.module_ctx is not None:
            ctx.update(self.module_ctx.model_dump())
        return ctx

    def add_rendered(
        self,
        path: Path,
        template: str,
        ctx: BaseModel | dict[str, Any],
        *,
        overwrite: bool = False,
    ) -> None:
        """Render *template* with *ctx* and queue a file creation."""
        content = self.render(template, ctx)
        self.add_file(path, content, overwrite=overwrite)

    def add_dependency(self, package: str, *, group: str | None = None) -> None:
        """Queue a package dependency to inject into pyproject.toml.

        Parameters
        ----------
        package:
            Package specifier, e.g. ``"httpx>=0.27"`` or ``"respx>=0.22"``.
        group:
            When ``None`` (default) the package is injected into
            ``[project.dependencies]`` (runtime). When set to a group name such as
            ``"test"``, the package is injected into
            ``[dependency-groups.<group>]`` instead.
        """
        if group is None:
            self._dependencies.append(package)
        else:
            self._group_dependencies.setdefault(group, []).append(package)

    @property
    def pending_dependencies(self) -> list[str]:
        """Runtime dependencies queued for injection (read-only copy)."""
        return list(self._dependencies)

    @property
    def pending_group_dependencies(self) -> dict[str, list[str]]:
        """Dependency-group deps queued for injection, keyed by group (read-only copy)."""
        return {group: list(pkgs) for group, pkgs in self._group_dependencies.items()}

    def set_project_script(self, entry_fn: str = "start_server") -> None:
        self._pending_project_script = entry_fn

    @property
    def pending_project_script(self) -> str | None:
        """Entry function name queued for [project.scripts] update, or None."""
        return self._pending_project_script

    def add_param(self, key: str, value: object) -> None:
        """Store an ad-hoc value used by factories/commands."""
        self._params[key] = value

    def get_param(self, key: str, default: object | None = None) -> object | None:
        """Read a previously stored parameter value."""
        return self._params.get(key, default)

    def preview_diffs(self) -> list[str]:
        """Return a unified diff per queued file operation, with project-relative paths."""
        diffs: list[str] = []
        for op in self._operations:
            path = op.file.path if isinstance(op, CreateFile) else op.path
            before = path.read_text(encoding="utf-8") if path.exists() else None
            after: str | None
            if isinstance(op, CreateFile):
                after = op.file.content
            elif isinstance(op, DeleteFile):
                after = None
            elif isinstance(op, InsertAfter):
                after = insert_after_text(before or "", op.anchor, op.content, path=path)
            else:
                after = append_text(before, op.content, op.marker)
                if after is None:
                    continue
            rel = path.relative_to(self.project_root).as_posix() if path.is_relative_to(self.project_root) else path
            lines = difflib.unified_diff(
                (before or "").splitlines(keepends=True),
                (after or "").splitlines(keepends=True),
                fromfile=f"a/{rel}" if before is not None else "/dev/null",
                tofile=f"b/{rel}" if after is not None else "/dev/null",
            )
            diff = "".join(line if line.endswith("\n") else line + "\n" for line in lines)
            if diff:
                diffs.append(diff)
        return diffs

    def persist(self) -> list[Path]:
        """Persist queued file and dependency operations.

        In dry-run mode no writes occur; the method returns the paths that would be
        affected by file operations.
        """
        paths = self._file_writer.execute(self._operations, dry_run=self.dry_run)

        if self._dependencies:
            inject_dependencies(self.project_root, self._dependencies, dry_run=self.dry_run)

        for grp, pkgs in self._group_dependencies.items():
            inject_group_dependencies(self.project_root, grp, pkgs, dry_run=self.dry_run)

        if self._pending_project_script is not None:
            update_project_scripts(
                self.project_root,
                self.project_ctx,
                self._pending_project_script,
                dry_run=self.dry_run,
            )

        return paths
