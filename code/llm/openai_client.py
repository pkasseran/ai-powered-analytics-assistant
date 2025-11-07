from typing import List, Dict, Any
from langchain_openai import ChatOpenAI

class OpenAIChatClient:
    def __init__(self, model: str, temperature: float = 0.0, max_retries: int = 3):
        self.llm = ChatOpenAI(model=model, temperature=temperature, max_retries=max_retries)

    # Accepts LangChain BaseMessage[] from ChatPromptTemplate.format_messages(...)
    # Synchronous version
    def complete(self, messages: List[Any]) -> str:
        resp = self.llm.invoke(messages)
        return resp.content

    def with_structured_output(self, output_schema):
        return self.llm.with_structured_output(output_schema)
    
    # Optional: keep async too, if we ever need it - something I have to explore later
    # Asynchronous version
    async def acomplete(self, messages: List[Dict[str, Any]]) -> str:
        resp = await self.llm.ainvoke(messages)
        return resp.content


