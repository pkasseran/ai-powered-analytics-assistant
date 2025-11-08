# AI‑Powered Analytics Assistant

A production‑oriented, multi‑agent system for self‑service BI. It turns natural‑language questions into validated SQL, fetches data from a semantic warehouse, and renders interactive Plotly charts with short narratives. The app uses LangGraph for orchestration, OpenAI via LangChain for reasoning, and Streamlit for the UI. Optional MCP (Model Context Protocol) tools provide safe, read‑only database access over TCP.

## Features

- Natural‑language to data questions, SQL, and charts
- Deterministic, YAML‑backed semantic layer (metrics, dimensions, joins)
- Validation at each stage (parser, SQL, chart JSON)
- Optional MCP Postgres server for read‑only queries with limits/timeouts
- JSON structured logging with per‑session correlation in `logs/`

<img src="ada-snapshot_1000.png" alt="Agent Workflow" width="800" height="500">

## Tech stack

- Python, Streamlit, Plotly
- LangGraph, LangChain, OpenAI (via `langchain-openai`)
- PostgreSQL (direct via SQLAlchemy or MCP TCP server)
- Docker (postgres database image)

## Repository layout (high level)

```
ai-powered-analytics-assistant/
├── code/
│   ├── ada_streamlit.py              # Main Streamlit app with per-session JSON logging
│   ├── graphs/                        # LangGraph graphs (orchestration)
│   │   ├── orchestrator_graph.py
│   │   ├── parser_graph.py
│   │   ├── data_extractor_graph.py
│   │   └── charting_graph.py
│   ├── nodes/                         # Workflow nodes (small, composable steps)
│   │   ├── parser_node.py
│   │   ├── parser_validation_node.py
│   │   ├── sql_generate_node.py
│   │   ├── sql_validate_node.py
│   │   ├── sql_extract_node.py
│   │   ├── run_extractor_node.py
│   │   ├── chart_render_node.py
│   │   ├── chart_validate_node.py
│   │   ├── run_render_chart_node.py
│   │   ├── init_loop_node.py
│   │   ├── pick_next_question_node.py
│   │   └── accumulate_and_advance_node.py
│   ├── services/                      # Business logic
│   │   ├── parsing_service.py
│   │   ├── parsing_validation_service.py
│   │   ├── sql_generation_service.py
│   │   ├── sql_validation_service.py
│   │   ├── data_extraction_service.py
│   │   └── charting_service_llm.py
│   ├── states/                        # Pydantic state models
│   │   ├── agentic_orchestrator_state.py
│   │   ├── parser_state.py
│   │   ├── charting_state.py
│   │   └── data_extractor_state.py
│   ├── models/                        # Domain models
│   │   ├── data_extractor_model.py
│   │   └── user_request_parser_model.py
│   ├── mcp_server/                    # TCP MCP server for Postgres
│   │   └── sql_postgres_tcp_server.py
│   ├── llm/                           # LLM client wrappers
│   │   └── openai_client.py
│   ├── utils/                         # Utilities & logging
│   │   ├── agent_logging_json.py
│   │   ├── mcp_client_tcp.py
│   │   └── prompt_loader.py
│   ├── tools/                         # In-process tools & DB adapters
│   │   ├── user_parser_tools.py
│   │   ├── chart_validation_tools.py
│   │   ├── postgres_validator_asyncpg.py
│   │   └── sqldb_sqlalchemy.py
│   └── tests/                         # (reserved for tests)
├── config/                            # App & semantic configuration
│   ├── config.yaml
│   ├── ag_data_extractor_config/
│   │   └── warehouse.yaml
│   └── ag_user_query_parser_config/
│       └── metrics.yaml
├── docs/                              # Design notes & diagrams
│   ├── publication_with_logging.md
│   └── *.mmd
├── setup/                             # Local Postgres bootstrap
│   ├── dwdb.dump                      # Copy of database 
│   ├── setup_docker_postgres_db.sh     
│   └── start_mcp_tcp_server.sh        # Helper to run the MCP TCP server
├── logs/                              # JSON logs (generated at runtime)
├── requirements.txt
├── requirements-test.txt
└── README.md
```

