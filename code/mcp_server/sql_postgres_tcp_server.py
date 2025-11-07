"""
TCP JSON server for SQL tools (Postgres).

Protocol (newline-delimited JSON per request/response):
  Request:  {"tool": "sql.validate"|"sql.query"|"schema.introspect", "arguments": {...}}
  Response: {"ok": true, "result": {...}} or {"ok": false, "error": "..."}

Env config:
  MCP_PG_DSN          - Postgres DSN (e.g., postgresql://user:pass@host:5432/db)
  MCP_PG_MAX_ROWS     - max rows per query (default 5000)
  MCP_PG_TIMEOUT_MS   - statement timeout in ms (default 20000)
  MCP_TCP_HOST        - bind host (default 127.0.0.1)
  MCP_TCP_PORT        - bind port (default 8765)

Run:
  python -m code.mcp_server.sql_postgres_tcp_server
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
import datetime
import decimal

import asyncpg

import dotenv

dotenv.load_dotenv()

# Config
DEFAULT_MAX_ROWS = int(os.getenv("MCP_PG_MAX_ROWS", "5000"))
DEFAULT_TIMEOUT_MS = int(os.getenv("MCP_PG_TIMEOUT_MS", "20000"))
PG_DSN = os.getenv("MCP_PG_DSN", "postgresql://localhost/postgres")
TCP_HOST = os.getenv("MCP_TCP_HOST", "127.0.0.1")
TCP_PORT = int(os.getenv("MCP_TCP_PORT", "8765"))

DISALLOWED = (
    "insert",
    "update",
    "delete",
    "alter",
    "drop",
    "truncate",
    "create",
    "grant",
    "revoke",
)


def _is_disallowed(sql: str) -> Optional[str]:
    s = sql.strip().lower()
    for bad in DISALLOWED:
        if bad in s:
            return bad
    return None


def _enforce_limit(sql: str, requested_limit: Optional[int], max_rows: int) -> str:
    # first remove any ";" at the end of the sql
    sql = sql.rstrip().rstrip(";")
    limit = min(requested_limit or max_rows, max_rows)
    return f"SELECT * FROM ( {sql} ) AS sub LIMIT {limit}"


async def _get_pool() -> asyncpg.Pool:
    global _POOL  # type: ignore
    try:
        return _POOL  # type: ignore
    except NameError:
        _POOL = await asyncpg.create_pool(PG_DSN)  # type: ignore
        return _POOL  # type: ignore


async def _run_explain(pool: asyncpg.Pool, sql: str, timeout_ms: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(f"SET statement_timeout = {int(timeout_ms)}")
        await conn.fetch("EXPLAIN " + sql)


async def _run_query(
    pool: asyncpg.Pool, sql: str, params: Optional[List[Any]], timeout_ms: int
) -> List[Dict[str, Any]]:
    async with pool.acquire() as conn:
        await conn.execute(f"SET statement_timeout = {int(timeout_ms)}")
        rows = await conn.fetch(sql, *(params or []))
        def _to_jsonable(v: Any) -> Any:
            if isinstance(v, (str, int, float, bool)) or v is None:
                return v
            if isinstance(v, (datetime.date, datetime.datetime)):
                # Use ISO 8601 for dates/times
                return v.isoformat()
            if isinstance(v, decimal.Decimal):
                # Convert to float; if NaN/Inf, fall back to string
                try:
                    f = float(v)
                    if f != f or f in (float('inf'), float('-inf')):
                        return str(v)
                    return f
                except Exception:
                    return str(v)
            # Fallback to string for any unknown types
            return str(v)

        out: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            out.append({k: _to_jsonable(v) for k, v in d.items()})
        return out


async def _introspect(pool: asyncpg.Pool) -> Dict[str, Any]:
    async with pool.acquire() as conn:
        tables = await conn.fetch(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
            """
        )
        columns = await conn.fetch(
            """
            SELECT table_schema, table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name, ordinal_position
            """
        )
        return {"tables": [dict(t) for t in tables], "columns": [dict(c) for c in columns]}


async def _handle_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    tool = payload.get("tool")
    args = payload.get("arguments", {}) or {}
    pool = await _get_pool()

    try:
        if tool == "sql.validate":
            query = args.get("query", "")
            if not isinstance(query, str) or not query.strip():
                return {"ok": False, "error": "empty query"}
            bad = _is_disallowed(query)
            if bad:
                return {"ok": True, "result": {"valid": False, "message": f"disallowed statement: {bad}"}}
            try:
                await _run_explain(pool, query, DEFAULT_TIMEOUT_MS)
                return {"ok": True, "result": {"valid": True, "message": "ok", "diagnostics": []}}
            except Exception as e:
                return {"ok": True, "result": {"valid": False, "message": str(e)}}

        elif tool == "sql.query":
            query = args.get("query", "")
            if not isinstance(query, str) or not query.strip():
                return {"ok": False, "error": "empty query"}
            bad = _is_disallowed(query)
            if bad:
                return {"ok": True, "result": {"rows": [], "rowcount": 0, "error": f"disallowed statement: {bad}"}}
            params = args.get("params") or []
            limit = args.get("limit")
            timeout_ms = int(args.get("timeout_ms") or DEFAULT_TIMEOUT_MS)
            safe_sql = _enforce_limit(query, limit, DEFAULT_MAX_ROWS)
            try:
                rows = await _run_query(pool, safe_sql, params, timeout_ms)
                return {"ok": True, "result": {"rows": rows, "rowcount": len(rows)}}
            except Exception as e:
                return {"ok": True, "result": {"rows": [], "rowcount": 0, "error": str(e)}}

        elif tool == "schema.introspect":
            meta = await _introspect(pool)
            return {"ok": True, "result": meta}

        else:
            return {"ok": False, "error": f"unknown tool: {tool}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    addr = writer.get_extra_info("peername")
    try:
        while not reader.at_eof():
            line = await reader.readline()
            if not line:
                break
            try:
                payload = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                resp = {"ok": False, "error": "invalid json"}
                writer.write((json.dumps(resp) + "\n").encode("utf-8"))
                await writer.drain()
                continue
            resp = await _handle_request(payload)
            writer.write((json.dumps(resp) + "\n").encode("utf-8"))
            await writer.drain()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def _amain() -> None:
    server = await asyncio.start_server(handle_client, TCP_HOST, TCP_PORT)
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"[sql_postgres_tcp_server] listening on {addrs}")
    async with server:
        await server.serve_forever()


def main() -> None:
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
