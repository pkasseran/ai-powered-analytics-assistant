import os
from pathlib import Path
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class _Settings:
    ROOT_DIR = Path(__file__).resolve().parents[2] # agentic_data_assistant/
    CODE_DIR = ROOT_DIR / "code"
    CONFIG_YAML_PATH =  ROOT_DIR / "config" / "config.yaml"
    POSTGRES_URI = os.getenv("POSTGRES_URI")  # e.g., postgresql://user:pass@host:5432/db
    OPEN_AI_API_KEY = os.getenv("OPENAI_API_KEY")
    DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4")
    
    MCP_ENABLED = os.getenv("MCP_ENABLED", 0) # "1" to enable MCP, "0" to disable
    MCP_SQL_MAX_ROWS = int(os.getenv("MCP_SQL_MAX_ROWS", "5000"))
    MCP_SQL_TIMEOUT_MS = int(os.getenv("MCP_SQL_TIMEOUT_MS", "20000"))
    MCP_TCP_HOST = os.getenv("MCP_TCP_HOST", "127.0.0.1")
    MCP_TCP_PORT = int(os.getenv("MCP_TCP_PORT", "8765"))

    LOGGING_APP_NAME: str = "ada"


SETTINGS = _Settings()

if __name__ == "__main__":
    print("Settings:")
    print(f"ROOT_DIR: {SETTINGS.ROOT_DIR}")
    print(f"CONFIG_YAML_PATH: {SETTINGS.CONFIG_YAML_PATH}")
    print(f"POSTGRES_URI: {SETTINGS.POSTGRES_URI}")
    print(f"MCP_ENABLED: {SETTINGS.MCP_ENABLED}")

    _USE_MCP = True if SETTINGS.MCP_ENABLED == "1" else False
    print(f"_USE_MCP: {_USE_MCP}")

# Settings:
# ROOT_DIR: /Users/praveshkasseran/Documents/Projects/readytensor_projects/agentic_data_assistant
# CONFIG_YAML_PATH: /Users/praveshkasseran/Documents/Projects/readytensor_projects/agentic_data_assistant/code/config/config.yaml
# MODEL_AGENT_DATA_EXTRACTOR: gpt-4
# POSTGRES_URI: postgresql+psycopg2://postgres:pravesh@localhost:5434/postgres