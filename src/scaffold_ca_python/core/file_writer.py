"""file_writer: atomic file creation and deletion using tempdir staging."""

from __future__ import annotations

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
                  be created or deleted, without touching disk.
    """

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
        for op in operations:
            if isinstance(op, CreateFile):
                result.append(op.file.path)
            elif isinstance(op, (DeleteFile, InsertAfter, AppendToFile)):
                result.append(op.path)
        return result

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
        op.path.write_text(insert_after_text(original, op.anchor, op.content, path=op.path), encoding="utf-8")

    @staticmethod
    def _apply_append_to_file(op: AppendToFile) -> None:
        """Append *op.content* to the end of *op.path*, or create the file."""
        original = op.path.read_text(encoding="utf-8") if op.path.exists() else None
        updated = append_text(original, op.content, op.marker)
        if updated is None:
            return
        op.path.parent.mkdir(parents=True, exist_ok=True)
        op.path.write_text(updated, encoding="utf-8")


def insert_after_text(original: str, anchor: str, content: str, *, path: Path) -> str:
    """Return *original* with *content* inserted after the first line containing *anchor*."""
    lines = original.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if anchor in line:
            lines.insert(i + 1, content if content.endswith("\n") else content + "\n")
            return "".join(lines)
    raise ValueError(f"insert_after anchor {anchor!r} not found in {path}")


def append_text(original: str | None, content: str, marker: str | None) -> str | None:
    """Return the appended text, or None when *marker* is already present.

    Existing files get trailing blank lines normalized to one newline; new files
    start with *content* minus leading blank lines.
    """
    if original is None:
        return content.lstrip("\n")
    if marker and marker in original:
        return None
    return original.rstrip("\n") + "\n" + content
