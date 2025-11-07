from services.parsing_validation_service import ParsingValidationService
from states.parser_state import UserRequestParserState
from config.settings import SETTINGS

import logging
from config.settings import SETTINGS
log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.user_request_parser")

# Path to metrics.yaml
METRICS_YAML_PATH = str(SETTINGS.ROOT_DIR / "config" / "ag_user_query_parser_config" / "metrics.yaml")
validator = ParsingValidationService(METRICS_YAML_PATH)

def make_parser_validation_node():
    def node(state: UserRequestParserState) -> UserRequestParserState:
        parsed = state.get("parsed")
        is_valid, validation_message = validator.validate_agent_output(parsed)
        log.info("Parser validation: is_valid=%s, message=%s", is_valid, validation_message)
        return {
            **state,
            "is_valid": is_valid,
            "validation_message": validation_message,
        }
    return node
