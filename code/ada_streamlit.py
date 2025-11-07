import uuid
import json
from pathlib import Path

import streamlit as st
import yaml
import plotly.graph_objects as go

from graphs.orchestrator_graph import build_orchestrator_graph
from states.agentic_orchestrator_state import AgenticOrchestratorState
from config.settings import SETTINGS
# REMOVE the old logger import:
# from utils.agent_logging import setup_logging
from utils.agent_logging_json import setup_logging  # new JSON logging mechanism


# ---------------------------
# Streamlit & Page Setup
# ---------------------------
st.set_page_config(page_title="AI-Powered Analytics Assistant", layout="wide")
st.title("AI-Powered Analytics Assistant")

st.markdown("""
<span style='color:#1f77b4;'>I am an AI-powered data assistant that helps you analyze and visualize your data for <span style='color:#b47b1f;'><b>Sales and Revenue</b></span> insights.<br>
Simply enter your data question in the input box and click 'Send request to Agent'.<br>
I will process your request and generate charts along with analysis narratives to help you understand your data</span>
""", unsafe_allow_html=True)


# ---------------------------
# Logger bootstrap (per-user)
# ---------------------------
def get_logger():
    # Persist a unique session_id per browser session
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    # Build the logger once per session and cache it
    if "logger" not in st.session_state:
        st.session_state.logger = setup_logging(
            app_name="ada",
            session_id=st.session_state.session_id,  # per-user correlation
            to_console=True,
            to_file=True,
            one_log_per_session=True # separate log file per user session, default is False
        )
    return st.session_state.logger


logger = get_logger()
st.caption(f"Session ID: `{st.session_state.session_id}`")


# ---------------------------
# Load semantic config
# ---------------------------
semantic_path = Path(SETTINGS.ROOT_DIR) / "config" / "ag_data_extractor_config" / "warehouse.yaml"
semantic = yaml.safe_load(open(semantic_path))

user_query = st.text_input("Enter your data question:", "Show monthly revenue by product in 2025.")
run_workflow = st.button("Send request to Agent")


# ---------------------------
# Run workflow
# ---------------------------
if run_workflow:
    request_id = str(uuid.uuid4())  # per-run correlation across logs
    status_box = st.empty()

    logger.info({"event": "run_started", "request_id": request_id, "user_query": user_query})

    try:
        app = build_orchestrator_graph()
        initial: AgenticOrchestratorState = {
            "user_query": user_query,
            "semantic": semantic,
            "progress_messages": ["Start processing user query..."],
        }

        final_state = None
        with st.spinner("Working on it ..."):
            for state in app.stream(initial, stream_mode="values"):
                # Stream progress to UI and logs
                progress_messages = state.get("progress_messages", [])
                if progress_messages:
                    last_2_msg = progress_messages[-2] if len(progress_messages) > 1 else progress_messages[-1]
                    last_msg = progress_messages[-1]
                    progress_html = f"""
                    <div style="background-color:#949596; border-radius:8px; padding:16px; border:1px solid #040404; margin-bottom:16px;">
                      <strong>Agent Progress:</strong><br>
                      {"<br>".join(progress_messages)}
                    </div>
                    """
                    status_box.markdown(progress_html, unsafe_allow_html=True)
                    logger.info({"event": "progress", "request_id": request_id, "message": last_msg})

                final_state = state

        # Remove status box after completion
        status_box.empty()

        # Post-processing
        processed = final_state.get("processed_questions", []) if final_state else []
        is_valid = final_state.get("is_valid", False) if final_state else False
        validation_message = final_state.get("validation_message", "") if final_state else ""

        logger.info({
            "event": "run_state_summary",
            "request_id": request_id,
            "is_valid": is_valid,
            "processed_count": len(processed)
        })

        if not is_valid:
            st.info(f"{validation_message}")
            logger.info({"event": "run_completed", "request_id": request_id, "status": "invalid", "reason": validation_message})
        else:
            if not processed:
                st.warning("No DataQuestions were produced by the parser.")
                logger.info({"event": "run_completed", "request_id": request_id, "status": "no_dataquestions"})
            else:
                for i, dq in enumerate(processed):
                    ds = getattr(dq, "dataset", None)
                    chart_figure_json = getattr(dq, "chart_figure_json", None)
                    narrative = getattr(dq, "narrative", None)
                    original_text = getattr(dq, "original_text", None)

                    st.subheader(f"Question {i+1}: {original_text}")
                    logger.info({
                        "event": "dq_render_start",
                        "request_id": request_id,
                        "dq_index": i + 1,
                        "original_text": original_text,
                        "has_chart": bool(chart_figure_json),
                        "has_narrative": bool(narrative)
                    })

                    if chart_figure_json:
                        # chart_json_path = f"chart_figure_{i+1}.json"
                        try:
                            # with open(chart_json_path, "w") as f:
                            #     f.write(chart_figure_json)
                            # st.info(f"Chart JSON saved to {chart_json_path}")

                            fig_dict = json.loads(chart_figure_json)
                            fig = go.Figure(fig_dict)
                            st.plotly_chart(fig, use_container_width=True)

                            logger.info({
                                "event": "dq_chart_rendered",
                                "request_id": request_id,
                                "dq_index": i + 1,
                                "chart_json_len": len(chart_figure_json)
                            })
                        except Exception as e:
                            st.error(f"Could not render chart: {e}")
                            logger.exception({
                                "event": "dq_chart_render_error",
                                "request_id": request_id,
                                "dq_index": i + 1,
                                "error": str(e)
                            })

                    if narrative:
                        st.subheader("Analysis")
                        st.write(narrative)
                        logger.info({
                            "event": "dq_narrative_rendered",
                            "request_id": request_id,
                            "dq_index": i + 1,
                            "narrative_len": len(narrative)
                        })

                logger.info({"event": "run_completed", "request_id": request_id, "status": "ok"})

    except Exception as e:
        logger.exception({"event": "run_failed", "request_id": request_id, "error": str(e)})
        st.error("Something went wrong. Check logs for details.")
