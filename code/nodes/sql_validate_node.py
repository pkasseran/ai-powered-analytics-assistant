from states.data_extractor_state import DataExtractorState
from services.sql_validation_service import SQLValidationService
import logging
from config.settings import SETTINGS

log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.sql_validate")

def make_sql_validate_node(validator: SQLValidationService):
    def node(state: DataExtractorState) -> DataExtractorState:
        log.info("Validating SQL...")

        sql = state.get("sql") or ""
        # Truncate to keep logs manageable (tweak 1500 as you like)
        preview = sql if len(sql) <= 1500 else sql[:1500] + f"... (truncated {len(sql)-1500} chars)"
        log.info("Validating SQL (len=%d):\n%s", len(sql), preview)

        is_valid, error = validator.validate(state["sql"])
        if is_valid:
            log.info("SQL validation PASSED")
        else:
            state["validation_attempts"] = state.get("validation_attempts", 0) + 1
            log.info("SQL validation FAILED: %s", error)
            log.info("Validation attempts: %d", state["validation_attempts"])
        return {**state, "is_valid": is_valid, "validation_error": error}
    return node