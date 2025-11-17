from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
import logging
from config.settings import SETTINGS

class OpenAIChatClient:
    def __init__(self, model: str, temperature: float = 0.0, max_retries: int = 3):
        self.model = model
        self.llm = ChatOpenAI(model=model, temperature=temperature, max_retries=max_retries)
        self.log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".services.llm")

    # Accepts LangChain BaseMessage[] from ChatPromptTemplate.format_messages(...)
    # Synchronous version
    def complete(self, messages: List[Any]) -> str:
        resp = self.llm.invoke(messages)
        # Try to extract and log usage tokens for evaluation (prompt/completion/total)
        prompt_t: Optional[int] = None
        compl_t: Optional[int] = None
        total_t: Optional[int] = None

        # LangChain AIMessage commonly carries usage in usage_metadata
        usage = getattr(resp, "usage_metadata", None)
        if isinstance(usage, dict):
            prompt_t = usage.get("input_tokens") or usage.get("prompt_tokens")
            compl_t = usage.get("output_tokens") or usage.get("completion_tokens")
            total_t = usage.get("total_tokens")

        # Some providers attach token usage under response_metadata
        if prompt_t is None or compl_t is None or total_t is None:
            meta = getattr(resp, "response_metadata", None)
            if isinstance(meta, dict):
                # OpenAI LC often records under token_usage
                tok = meta.get("token_usage") or meta.get("usage")
                if isinstance(tok, dict):
                    prompt_t = prompt_t or tok.get("prompt_tokens") or tok.get("input_tokens")
                    compl_t = compl_t or tok.get("completion_tokens") or tok.get("output_tokens")
                    total_t = total_t or tok.get("total_tokens")

        # Compute fallback total if missing
        if total_t is None and (prompt_t is not None or compl_t is not None):
            try:
                total_t = (prompt_t or 0) + (compl_t or 0)
            except Exception:
                total_t = None

        # Emit a structured usage log if we have anything
        if any(v is not None for v in (prompt_t, compl_t, total_t)):
            payload = {
                "event": "llm_usage",
                "model": self.model,
                "prompt_tokens": int(prompt_t) if isinstance(prompt_t, int) else prompt_t,
                "completion_tokens": int(compl_t) if isinstance(compl_t, int) else compl_t,
                "total_tokens": int(total_t) if isinstance(total_t, int) else total_t,
            }
            try:
                self.log.info(payload)
            except Exception:
                pass

        return resp.content

    def with_structured_output(self, output_schema):
        return self.llm.with_structured_output(output_schema)
    
    # Optional: keep async too, if we ever need it - something I have to explore later
    # Asynchronous version
    async def acomplete(self, messages: List[Dict[str, Any]]) -> str:
        resp = await self.llm.ainvoke(messages)
        return resp.content