## Prerequisites

- Python 3.10+ (recommended)
- Docker installed and running
- A PostgreSQL database you can read from
  - Use the provided Docker script and database dump in `setup/`
- An OpenAI API key (for LLM steps)

## Quick start

1) Installation

```bash
# Clone and navigate to project
cd ai-powered-analytics-assistant

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your OpenAI API key
```

2) Configure environment variables:

```bash
# For using OpenAI
OPENAI_API_KEY=sk-your-openai-api-key-here
DEFAULT_LLM_MODEL="gpt-4-mini"

# FOR SQLALCHEMY (direct Database connection)
# Change as needed to match your local Postgres setup
POSTGRES_URI=postgresql+psycopg2://postgres:postgres@localhost:5435/dwdb

# FOR MCP CONFIGURATION
# Change as needed to match your local Postgres setup
MCP_PG_DSN=postgresql://postgres:postgres@localhost:5435/dwdb 
MCP_PG_MAX_ROWS=5000
MCP_PG_TIMEOUT_MS=20000
MCP_TCP_HOST=127.0.0.1
MCP_TCP_PORT=8765
MCP_ENABLED=1
```

3) Setup Database

Prerequisite: 
- Make sure Docker is installed and running

This will run a container on port 5435 and restore `dwdb.dump` into a database named `dwdb`.

```bash
cd setup
./setup_docker_postgres_db.sh # for MacOS or Linux
# or
./setup_docker_postgres_db.ps1 # for Windows
```

4) Start MCP server

The app will automatically use MCP when:
- `MCP_ENABLED=1`, and
- it can connect to the TCP server at `MCP_TCP_HOST:MCP_TCP_PORT`.

If you prefer not to run MCP, keep `MCP_ENABLED=0` and the app will fall back to direct SQLAlchemy for queries and a local asyncpg validator for SQL validation.

```bash
 
 cd setup
./ start_mcp_tcp_server.sh # for MacOS or Linux
# or
./start_mcp_tcp_server.ps1 # for Windowns

```

5) Run the Streamlit UI:

```bash
cd ai-powered-analytics-assistant
streamlit run code/ada_streamlit.py
```

- Open the URL shown by Streamlit, enter a question (e.g., "Show monthly revenue by product in 2025."), and click "Send request to Agent".
- Logs: see `logs/` (one JSON log file per session by default).


## Configuration

- Main settings: `code/config/settings.py` (reads env vars and resolves paths)
- LLM + prompt settings: `config/config.yaml`
- Semantic layer YAMLs:
  - Warehouse joins/filters: `config/ag_data_extractor_config/warehouse.yaml`
  - Metrics, dimensions, aliases: `config/ag_user_query_parser_config/metrics.yaml`

You can customize model names (e.g., `gpt-4.1-mini`) and temperatures in `config/config.yaml` without code changes.

## Logging

- Structured JSON logs are written to `logs/` with per‑session correlation IDs.
- The Streamlit app shows the latest agent progress message in the UI while full details stream to the logs.

## Troubleshooting

- MCP connection refused
  - Ensure the MCP server is running (see above) and `MCP_ENABLED=1`.
  - Or set `MCP_ENABLED=0` to use local validators and direct SQLAlchemy.
- Postgres connection/auth issues
  - Verify `POSTGRES_URI` format and credentials; try connecting with `psql`.
- OpenAI auth errors
  - Ensure `OPENAI_API_KEY` is set in your environment and valid.
- Streamlit cannot find the module
  - Run from the repo root so that imports like `code.graphs...` resolve.

## Notes on the semantic layer

The current YAML semantic layer is designed to evolve toward an enterprise catalog (e.g., Microsoft Purview) behind the same contract. You can keep the public interface stable while swapping the backing source via adapters.

## License

Refer to the included LICENSE file