import logging
import os
from datetime import datetime
from pathlib import Path
from config.settings import SETTINGS

def setup_logging(app_name: str = "data_assistant") -> logging.Logger:
    """
    One-time setup for simple logging to a daily file + console.
    Call this ONCE at process start (e.g., in app.py).
    """
    # logs/ folder next to this code/ directory
    #code_dir = Path(__file__).resolve().parents[1]   # .../code
    log_dir = SETTINGS.ROOT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    current_day = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{app_name}_{current_day}.log"

    # Configure root only once
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()   # remove this handler if you want file-only
        ]
    )
    return logging.getLogger(app_name)


def parse_escaped_string(s: str) -> str:
    """
    Convert a string containing literal escape sequences like '\\n' into
    actual newlines so it logs with proper formatting.

    Used mainly for LLM outputs that embed escaped characters.

    Example:
        raw = "Line1\\nLine2\\nLine3"
        formatted = parse_escaped_string(raw)
        logger.info(formatted)

    Returns:
        str: The string with real line breaks and escapes resolved.
    """
    import json, ast

    text = s.strip()

    # Try JSON decoding first (handles most escape sequences cleanly)
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return ast.literal_eval(text)
    else:
        # Fallback: manually interpret standard escapes like \n, \t
        return text.encode("utf-8").decode("unicode_escape")
