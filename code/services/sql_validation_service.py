import asyncio
import logging
from typing import Tuple, Optional, Dict

from config.settings import SETTINGS
from tools.postgres_validator_asyncpg import validate_sql
from utils.mcp_client_tcp import get_tcp_mcp_sql_client_from_settings, MCPSQLClientTCP

log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".services.sql_validation_service")

_USE_MCP = True if SETTINGS.MCP_ENABLED == "1" else False

class SQLValidationService:
    """SQL validation service with optional MCP backend.

    If MCP is enabled via settings, validation is delegated to the MCP sql.validate tool.
    Otherwise, falls back to the local asyncpg-based validator.
    """

    def __init__(self, uri: str | None = None, mcp_client: MCPSQLClientTCP | None = None):
        self.uri = (uri or SETTINGS.POSTGRES_URI)
        self.mcp = mcp_client if mcp_client is not None else get_tcp_mcp_sql_client_from_settings()
        self.use_mcp = _USE_MCP

    def validate(self, sql: str) -> Tuple[bool, Optional[Dict]]:
        # Prefer MCP when available
        # Check if MCP connection is available
        if self.mcp is not None:
            if self.use_mcp and self.mcp.test_connection():
                log.info("Validating SQL via MCP...")
                ok, msg = self.mcp.validate(sql)
                if ok:
                    log.info("Validation OK (MCP)")
                    return True, None
                else:
                    log.warning("Validation failed (MCP): %s", msg)
                    return False, {"message": msg}

        # Fallback to local asyncpg validator
        log.info("Validating SQL via asyncpg fallback...")
        if not self.uri:
            raise RuntimeError("POSTGRES_URI is not set")
        uri = self.uri.replace("postgresql+psycopg2://", "postgresql://")
        ok, err = asyncio.run(validate_sql(uri, sql))
        log.info("Validation result: %s", "OK" if ok else f"ERR {err}")
        return ok, err