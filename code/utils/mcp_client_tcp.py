"""
MCP SQL Client wrapper for the Postgres MCP server - TCP Only Version.

Provides a lightweight interface used by services/nodes:
- validate(sql) -> (valid: bool, message: str | None)
- query(sql, params: list | None, limit: int | None, timeout_ms: int | None) -> dict

Notes
- This client only supports TCP mode for connecting to MCP servers.
- Establishes fresh TCP connections per call for simplicity and robustness.
- TODO: Later we will add an optimized version of the tcp client that uses asyncio-tcp connection pooling for production readiness.
- Requires `asyncio`.

Example
    from utils.mcp_client_tcp import get_tcp_mcp_sql_client_from_settings
    client = get_tcp_mcp_sql_client_from_settings()
    ok, msg = client.validate("SELECT 1")
    res = client.query("SELECT 1 as x", params=None, limit=10)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
import json

from config.settings import SETTINGS

log = logging.getLogger("agentic_data_assistant.mcp_client_tcp")


class MCPSQLClientTCP:
    def __init__(
        self,
        *,
        tcp_host: str = "127.0.0.1",
        tcp_port: int = 8765,
        max_rows: int = 5000,
        timeout_ms: int = 20000,
        connection_timeout: float = 10.0,
    ) -> None:
        """Create a TCP-only MCP SQL client.

        Args:
            tcp_host: TCP server hostname/IP
            tcp_port: TCP server port
            max_rows: Maximum rows to return from queries
            timeout_ms: Query timeout in milliseconds
            connection_timeout: TCP connection timeout in seconds
        """
        self._tcp_host = tcp_host
        self._tcp_port = tcp_port
        self._max_rows = max_rows
        self._timeout_ms = timeout_ms
        self._connection_timeout = connection_timeout

    async def _acall_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool via TCP JSON server."""
        log.debug("TCP MCP call %s to %s:%d", name, self._tcp_host, self._tcp_port)
        
        try:
            # Establish TCP connection with timeout
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._tcp_host, self._tcp_port),
                timeout=self._connection_timeout
            )
            
            # Send request
            req = {"tool": name, "arguments": arguments}
            request_data = (json.dumps(req) + "\n").encode("utf-8")
            writer.write(request_data)
            await writer.drain()
            
            # Read response
            line = await reader.readline()
            
            # Close connection
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            
            if not line:
                return {"error": "no response from TCP server"}
            
            # Parse response
            resp = json.loads(line.decode("utf-8"))
            if not resp.get("ok", False):
                return {"error": resp.get("error", "unknown error")}
            
            return resp.get("result", {})
            
        except asyncio.TimeoutError:
            return {"error": f"connection timeout to {self._tcp_host}:{self._tcp_port}"}
        except ConnectionRefusedError:
            return {"error": f"connection refused to {self._tcp_host}:{self._tcp_port}"}
        except json.JSONDecodeError as e:
            return {"error": f"invalid JSON response: {e}"}
        except Exception as e:
            return {"error": f"unexpected error: {e}"}

    async def avalidate(self, query: str) -> Tuple[bool, Optional[str]]:
        """Validate SQL query asynchronously."""
        resp = await self._acall_tool("sql.validate", {"query": query})
        
        if "error" in resp:
            log.warning("SQL validation error: %s", resp["error"])
            return False, resp["error"]
        
        valid = bool(resp.get("valid", False))
        message = resp.get("message")
        
        log.debug("SQL validation result: valid=%s, message=%s", valid, message)
        return valid, message

    async def aquery(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        limit: Optional[int] = None,
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute SQL query asynchronously."""
        payload = {
            "query": query,
            "params": params or [],
            "limit": limit or self._max_rows,
            "timeout_ms": timeout_ms or self._timeout_ms,
        }
        
        resp = await self._acall_tool("sql.query", payload)
        
        if "error" in resp:
            log.warning("SQL query error: %s", resp["error"])
            return {"error": resp["error"], "rows": [], "rowcount": 0}
        
        # Ensure consistent response shape
        rows = resp.get("rows", [])
        rowcount = resp.get("rowcount", len(rows))
        
        log.debug("SQL query result: %d rows returned", rowcount)
        return {"rows": rows, "rowcount": rowcount}

    # Synchronous facades for convenience in sync code paths
    def validate(self, query: str) -> Tuple[bool, Optional[str]]:
        """Validate SQL query synchronously."""
        return asyncio.run(self.avalidate(query))

    def query(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        limit: Optional[int] = None,
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute SQL query synchronously."""
        return asyncio.run(self.aquery(query, params=params, limit=limit, timeout_ms=timeout_ms))

    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test TCP connection to MCP server."""
        try:
            valid, message = self.validate("SELECT 1")
            if valid:
                return True, "TCP connection successful"
            else:
                return False, f"Connection test failed: {message}"
        except Exception as e:
            return False, f"Connection test error: {e}"


def get_tcp_mcp_sql_client_from_settings() -> Optional[MCPSQLClientTCP]:
    """Factory that creates TCP-only MCP client from settings.

    Expected settings (with fallbacks):
      - MCP_ENABLED: bool
      - MCP_TCP_HOST: str (default: "127.0.0.1")
      - MCP_TCP_PORT: int (default: 8765)
      - MCP_SQL_MAX_ROWS: int (default: 5000)
      - MCP_SQL_TIMEOUT_MS: int (default: 20000)
      - MCP_CONNECTION_TIMEOUT: float (default: 10.0)
    """
    enabled = bool(getattr(SETTINGS, "MCP_ENABLED", False))
    if not enabled:
        log.info("MCP disabled via settings; returning None client")
        return None
    
    tcp_host = getattr(SETTINGS, "MCP_TCP_HOST", "127.0.0.1")
    tcp_port = int(getattr(SETTINGS, "MCP_TCP_PORT", 8765))
    max_rows = int(getattr(SETTINGS, "MCP_SQL_MAX_ROWS", 5000))
    timeout_ms = int(getattr(SETTINGS, "MCP_SQL_TIMEOUT_MS", 20000))
    connection_timeout = float(getattr(SETTINGS, "MCP_CONNECTION_TIMEOUT", 10.0))
    
    log.info("Creating TCP MCP client: %s:%d", tcp_host, tcp_port)
    
    return MCPSQLClientTCP(
        tcp_host=tcp_host,
        tcp_port=tcp_port,
        max_rows=max_rows,
        timeout_ms=timeout_ms,
        connection_timeout=connection_timeout,
    )


def create_tcp_mcp_client(
    host: str = "127.0.0.1",
    port: int = 8765,
    max_rows: int = 5000,
    timeout_ms: int = 20000,
    connection_timeout: float = 10.0,
) -> MCPSQLClientTCP:
    """Create a TCP MCP client with explicit parameters."""
    return MCPSQLClientTCP(
        tcp_host=host,
        tcp_port=port,
        max_rows=max_rows,
        timeout_ms=timeout_ms,
        connection_timeout=connection_timeout,
    )