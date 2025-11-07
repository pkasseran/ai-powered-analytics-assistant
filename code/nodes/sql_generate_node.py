from services.sql_generation_service import SQLGenerationService, SQLGenerationInput
from models.data_extractor_model import DataQuestionInfo
from states.data_extractor_state import DataExtractorState
from config.settings import SETTINGS
import logging

log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.sql_generate")

def make_sql_generate_node(gen: SQLGenerationService):
    def node(state: DataExtractorState) -> DataExtractorState:
        # Convert DataQuestion to DataQuestionInfo and prepare SQLGenerationInput
        dq_info = DataQuestionInfo.from_dataquestion(state["data_question"])
        payload = SQLGenerationInput(
            semantic=state["semantic"],
            original_text=dq_info.original_text,
            metrics=dq_info.metrics,
            dimensions=dq_info.dimensions,
            time_grain=dq_info.time_grain,
            time_range=dq_info.time_range,
            filters=dq_info.filters,
            sort=dq_info.sort,
            top_k=dq_info.top_k,
            previous_validation_error=(
                state["validation_error"]["message"]
                if state.get("validation_error")
                else None
            ),
        )
        sql = gen.generate_sql(payload)
        log.info("SQL generated (len=%d)", len(sql))
        return {**state, "sql": sql}
    return node
