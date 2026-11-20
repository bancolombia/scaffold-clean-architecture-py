"""Pinned dependency specifiers injected by scaffold factories."""

from __future__ import annotations

FASTAPI_STANDARD = "fastapi[standard]~=0.141.1"
UVICORN_STANDARD = "uvicorn[standard]~=0.53.0"
WIREUP = "wireup~=2.13.0"
PYDANTIC_SETTINGS = "pydantic-settings~=2.15.0"
MCP = "mcp~=1.30.0"  # ~=1.30.0 caps below 2.0; templates target the 1.x FastMCP API
STARLETTE = "starlette~=1.6.0"
HTTPX = "httpx~=0.28.1"
RESPX = "respx~=0.23.1"
BOTO3 = "boto3~=1.43.98"
A2A_SDK_HTTP_SERVER = "a2a-sdk[http-server]~=1.1.4"
MYPY = "mypy~=1.16.1"

RESTAPI_RUNTIME = (FASTAPI_STANDARD, UVICORN_STANDARD, WIREUP, PYDANTIC_SETTINGS)
MCP_RUNTIME = (MCP, UVICORN_STANDARD, STARLETTE, WIREUP, PYDANTIC_SETTINGS)
A2A_RUNTIME = (A2A_SDK_HTTP_SERVER, STARLETTE, UVICORN_STANDARD, WIREUP, PYDANTIC_SETTINGS)
