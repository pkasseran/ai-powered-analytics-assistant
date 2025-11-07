#requires -Version 5.1
# Simple launcher for the PostgreSQL MCP TCP server on Windows.
# Assumes all configuration is handled inside the Python module (dotenv/env defaults).

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $repoRoot
try {
  python -m code.mcp_server.sql_postgres_tcp_server
}
finally {
  Pop-Location
}
