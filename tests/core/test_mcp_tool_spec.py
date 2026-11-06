"""Tests for mcp_tool_spec module.

Tests for parsing and validating --add-tool CLI arguments.
"""

from __future__ import annotations

import pytest

from scaffold_ca_python.core.mcp_tool_spec import (
    ParamSpec,
    ToolSpec,
    build_tool_spec,
    find_existing_tool_names,
    has_bind_tools_function,
    has_test_registration_structure,
    parse_param,
    validate_description,
    validate_type_expression,
)

# parse_param tests


def test_parse_param_valid_simple() -> None:
    """parse_param accepts 'name:type' format."""
    assert parse_param("path:str") == ("path", "str")


def test_parse_param_accepts_soft_keyword() -> None:
    """parse_param accepts soft keywords like 'match' as parameter names."""
    assert parse_param("match:str") == ("match", "str")


def test_parse_param_rejects_no_colon() -> None:
    """parse_param rejects params missing colon."""
    with pytest.raises(ValueError, match="Expected 'name:type' format"):
        parse_param("path")


def test_parse_param_rejects_bad_casing() -> None:
    """parse_param rejects PascalCase parameter names."""
    with pytest.raises(ValueError, match="snake_case"):
        parse_param("Path:str")


def test_parse_param_rejects_hard_keyword() -> None:
    """parse_param rejects hard Python keywords."""
    with pytest.raises(ValueError, match="'class' is a Python keyword"):
        parse_param("class:str")


def test_parse_param_rejects_bad_type() -> None:
    """parse_param rejects non-type-expression types."""
    with pytest.raises(ValueError, match="not a recognizable type-expression"):
        parse_param("path:print('x')")


# validate_type_expression tests


def test_validate_type_expression_accepts_builtins() -> None:
    """validate_type_expression accepts builtin types."""
    assert validate_type_expression("str") is True
    assert validate_type_expression("int") is True
    assert validate_type_expression("float") is True
    assert validate_type_expression("bool") is True


def test_validate_type_expression_accepts_generics() -> None:
    """validate_type_expression accepts generic types."""
    assert validate_type_expression("list[str]") is True
    assert validate_type_expression("dict[str, int]") is True
    assert validate_type_expression("tuple[int, ...]") is True


def test_validate_type_expression_accepts_union() -> None:
    """validate_type_expression accepts union types."""
    assert validate_type_expression("str | None") is True
    assert validate_type_expression("int | str") is True
    assert validate_type_expression("typing.Optional[str]") is True


def test_validate_type_expression_accepts_literal() -> None:
    """validate_type_expression accepts Literal types."""
    assert validate_type_expression('Literal["a", "b"]') is True


def test_validate_type_expression_rejects_function_call() -> None:
    """validate_type_expression rejects function calls."""
    assert validate_type_expression("print('x')") is False


def test_validate_type_expression_rejects_string_literal() -> None:
    """validate_type_expression rejects bare string literals."""
    assert validate_type_expression('"hello"') is False


def test_validate_type_expression_rejects_arithmetic() -> None:
    """validate_type_expression rejects arithmetic expressions."""
    assert validate_type_expression("1 + 1") is False


def test_validate_type_expression_rejects_lambda() -> None:
    """validate_type_expression rejects lambda expressions."""
    assert validate_type_expression("lambda x: x") is False


def test_validate_type_expression_rejects_comprehension() -> None:
    """validate_type_expression rejects comprehensions."""
    assert validate_type_expression("[x for x in range(10)]") is False


# find_existing_tool_names tests


def test_find_existing_tool_names_returns_registered_names() -> None:
    """find_existing_tool_names returns @mcp.tool decorator names."""
    source = """
@mcp.tool("example_tool")
async def example_tool(query: str) -> str:
    return f"result: {query}"
"""
    assert "example_tool" in find_existing_tool_names(source)


