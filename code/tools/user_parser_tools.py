from langchain.tools import tool
from typing import Optional

@tool
def alias_to_canonical(word: str, registry: dict) -> str:
    """
    Maps a word (metric, dimension, or alias) to its canonical name using a registry.
    Args:
        word: The word to map (e.g., metric, dimension, or alias).
        registry: Dictionary containing 'aliases', 'metrics', and 'dimensions'.
    Returns:
        The canonical name if found, otherwise returns the original word.
    """
    aliases = registry.get('aliases', {})
    for canon, syns in aliases.items():
        if word.lower() == canon.lower() or word.lower() in [s.lower() for s in syns]:
            return canon
        if word.lower() in [m.lower() for m in registry.get('metrics', [])]:
            return word
        if word.lower() in [d.lower() for d in registry.get('dimensions', [])]:
            return word
    return word

@tool
def try_map_template(metric: Optional[str], time_grain: Optional[str], group_by_cnt: int, tmpl_rules: dict) -> Optional[str]:
    """
    Maps a metric, time grain, and group-by count to a template ID using template rules.
    Args:
        metric: The metric name to match.
        time_grain: The time grain (e.g., 'daily', 'monthly').
        group_by_cnt: Number of group-by dimensions.
        tmpl_rules: Dictionary containing template mapping rules.
    Returns:
        The template ID if a matching rule is found, otherwise None.
    """
    if not metric:
        return None
    for rule in tmpl_rules.get('rules', []):
        when = rule.get('when', {})
        if when.get('metric') == metric and when.get('time_grain') == time_grain and when.get('group_by_count') == group_by_cnt:
            return rule.get('template_id')
    return None


""" 
NOTE TO SELF: How to use these tools
Tools can also be used directly in your code.
just import it "from tools import alias_to_canonical, try_map_template"
and use them as regular functions.

However, you can also used them as agent-driven invocation
Suppose you want an agent to be able to call these tools dynamically as part of its reasoning. You would:

Register the tools with @tool (already done).
Add them to the agent’s tool list.
Use an agent (e.g., an LLM agent) that can call tools by name.

#################################################################
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from tools import alias_to_canonical, try_map_template

# Wrap your tool functions as LangChain Tool objects
tools = [
    Tool.from_function(alias_to_canonical),
    Tool.from_function(try_map_template),
]

# Initialize the LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Create the agent with the tools
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS,  # or another agent type that supports tool usage
    verbose=True,
)

# Example usage: ask the agent to canonicalize a metric
result = agent.run("Canonicalize the metric 'revenue' using the registry {'aliases': {'revenue': ['sales']}, 'metrics': ['revenue'], 'dimensions': []}")
print(result)

# Or: ask the agent to map a template
result = agent.run("Find the template for metric 'revenue', time grain 'monthly', group by 2, using rules {'rules': [{'when': {'metric': 'revenue', 'time_grain': 'monthly', 'group_by_count': 2}, 'template_id': 'monthly_revenue_by_2'}]}")
print(result)

#################################################################


How it works:

The agent receives a user query.
It decides which tool to call (e.g., alias_to_canonical or try_map_template) based on the query.
It calls the tool, passing the required arguments.
The result is returned to the user.
Summary:
Agent-driven usage means the agent can call your tools as actions, not just as direct function calls. This enables flexible, dynamic workflows and reasoning.
"""