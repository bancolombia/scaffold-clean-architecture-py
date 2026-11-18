"""MCP tool specification parsing and validation.

This module provides utilities for parsing and validating --add-tool CLI arguments,
including tool names, parameters, type expressions, and duplicate-name detection.
"""

from __future__ import annotations

import ast
import keyword

from pydantic import BaseModel, field_validator, model_validator

from scaffold_ca_python.core.name_utils import validate_snake_identifier


class ParamSpec(BaseModel):
    """A single parsed --param name:type value."""

    name: str
    type: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate parameter name is snake_case and not a hard keyword."""
        validate_snake_identifier(v, kind="parameter name")

        if keyword.iskeyword(v):
            msg = f"'{v}' is a Python keyword and cannot be used as a parameter name."
            raise ValueError(msg)

        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate type is a recognizable type expression."""
        if not validate_type_expression(v):
            msg = f"Invalid type '{v}'. Not a recognizable type-expression."
            raise ValueError(msg)
        return v


class ToolSpec(BaseModel):
    """Parsed, fully-validated representation of a single --add-tool invocation."""

    name: str
    params: list[ParamSpec]
    returns: str
    docstring: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate tool name is snake_case and not a hard keyword."""
        validate_snake_identifier(v, kind="tool name")

        if keyword.iskeyword(v):
            msg = f"'{v}' is a Python keyword and cannot be used as a tool name."
            raise ValueError(msg)

        return v

    @field_validator("returns")
    @classmethod
    def validate_returns_type(cls, v: str) -> str:
        """Validate returns is a valid type expression."""
        if not validate_type_expression(v):
            msg = f"Invalid --returns '{v}'. Not a recognizable type-expression."
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def check_no_duplicate_param_names(self) -> ToolSpec:
        """Reject duplicate parameter names."""
        names = [p.name for p in self.params]
        seen = set()
        for name in names:
            if name in seen:
                msg = f"Duplicate --param name '{name}'. Each parameter name must be unique."
                raise ValueError(msg)
            seen.add(name)
        return self


def parse_param(param_str: str) -> tuple[str, str]:
    """Parse a --param 'name:type' string.

    Args:
        param_str: String in format 'name:type'

    Returns:
        Tuple of (name, type)

    Raises:
        ValueError: If format is invalid, name is not snake_case, name is a hard
                    keyword, or type is not a recognizable type-expression
    """
    if ":" not in param_str:
        msg = f"Invalid --param '{param_str}'. Expected 'name:type' format."
        raise ValueError(msg)

    name, type_str = param_str.split(":", 1)

    try:
        validate_snake_identifier(name, kind="parameter name")
    except ValueError as e:
        msg = f"Invalid --param '{param_str}'. Parameter name must be snake_case (e.g., 'path:str')."
        raise ValueError(msg) from e

    if keyword.iskeyword(name):
        msg = f"Invalid --param '{param_str}'. '{name}' is a Python keyword and cannot be used as a parameter name."
        raise ValueError(msg)

    if not validate_type_expression(type_str):
        msg = f"Invalid --param '{param_str}'. '{type_str}' is not a recognizable type-expression."
        raise ValueError(msg)

    return name, type_str


def validate_type_expression(type_str: str) -> bool:
    """Check if type_str is a recognizable Python type expression.

    Uses AST parsing to verify the type string is a valid type expression
    (Name, Subscript, BinOp with |, Attribute, etc.) and not a function call,
    string literal, arithmetic expression, lambda, or comprehension.

    Args:
        type_str: Type expression string to validate

    Returns:
        True if valid type expression, False otherwise
    """
    try:
        node = ast.parse(type_str, mode="eval").body
    except SyntaxError:
        return False

    # Allowed: Name (str, int), Subscript (list[str]), BinOp (str | None),
    # Attribute (typing.Optional), Constant (for Literal values inside [...])
    # Not allowed: Call, Str/Constant at top level, Lambda, comprehensions, arithmetic
    return _is_type_expression_node(node)


def _is_type_expression_node(node: ast.expr) -> bool:
    """Recursively check if AST node represents a valid type expression."""
    if isinstance(node, ast.Name):
        return True
    if isinstance(node, ast.Constant):
        return node.value is None
    if isinstance(node, ast.Attribute):
        return isinstance(node.value, (ast.Name, ast.Attribute))
    if isinstance(node, ast.Subscript):
        # Allow Constant in subscript (for Literal["a", "b"])
        return _is_type_expression_node(node.value) and _is_subscript_arg_valid(node.slice)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _is_type_expression_node(node.left) and _is_type_expression_node(node.right)
    return False


def _is_subscript_arg_valid(node: ast.expr) -> bool:
    """Check if subscript argument is valid (Name, Tuple, or Constant for Literal)."""
    if isinstance(node, ast.Constant):
        return True  # Allow string literals inside Literal[...]
    if isinstance(node, ast.Tuple):
        return all(_is_subscript_arg_valid(elt) for elt in node.elts)
    return _is_type_expression_node(node)


def find_existing_tool_names(tools_py_source: str) -> set[str]:
    """Find all existing tool names in tools.py.

    Returns the union of:
    - Every @<x>.tool("name") registered name
    - Every function name defined directly inside bind_tools
    - The reserved name "bind_tools"

    Args:
        tools_py_source: Source code of tools.py

    Returns:
        Set of existing tool names
    """
    names: set[str] = {"bind_tools"}  # Always reserved

    try:
        module = ast.parse(tools_py_source)
    except SyntaxError:
        return names

    for node in ast.walk(module):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                # Match @mcp.tool("name") or @x.tool("name")
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == "tool"
                    and decorator.args
                    and isinstance(decorator.args[0], ast.Constant)
                    and isinstance(decorator.args[0].value, str)
                ):
                    names.add(decorator.args[0].value)

    for node in ast.walk(module):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "bind_tools":
            for child in ast.walk(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child != node:
                    names.add(child.name)

    return names


def has_bind_tools_function(tools_py_source: str) -> bool:
    """Check if tools.py has async def bind_tools as the last top-level statement.

    Args:
        tools_py_source: Source code of tools.py

    Returns:
        True if last top-level statement is async def bind_tools, False otherwise
    """
    try:
        module = ast.parse(tools_py_source)
    except SyntaxError:
        return False

    if not module.body:
        return False

    last_stmt = module.body[-1]
    return isinstance(last_stmt, ast.AsyncFunctionDef) and last_stmt.name == "bind_tools"


def has_test_registration_structure(test_tools_py_source: str) -> bool:
    """Check if test_tools.py can host an appended registration test.

    Returns True only if it defines a top-level _make_mock_mcp function and
    imports both bind_tools and asyncio.

    Args:
        test_tools_py_source: Source code of test_tools.py

    Returns:
        True if structure is compatible, False otherwise
    """
    try:
        module = ast.parse(test_tools_py_source)
    except SyntaxError:
        return False

    has_helper = any(isinstance(node, ast.FunctionDef) and node.name == "_make_mock_mcp" for node in module.body)

    imported = set()
    for node in module.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                imported.add(alias.asname or alias.name)

    has_required_imports = {"bind_tools", "asyncio"} <= imported

    return has_helper and has_required_imports


def validate_description(description: str | None) -> str:
    """Validate description is safe for docstring embedding.

    Args:
        description: User-provided description or None

    Returns:
        Validated description or generic placeholder

    Raises:
        ValueError: If description contains embedded triple-quote sequence
    """
    if not description or not description.strip():
        return "TODO: describe this tool."

    if '"""' in description or "'''" in description:
        msg = "--description contains an embedded triple-quote sequence and cannot be used as a docstring."
        raise ValueError(msg)

    return description


def build_tool_spec(
    name: str,
    param: list[str] | None,
    returns: str | None,
    description: str | None,
) -> ToolSpec:
    """Build a validated ToolSpec from CLI arguments.

    Args:
        name: Tool name (required)
        param: List of 'name:type' strings or None
        returns: Return type expression or None (defaults to "str")
        description: Tool description or None (defaults to placeholder)

    Returns:
        Validated ToolSpec

    Raises:
        ValueError: If any validation fails
    """
    params = []
    if param:
        for p in param:
            param_name, param_type = parse_param(p)
            params.append(ParamSpec(name=param_name, type=param_type))

    return ToolSpec(
        name=name,
        params=params,
        returns=returns or "str",
        docstring=validate_description(description),
    )
