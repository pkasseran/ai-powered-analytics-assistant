import logging
import pandas as pd
from states.agentic_orchestrator_state import AgenticOrchestratorState
from states.data_extractor_state import DataExtractorState
from graphs.data_extractor_graph import build_data_extractor_graph

from langgraph.func import task
from config.settings import SETTINGS
log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.run_extractor")

# build once at import; if you prefer, move inside the function
_EXTRACTOR_APP = build_data_extractor_graph()


def df_dates_to_str(df, date_format='%Y-%m-%d'):
    # Find all columns with datetime dtype
        # Print all column datatypes for debugging
        print("DataFrame column dtypes:")
        print(df.dtypes)
        datetime_cols = df.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]', 'datetime'])
        # print("@@@@date columns", datetime_cols.columns)
        for col in datetime_cols.columns:
            df = df.sort_values(by=col)
            df[col] = df[col].dt.strftime(date_format)
        return df

def dq_dataset_to_str(dq_dataset: pd.DataFrame) -> str:
    """
    Convert a pandas DataFrame to a string json representation for LLM prompt consumption.
    """
    if dq_dataset is None or dq_dataset.empty:
        return "[]"
    # convert dates column before to_json:
    df = df_dates_to_str(dq_dataset)
    json_str = df.to_json(orient='records')
    #print("@@@@@myjson_str@@@@@:", json_str)
    return json_str

def run_extractor_node(state: AgenticOrchestratorState) -> AgenticOrchestratorState:
    dq = state["data_question"]
    extractor_state: DataExtractorState = {"semantic": state["semantic"], "data_question": dq}
    out = _EXTRACTOR_APP.invoke(extractor_state)
    df: pd.DataFrame = out.get("df")
    progress = state.get("progress_messages", [])
    progress.append(f"Data Extraction completed for question {state['current_idx']+1}.")
    progress.append(f"Rendering chart for question {state['current_idx']+1}...")
    
    # convert dataset to string for DQ dataset field for JSON serialization
    dq_dataset_str = dq_dataset_to_str(df)
  
    try:
        dq.dataset = dq_dataset_str  # type: ignore[attr-defined]
    except Exception:
        dq = dq.model_copy(update={"dataset": dq_dataset_str})  # pydantic v2 fallback

    log.info("Extracted df shape: %s", None if df is None else df.shape)
    return {**state, "df": df, "data_question": dq, "progress_messages": progress}