def test_find_existing_tool_names_returns_function_names_inside_bind_tools() -> None:
    """find_existing_tool_names returns function names defined inside bind_tools."""
    source = """
async def bind_tools(mcp):
    @mcp.tool("search")
    async def do_search(query: str) -> str:
        return query
"""
    names = find_existing_tool_names(source)
    assert "search" in names  # from @mcp.tool("search")
    assert "do_search" in names  # function name inside bind_tools


def test_find_existing_tool_names_includes_bind_tools() -> None:
    """find_existing_tool_names always returns 'bind_tools' as reserved."""
    source = """
async def bind_tools(mcp):
    pass
"""
    assert "bind_tools" in find_existing_tool_names(source)


def test_find_existing_tool_names_ignores_comments() -> None:
    """find_existing_tool_names ignores tool-like text in comments/docstrings."""
    source = '''
# @mcp.tool("fake_tool")
async def bind_tools(mcp):
    """This is not @mcp.tool("another_fake")."""
    pass
'''
    names = find_existing_tool_names(source)
    assert "fake_tool" not in names
    assert "another_fake" not in names


# has_bind_tools_function tests


def test_has_bind_tools_function_returns_true_when_last() -> None:
    """has_bind_tools_function returns True when bind_tools is the last top-level statement."""
    source = """
from mcp.server.fastmcp import FastMCP

async def bind_tools(mcp: FastMCP) -> None:
    pass
"""
    assert has_bind_tools_function(source) is True


def test_has_bind_tools_function_returns_false_when_missing() -> None:
    """has_bind_tools_function returns False when bind_tools is absent."""
    source = """
from mcp.server.fastmcp import FastMCP

async def other_function() -> None:
    pass
"""
    assert has_bind_tools_function(source) is False


def test_has_bind_tools_function_returns_false_when_not_async() -> None:
    """has_bind_tools_function returns False when bind_tools is not async."""
    source = """
def bind_tools(mcp) -> None:
    pass
"""
    assert has_bind_tools_function(source) is False


def test_has_bind_tools_function_returns_false_when_in_comment() -> None:
    """has_bind_tools_function returns False when bind_tools only appears in a comment."""
    source = """
# async def bind_tools(mcp):
#     pass

async def other_function() -> None:
    pass
"""
    assert has_bind_tools_function(source) is False


def test_has_bind_tools_function_returns_false_when_followed_by_function() -> None:
    """has_bind_tools_function returns False when another function follows bind_tools."""
    source = """
async def bind_tools(mcp) -> None:
    pass

def helper() -> None:
    pass
"""
    assert has_bind_tools_function(source) is False


def test_has_bind_tools_function_returns_false_when_followed_by_assignment() -> None:
    """has_bind_tools_function returns False when an assignment follows bind_tools."""
    source = """
async def bind_tools(mcp) -> None:
    pass

__all__ = ["bind_tools"]
"""
    assert has_bind_tools_function(source) is False


# has_test_registration_structure tests


def test_has_test_registration_structure_returns_true_with_all_requirements() -> None:
    """has_test_registration_structure returns True when all requirements are met."""
    source = """
import asyncio
from my_app.infrastructure.entry_points.mcp_server.tools import bind_tools

def _make_mock_mcp():
    pass

def test_something():
    pass
"""
    assert has_test_registration_structure(source) is True


def test_has_test_registration_structure_returns_false_missing_helper() -> None:
    """has_test_registration_structure returns False when _make_mock_mcp is missing."""
    source = """
import asyncio
from my_app.infrastructure.entry_points.mcp_server.tools import bind_tools

def test_something():
    pass
"""
    assert has_test_registration_structure(source) is False


def test_has_test_registration_structure_returns_false_missing_bind_tools_import() -> None:
    """has_test_registration_structure returns False when bind_tools import is missing."""
    source = """
import asyncio

def _make_mock_mcp():
    pass
"""
    assert has_test_registration_structure(source) is False


