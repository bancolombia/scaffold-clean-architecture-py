"""Tests for GeneratedFile, CreateFile, DeleteFile, FileOperation union."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from scaffold_ca_python.models.file_operation import CreateFile, DeleteFile, FileOperation, GeneratedFile


def test_generated_file_fields() -> None:
    gf = GeneratedFile(
        path=Path("/tmp/project/domain/model/order.py"),
        content="class Order: pass",
    )
    assert gf.path == Path("/tmp/project/domain/model/order.py")
    assert gf.content == "class Order: pass"
    assert gf.overwrite is False


def test_generated_file_overwrite_flag() -> None:
    gf = GeneratedFile(path=Path("/tmp/x.py"), content="", overwrite=True)
    assert gf.overwrite is True


def test_generated_file_requires_path() -> None:
    with pytest.raises(ValidationError):
        GeneratedFile(content="x")  # type: ignore[call-arg]


def test_create_file_kind_discriminator() -> None:
    gf = GeneratedFile(path=Path("/tmp/x.py"), content="pass")
    op = CreateFile(file=gf)
    assert op.kind == "create"


def test_delete_file_kind_discriminator() -> None:
    op = DeleteFile(path=Path("/tmp/x.py"))
    assert op.kind == "delete"


def test_file_operation_kind_distinguishes_types() -> None:
    gf = GeneratedFile(path=Path("/tmp/x.py"), content="")
    ops: list[FileOperation] = [
        CreateFile(file=gf),
        DeleteFile(path=Path("/tmp/y.py")),
    ]
    assert [op.kind for op in ops] == ["create", "delete"]
