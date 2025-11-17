import logging
from states.charting_state import ChartingState
from services.charting_service_llm import ChartingServiceLLM
import json
from config.settings import SETTINGS
from utils.agent_logging_json import get_current_test_id
from pathlib import Path

log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.chart_validate")

def make_chart_validate_node(validator: ChartingServiceLLM):
	def node(state: ChartingState) -> ChartingState:
		log.info("Validating chart JSON...")
		fig_json = state.get("plotly_fig_json", None)
		preview = str(fig_json)[:1500] + ("... (truncated)" if fig_json and len(str(fig_json)) > 1500 else "")
		log.info("Chart JSON preview (len=%d):\n%s", len(str(fig_json)) if fig_json else 0, preview)
		# Emit full figure in a separate structured log line for evaluation (avoid truncation issues)
		try:
			if isinstance(fig_json, dict):
				full_json = json.dumps(fig_json)
			else:
				# Already a JSON string or repr; attempt to load then re-dump for normalization
				loaded = json.loads(fig_json) if fig_json else None
				full_json = json.dumps(loaded) if loaded is not None else None
			if full_json:
				log.info("chart_full_json:%s", full_json)
				# Option B: persist full figure JSON to logs/charts/<test_id>.json
				try:
					tid = get_current_test_id()
					charts_dir = SETTINGS.ROOT_DIR / "logs" / "charts"
					charts_dir.mkdir(parents=True, exist_ok=True)
					fname = f"{tid}.json" if tid else "chart.json"
					out_path = charts_dir / fname
					with open(out_path, "w", encoding="utf-8") as fh:
						fh.write(full_json)
					log.info("Saved chart JSON to %s", str(out_path))
				except Exception as _e2:
					pass
		except Exception as _e:
			# Non-fatal; evaluator will fall back to preview
			pass
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

