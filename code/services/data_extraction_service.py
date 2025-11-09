import pandas as pd
from sqlalchemy import text
from tools.sqldb_sqlalchemy import get_sql_db
from config.settings import SETTINGS
from utils.mcp_client_tcp import get_tcp_mcp_sql_client_from_settings, MCPSQLClientTCP
import logging

log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".services.data_extraction")

_USE_MCP = True if SETTINGS.MCP_ENABLED == "1" else False

class DataExtractionService:
    """Data extraction service with optional MCP backend for read-only queries.

    If MCP is enabled via settings, executes queries via the MCP sql.query tool with enforced
    row limits and timeouts. Otherwise falls back to SQLAlchemy direct execution.
    """

    def __init__(self, uri: str | None = None, mcp_client: MCPSQLClientTCP | None = None):
        self.uri = uri or SETTINGS.POSTGRES_URI
        self.mcp = mcp_client if mcp_client is not None else get_tcp_mcp_sql_client_from_settings()
        self.use_mcp = _USE_MCP
        log.info(f"DataExtractionService initialized. MCP enabled: {self.use_mcp}")

    def _rows_to_df(self, rows: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(rows)
        # Infer better dtypes
        df = df.convert_dtypes()
        # Optionally, convert date-like columns
        for col in df.columns:
            cl = str(col).lower()
            if 'date' in cl or 'month' in cl or 'period' in cl:
                try:
                    df[col] = pd.to_datetime(df[col])
                except Exception:
                    pass
        return df

    def run_query(self, sql: str) -> pd.DataFrame:
        # Prefer MCP when available
        # Check if MCP connection is available
        test_conn_ok, test_conn_msg = self.mcp.test_connection()
        if self.mcp is not None:
            if self.use_mcp and test_conn_ok:
                log.info("Running query via MCP sql.query...")
                log.info("Running SQL: %s", sql)
                resp = self.mcp.query(sql, params=None, limit=getattr(SETTINGS, "MCP_SQL_MAX_ROWS", None))
                if "error" in resp and resp["error"]:
                    log.error("MCP query error: %s", resp["error"])
                    raise RuntimeError(f"MCP query error: {resp['error']}")
                rows = resp.get("rows", [])
                log.info("MCP query done (rows=%d)", len(rows))
                return self._rows_to_df(rows)

        # Fallback to SQLAlchemy direct execution
        log.info("Running query via SQLAlchemy fallback...")
        db = get_sql_db(self.uri)
        with db._engine.begin() as conn:
            result = conn.execute(text(sql))
            cols = list(result.keys())
            rows = [dict(r) for r in result.mappings().all()]
        df = pd.DataFrame(rows, columns=cols)
        # Infer better dtypes and parse date-like columns
        df = df.convert_dtypes()
        for col in df.columns:
            cl = str(col).lower()
            if 'date' in cl or 'month' in cl or 'period' in cl:
                try:
                    df[col] = pd.to_datetime(df[col])
                except Exception:
                    pass
        log.info("Query done (rows=%d, cols=%d)", len(rows), len(cols))
        return df