def test_has_test_registration_structure_returns_false_missing_asyncio_import() -> None:
    """has_test_registration_structure returns False when asyncio import is missing."""
    source = """
from my_app.infrastructure.entry_points.mcp_server.tools import bind_tools

def _make_mock_mcp():
    pass
"""
    assert has_test_registration_structure(source) is False


# validate_description tests


def test_validate_description_accepts_normal_text() -> None:
    """validate_description accepts normal docstring-safe text."""
    assert validate_description("Creates a file on disk") == "Creates a file on disk"


def test_validate_description_returns_placeholder_for_none() -> None:
    """validate_description returns placeholder for None."""
    result = validate_description(None)
    assert "TODO" in result


def test_validate_description_returns_placeholder_for_empty() -> None:
    """validate_description returns placeholder for empty string."""
    result = validate_description("")
    assert "TODO" in result


def test_validate_description_rejects_triple_double_quote() -> None:
    """validate_description rejects text containing embedded triple-double-quote."""
    with pytest.raises(ValueError, match="triple-quote"):
        validate_description('breaks """ here')


def test_validate_description_rejects_triple_single_quote() -> None:
    """validate_description rejects text containing embedded triple-single-quote."""
    with pytest.raises(ValueError, match="triple-quote"):
        validate_description("breaks ''' here")


# ToolSpec and ParamSpec tests


def test_tool_spec_accepts_valid_input() -> None:
    """ToolSpec accepts valid tool specification."""
    spec = ToolSpec(
        name="create_file",
        params=[ParamSpec(name="path", type="str")],
        returns="str",
        docstring="Creates a file",
    )
    assert spec.name == "create_file"
    assert len(spec.params) == 1
    assert spec.params[0].name == "path"


def test_tool_spec_rejects_hard_keyword_name() -> None:
    """ToolSpec rejects hard Python keywords as tool names."""
    with pytest.raises(ValueError, match="'class' is a Python keyword"):
        ToolSpec(name="class", params=[], returns="str", docstring="Invalid")


def test_tool_spec_accepts_soft_keyword_name() -> None:
    """ToolSpec accepts soft keywords like 'match' as tool names."""
    spec = ToolSpec(name="match", params=[], returns="str", docstring="Match query")
    assert spec.name == "match"


def test_tool_spec_rejects_duplicate_param_names() -> None:
    """ToolSpec rejects duplicate parameter names."""
    with pytest.raises(ValueError, match="Duplicate.*param.*name"):
        ToolSpec(
            name="read_file",
            params=[ParamSpec(name="path", type="str"), ParamSpec(name="path", type="int")],
            returns="str",
            docstring="Read file",
        )


def test_param_spec_rejects_hard_keyword_name() -> None:
    """ParamSpec rejects hard Python keywords as parameter names."""
    with pytest.raises(ValueError, match="'import' is a Python keyword"):
        ParamSpec(name="import", type="str")


@pytest.mark.parametrize("bad_type", ["int, str", "...", "foo().bar"])
def test_invalid_type_expressions_rejected(bad_type: str) -> None:
    with pytest.raises(ValueError):
        ParamSpec(name="x", type=bad_type)


def test_build_tool_spec_applies_defaults() -> None:
    """build_tool_spec applies default return type and placeholder docstring."""
    spec = build_tool_spec(name="list_files", param=None, returns=None, description=None)
    assert spec.returns == "str"
    assert "TODO" in spec.docstring


def test_build_tool_spec_preserves_param_order() -> None:
    """build_tool_spec preserves --param order."""
    spec = build_tool_spec(
        name="copy_file",
        param=["src:str", "dest:str"],
        returns="bool",
        description="Copy file",
    )
    assert spec.params[0].name == "src"
    assert spec.params[1].name == "dest"


def test_build_tool_spec_with_no_params() -> None:
    """build_tool_spec handles zero parameters."""
    spec = build_tool_spec(name="list_all", param=[], returns="list[str]", description="List all")
    assert len(spec.params) == 0
