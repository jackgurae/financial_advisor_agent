import os
from functools import lru_cache
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.tools import get_tools

SYSTEM_PROMPT = """You are a financial advisor agent. Help users analyze public stocks using the available tools. Use tools when stock-specific data, valuation data, or recent news would improve the answer. Be clear about uncertainty, avoid fabricating facts, and provide balanced analysis rather than absolute investment advice."""


@lru_cache(maxsize=1)
def build_agent():
    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    tools = get_tools()
    try:
        return create_react_agent(model=model, tools=tools, prompt=SYSTEM_PROMPT)
    except TypeError:
        return create_react_agent(model=model, tools=tools, state_modifier=SYSTEM_PROMPT)


def _message_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                elif isinstance(text, dict):
                    value = text.get("value")
                    if value:
                        parts.append(str(value))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content)


def run_agent(user_input: str, history: list[dict[str, str]]) -> str:
    agent = build_agent()
    messages = []
    for message in history:
        role = message.get("role")
        content = message.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=user_input))

    result = agent.invoke({"messages": messages})
    result_messages = result.get("messages", [])
    for message in reversed(result_messages):
        if isinstance(message, AIMessage):
            text = _message_to_text(message.content).strip()
            if text:
                return text
    raise ValueError("Agent returned no assistant response")
