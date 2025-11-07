from states.data_extractor_state import DataExtractorState
from services.data_extraction_service import DataExtractionService
import logging
from config.settings import SETTINGS
log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.sql_extract")

def make_sql_extract_node(extractor: DataExtractionService):
    def node(state: DataExtractorState) -> DataExtractorState:
        log.info("Executing SQL and loading DataFrame...")
        df = extractor.run_query(state["sql"])
        log.info("DataFrame ready (rows=%d, cols=%d)", df.shape[0], df.shape[1])
        return {**state, "df": df}
    return node
