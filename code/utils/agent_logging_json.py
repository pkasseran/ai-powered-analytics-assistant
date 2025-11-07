import logging
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SETTINGS


class JsonFormatter(logging.Formatter):
    """
    Format log records as structured JSON with a session_id, ISO-8601 UTC timestamp,
    log level, and logger name.

    Features:
      - If record.msg is a dict -> merged as top-level fields.
      - If record.msg is a string that is valid JSON -> parsed and merged (dict) or
        stored as a value (list/str/number).
      - Otherwise -> stored under "message".
      - Merges `extra=...` fields (excluding standard logging attributes).
      - Includes exception info if present.
    """

    STANDARD_KEYS = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "stacklevel"
    }

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id

    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
            "level": record.levelname,
            "session_id": self.session_id,
            "logger": record.name,
        }

        # 1) Merge dicts logged directly: logger.info({"event": "...", ...})
        if isinstance(record.msg, dict):
            base.update(record.msg)
            message_str = None
        else:
            # 2) Normal string messages; try to parse JSON text to merge
            raw = record.getMessage()
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    base.update(parsed)
                    message_str = None
                else:
                    # JSON but not an object; keep under "message"
                    message_str = parsed
            except (json.JSONDecodeError, TypeError):
                # Not JSON -> keep raw text (multi-line safe; will be escaped by json.dumps)
                message_str = raw

        if message_str is not None:
            base["message"] = message_str

        # 3) Merge extra fields from the record (added via logger.*(..., extra={...}))
        for k, v in record.__dict__.items():
            if k not in self.STANDARD_KEYS and k not in base:
                base[k] = v

        # 4) Exceptions
        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)

        return json.dumps(base, ensure_ascii=False)


def setup_logging(
    app_name: str = "data_assistant",
    level: int = logging.INFO,
    to_console: bool = True,
    to_file: bool = True,
    session_id: Optional[str] = None,
    one_log_per_session: bool = False
) -> logging.Logger:
    """
    Setup JSON logging with a unique session_id.
    Logs to console (stdout) for streaming and to a daily file for persistence.

    Returns a configured logger named `app_name`.
    """
    session_id = session_id or str(uuid.uuid4())

    log_dir = SETTINGS.ROOT_DIR / "logs"
    if to_file:
        log_dir.mkdir(parents=True, exist_ok=True)
        # Daily log file naming - add seconds to the name to avoid collisions in fast session creation
        current_day = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        if one_log_per_session:
            log_file = log_dir / f"{app_name}_{current_day}_{session_id}.log"
        else:
            log_file = log_dir / f"{app_name}_{current_day}.log"

    logger = logging.getLogger(app_name)
    logger.setLevel(level)
    logger.propagate = False  # avoid duplicate logs in root handlers

    # Remove any existing handlers (important for notebooks/reloaders)
    for h in logger.handlers[:]:
        logger.removeHandler(h)

    formatter = JsonFormatter(session_id)

    if to_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(formatter)
        fh.setLevel(level)
        logger.addHandler(fh)

    if to_console:
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        sh.setLevel(level)
        logger.addHandler(sh)

    # Emit an initialization event
    logger.info({"event": "logger_initialized", "session_id": session_id, "app_name": app_name})
    return logger


def parse_escaped_string(s: str) -> str:
    """
    Convert a string containing literal escape sequences like '\\n' into actual newlines
    so it logs with proper formatting. Supports JSON text too.

    Example:
        raw = "Line1\\nLine2\\nLine3"
        logger.info(parse_escaped_string(raw))
    """
    import json as _json
    import ast as _ast

    text = s.strip()
    if not text:
        return text

    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        try:
            return _json.loads(text)
        except _json.JSONDecodeError:
            try:
                return _ast.literal_eval(text)
            except Exception:
                return text
    else:
        return text.encode("utf-8").decode("unicode_escape")


# ---------- Optional tiny helpers (use if you like) ----------

def log_sql(logger: logging.Logger, sql: str, **meta: Any) -> None:
    """
    Log SQL as structured JSON (keeps human text optional).
    Example:
        log_sql(logger, sql_text, phase="execute", source="mcp", rows=252, duration_ms=87)
    """
    payload = {"event": "sql_run", "sql": sql}
    payload.update(meta)
    logger.info(payload)


def log_dataset(logger: logging.Logger, rows: int, cols: int, sample: Optional[Any] = None, **meta: Any) -> None:
    """
    Log dataset shape and (optional) small sample as real JSON objects.
    Example:
        log_dataset(logger, rows=len(df), cols=len(df.columns), sample=df.head(3).to_dict(orient="records"))
    """
    payload = {"event": "dataset_ready", "rows": rows, "cols": cols}
    if sample is not None:
        payload["sample"] = sample
    payload.update(meta)
    logger.info(payload)


"""
USAGE EXAMPLE:

logger = setup_logging("data_assistant_agent")

# Plain text -> becomes {"message": "...", ...}
logger.info("Validating SQL via MCP...")

# Dict -> becomes merged JSON (no double-encoding)
logger.info({"event": "mcp_query_done", "rows": 252})

# Stringified JSON -> parsed & merged
logger.info(json.dumps({"event": "chart_preview", "len": 743}))

# With extra fields
logger.info("HTTP Request complete", extra={"http_status": 200, "method": "POST", "service": "openai"})

# Helpers
log_sql(logger, "WITH base AS (...)", phase="execute", source="mcp")
log_dataset(logger, rows=252, cols=3, sample=[{"period": "2025-07-01", "product": "X", "actual_revenue": 123.45}])

"""