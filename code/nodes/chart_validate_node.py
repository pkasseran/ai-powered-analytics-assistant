import logging
from states.charting_state import ChartingState
from services.charting_service_llm import ChartingServiceLLM
import json
from config.settings import SETTINGS

log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.chart_validate")

def make_chart_validate_node(validator: ChartingServiceLLM):
	def node(state: ChartingState) -> ChartingState:
		log.info("Validating chart JSON...")
		fig_json = state.get("plotly_fig_json", None)
		preview = str(fig_json)[:1500] + ("... (truncated)" if fig_json and len(str(fig_json)) > 1500 else "")
		log.info("Chart JSON preview (len=%d):\n%s", len(str(fig_json)) if fig_json else 0, preview)
		if not isinstance(fig_json, dict):
			fig_dict = json.loads(fig_json)  # fig_json is a string
		else:
			fig_dict = fig_json

		try:
			#is_valid = validator.validate_plotly_fig_json(fig_dict)
			is_valid = validator.validate_chart(fig_dict)
			error = None
			log.info("Chart validation PASSED")
		except Exception as e:
			is_valid = False
			error = str(e)
			state["validation_attempts"] = state.get("validation_attempts", 0) + 1
			log.info("Chart validation FAILED: %s", error)
			log.info("Validation attempts: %d", state["validation_attempts"])
		return {**state, "is_valid": is_valid, "validation_error": error}
	return node

