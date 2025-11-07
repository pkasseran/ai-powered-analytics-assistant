"""
MCP SQL Client wrapper for the Postgres MCP server.

Provides a lightweight interface used by services/nodes:
- validate(sql) -> (valid: bool, message: str | None)
- query(sql, params: list | None, limit: int | None, timeout_ms: int | None) -> dict

Notes
- This client establishes a fresh stdio session per call for simplicity and robustness.
  You can optimize later by keeping a persistent session if needed.
- Requires `mcp` and `asyncio`.

Example
    from code.utils.mcp_client import get_mcp_sql_client_from_settings
    client = get_mcp_sql_client_from_settings()
    ok, msg = client.validate("SELECT 1")
    res = client.query("SELECT 1 as x", params=None, limit=10)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
import json

try:
    from mcp.client.stdio import stdio_client, StdioServerParameters  # type: ignore
    from mcp.client.session import ClientSession  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "The MCP Python SDK is required. Install with: pip install mcp"
    ) from e

from config.settings import SETTINGS

log = logging.getLogger("agentic_data_assistant.mcp_client")


class MCPSQLClient:
    def __init__(
        self,
        server_cmd: Optional[List[str]] = None,
        *,
        mode: str = "stdio",
        tcp_host: Optional[str] = None,
        tcp_port: Optional[int] = None,
        max_rows: int = 5000,
        timeout_ms: int = 20000,
    ) -> None:
        """Create an MCP SQL client.

        mode: "stdio" (spawn process) or "tcp" (connect to host/port)
        server_cmd: command to spawn stdio server (when mode=="stdio")
        tcp_host/tcp_port: when mode=="tcp"
        """
        self._mode = mode
        self._server_cmd = server_cmd or ["python", "-m", "mcp_server.sql_postgres_server"]
        self._tcp_host = tcp_host or "127.0.0.1"
        self._tcp_port = tcp_port or 8765
        self._max_rows = max_rows
        self._timeout_ms = timeout_ms

    async def _acall_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool either via stdio MCP or TCP JSON server."""
        log.debug("MCP call %s args=%s", name, {**arguments, **{"_redacted": True}})
        if self._mode == "tcp":
            reader, writer = await asyncio.open_connection(self._tcp_host, self._tcp_port)
            req = {"tool": name, "arguments": arguments}
            writer.write((json.dumps(req) + "\n").encode("utf-8"))
            await writer.drain()
            line = await reader.readline()
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            if not line:
                return {"error": "no response"}
            resp = json.loads(line.decode("utf-8"))
            if not resp.get("ok", False):
                # unify error surface
                return {"error": resp.get("error", "unknown error")}
            return resp.get("result", {})
        else:
            # stdio MCP: build proper StdioServerParameters from command list/string
            server_params: StdioServerParameters
            if isinstance(self._server_cmd, list) and len(self._server_cmd) >= 1:
                server_params = StdioServerParameters(
                    command=self._server_cmd[0], args=self._server_cmd[1:]
                )
            elif isinstance(self._server_cmd, str):
                server_params = StdioServerParameters(command=self._server_cmd)
            else:
                raise RuntimeError(
                    "Invalid MCP stdio server command. Expected list[str] or str."
                )
            async with stdio_client(server_params) as (read_stream, write_stream):  # type: ignore
                # Support both MCP client API shapes:
                # Newer: ClientSession(read_stream=..., write_stream=..., client_name="...")
                # Older: ClientSession(client_name).connect(read_stream, write_stream)
                try:
                    async with ClientSession(
                        read_stream=read_stream,
                        write_stream=write_stream,
                        client_name="mcp-sql-client",
                    ) as session:  # type: ignore
                        result = await session.call_tool(name, arguments=arguments)  # type: ignore
                        return result  # type: ignore
                except TypeError:
                    async with ClientSession("mcp-sql-client") as session:  # type: ignore
                        await session.connect(read_stream, write_stream)  # type: ignore
                        result = await session.call_tool(name, arguments=arguments)  # type: ignore
                        return result  # type: ignore

    async def avalidate(self, query: str) -> Tuple[bool, Optional[str]]:
        resp = await self._acall_tool("sql.validate", {"query": query})
        valid = bool(resp.get("valid", False))
        return valid, resp.get("message")

    async def aquery(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        limit: Optional[int] = None,
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload = {
            "query": query,
            "params": params or [],
            "limit": limit,
            "timeout_ms": timeout_ms or self._timeout_ms,
        }
        resp = await self._acall_tool("sql.query", payload)
        # Ensure shape
        rows = resp.get("rows", [])
        rowcount = resp.get("rowcount", len(rows))
        return {"rows": rows, "rowcount": rowcount, **({"error": resp["error"]} if "error" in resp else {})}

    # Synchronous facades for convenience in sync code paths
    def validate(self, query: str) -> Tuple[bool, Optional[str]]:
        return asyncio.run(self.avalidate(query))

    def query(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        limit: Optional[int] = None,
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        return asyncio.run(self.aquery(query, params=params, limit=limit, timeout_ms=timeout_ms))


def get_mcp_sql_client_from_settings() -> Optional[MCPSQLClient]:
    """Factory that respects SETTINGS feature flags.

    Expected optional settings (with fallbacks):
      - MCP_ENABLED: bool
      - MCP_SERVER_CMD: list[str]
      - MCP_SQL_MAX_ROWS: int
      - MCP_SQL_TIMEOUT_MS: int
    """
    enabled = bool(getattr(SETTINGS, "MCP_ENABLED", False))
    if not enabled:
        log.info("MCP disabled via settings; returning None client")
        return None
    mode = getattr(SETTINGS, "MCP_SERVER_MODE", "stdio")
    max_rows = int(getattr(SETTINGS, "MCP_SQL_MAX_ROWS", 5000))
    timeout_ms = int(getattr(SETTINGS, "MCP_SQL_TIMEOUT_MS", 20000))

    if mode == "tcp":
        tcp_host = getattr(SETTINGS, "MCP_TCP_HOST", "127.0.0.1")
        tcp_port = int(getattr(SETTINGS, "MCP_TCP_PORT", 8765))
        return MCPSQLClient(
            None,
            mode="tcp",
            tcp_host=tcp_host,
            tcp_port=tcp_port,
            max_rows=max_rows,
            timeout_ms=timeout_ms,
        )
    else:
        server_cmd = getattr(SETTINGS, "MCP_SERVER_CMD", None)
        # Normalize server_cmd: allow JSON/list, or space-separated string
        if not server_cmd:
            server_cmd = ["python", "-m", "code.mcp_server.sql_postgres_server"]
        elif isinstance(server_cmd, str):
            # Try JSON first
            try:
                parsed = json.loads(server_cmd)
                if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                    server_cmd = parsed
                else:
                    # Fallback: simple whitespace split
                    server_cmd = server_cmd.strip().split()
            except Exception:
                server_cmd = server_cmd.strip().split()
        return MCPSQLClient(
            server_cmd,
            mode="stdio",
            max_rows=max_rows,
            timeout_ms=timeout_ms,
        )
