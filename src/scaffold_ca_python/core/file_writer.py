"""file_writer: atomic file creation and deletion using tempdir staging."""

from __future__ import annotations

import difflib
import os
import tempfile
from pathlib import Path

from scaffold_ca_python.models.file_operation import (
    AppendToFile,
    CreateFile,
    DeleteFile,
    FileOperation,
    GeneratedFile,
    InsertAfter,
)


class FileWriter:
    """Execute a list of :class:`FileOperation` objects.

    Real mode:  Uses a temporary directory for staging, then ``os.replace()``
                (atomic on POSIX) to commit every file.  If staging fails for
                *any* file the temp directory is discarded and no partial writes
                reach the target tree.

    Dry-run mode: Returns a list of target :class:`Path` objects that *would*
                  be created or deleted, without touching disk. Unified diffs are
                  accumulated in :attr:`dry_run_diffs`.
    """

    def __init__(self) -> None:
        self.dry_run_diffs: list[str] = []

    def execute(
        self,
        operations: list[FileOperation],
        *,
        dry_run: bool = False,
    ) -> list[Path]:
        """Execute *operations*, returning affected paths."""
        if dry_run:
            return self._dry_run(operations)
        return self._commit(operations)

    def write(self, path: Path, content: str) -> None:
        """Write a single file to *path* with *content*."""
        self._commit([CreateFile(file=GeneratedFile(path=path, content=content))])

    def _dry_run(self, operations: list[FileOperation]) -> list[Path]:
        result: list[Path] = []
        self.dry_run_diffs = []
        for op in operations:
            if isinstance(op, CreateFile):
                result.append(op.file.path)
                self._record_create_diff(op)
            elif isinstance(op, DeleteFile):
                result.append(op.path)
                self._record_delete_diff(op.path)
            elif isinstance(op, InsertAfter):
                result.append(op.path)
                self._record_insert_diff(op)
            elif isinstance(op, AppendToFile):
                result.append(op.path)
                self._record_append_diff(op)
        return result

    def _record_create_diff(self, op: CreateFile) -> None:
        path = op.file.path
        before = path.read_text(encoding="utf-8") if path.exists() else ""
        after = op.file.content
        label = str(path)
        if not before:
            lines = difflib.unified_diff(
                [],
                after.splitlines(keepends=True),
                fromfile="/dev/null",
                tofile=label,
                lineterm="",
            )
        else:
            lines = difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=label,
                tofile=label,
                lineterm="",
            )
        diff = "".join(lines)
        if diff:
            self.dry_run_diffs.append(diff)

    def _record_delete_diff(self, path: Path) -> None:
        if not path.exists():
            return
        before = path.read_text(encoding="utf-8")
        lines = difflib.unified_diff(
            before.splitlines(keepends=True),
            [],
            fromfile=str(path),
            tofile="/dev/null",
            lineterm="",
        )
        diff = "".join(lines)
        if diff:
            self.dry_run_diffs.append(diff)

    def _record_insert_diff(self, op: InsertAfter) -> None:
        if not op.path.exists():
            return
        before = op.path.read_text(encoding="utf-8")
        lines = before.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if op.anchor in line:
                insertion = op.content if op.content.endswith("\n") else op.content + "\n"
                lines.insert(i + 1, insertion)
                break
        after = "".join(lines)
        diff_lines = difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(op.path),
            tofile=str(op.path),
            lineterm="",
        )
        diff = "".join(diff_lines)
        if diff:
            self.dry_run_diffs.append(diff)

    def _record_append_diff(self, op: AppendToFile) -> None:
        before = op.path.read_text(encoding="utf-8") if op.path.exists() else ""
        normalized = before.rstrip("\n") + "\n" if before else ""
        after = normalized + op.content
        lines = difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(op.path),
            tofile=str(op.path),
            lineterm="",
        )
        diff = "".join(lines)
        if diff:
            self.dry_run_diffs.append(diff)

    def _partition(self, operations: list[FileOperation]) -> tuple[list[CreateFile], list[DeleteFile]]:
        creates = [op for op in operations if isinstance(op, CreateFile)]
        deletes = [op for op in operations if isinstance(op, DeleteFile)]
        return creates, deletes

    def _stage(self, creates: list[CreateFile], tmpdir: str) -> list[tuple[Path, Path]]:
        staged: list[tuple[Path, Path]] = []
        for i, op in enumerate(creates):
            tmp_file = Path(tmpdir) / f"staged_{i}"
            tmp_file.write_text(op.file.content, encoding="utf-8")
            staged.append((tmp_file, op.file.path))
        return staged

    def _preflight(self, creates: list[CreateFile], staged: list[tuple[Path, Path]]) -> None:
        for op, (_, target) in zip(creates, staged, strict=True):
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and not op.file.overwrite:
                raise FileExistsError(
                    f"File already exists: {target}. Use overwrite=True on GeneratedFile to replace it."
                )

    def _apply_deletes(self, deletes: list[DeleteFile]) -> None:
        for op in deletes:
            if op.path.exists():
                op.path.unlink()

    def _apply_mutations(self, operations: list[FileOperation]) -> None:
        for op in operations:
            if isinstance(op, InsertAfter):
                self._apply_insert_after(op)
            elif isinstance(op, AppendToFile):
                self._apply_append_to_file(op)

    def _commit(self, operations: list[FileOperation]) -> list[Path]:
        """Stage all creates in a temp dir, then commit atomically."""
        creates, deletes = self._partition(operations)
        committed: list[Path] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            staged = self._stage(creates, tmpdir)
            self._preflight(creates, staged)
            for tmp_file, target in staged:
                os.replace(tmp_file, target)
                committed.append(target)

        self._apply_deletes(deletes)
        self._apply_mutations(operations)
        return committed

    @staticmethod
    def _apply_insert_after(op: InsertAfter) -> None:
        """Insert *op.content* on a new line after the first line containing *op.anchor*."""
        if not op.path.exists():
            raise FileNotFoundError(f"insert_after target not found: {op.path}")
        original = op.path.read_text(encoding="utf-8")
        lines = original.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if op.anchor in line:
                insertion = op.content if op.content.endswith("\n") else op.content + "\n"
                lines.insert(i + 1, insertion)
                op.path.write_text("".join(lines), encoding="utf-8")
                return
        raise ValueError(f"insert_after anchor {op.anchor!r} not found in {op.path}")

    @staticmethod
    def _apply_append_to_file(op: AppendToFile) -> None:
        """Append *op.content* to the end of *op.path*, or create the file.

        When the file exists, trailing blank lines are normalized to a single newline
        before appending. When it doesn't exist, it's created with *op.content* as
        initial contents (leading blank lines stripped).
        """
        if op.path.exists():
            original = op.path.read_text(encoding="utf-8")
            if op.marker and op.marker in original:
                return
            normalized = original.rstrip("\n") + "\n"
            op.path.write_text(normalized + op.content, encoding="utf-8")
        else:
            op.path.parent.mkdir(parents=True, exist_ok=True)
            content = op.content.lstrip("\n")
            op.path.write_text(content, encoding="utf-8")
