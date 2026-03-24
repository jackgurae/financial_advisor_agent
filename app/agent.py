import logging
import os
from functools import lru_cache
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.prompt import SYSTEM_PROMPT
from app.tools import get_tools

logger = logging.getLogger(__name__)


def _get_reasoning_effort() -> str | None:
    reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT", "").strip().lower()
    if reasoning_effort in {"low", "medium", "high"}:
        return reasoning_effort
    return None


def _supports_reasoning_effort(model_name: str) -> bool:
    """Check if the model supports the reasoning_effort parameter (o1-series models)."""
    return model_name.startswith(("o1-", "o3-"))


@lru_cache(maxsize=1)
def build_agent():
    reasoning_effort = _get_reasoning_effort()
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    logger.debug(
        "Building agent",
        extra={
            "model_name": model_name,
            "reasoning_effort": reasoning_effort or "default",
        },
    )

    if reasoning_effort and _supports_reasoning_effort(model_name):
        model = ChatOpenAI(
            model=model_name,
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY"),
            reasoning={"effort": reasoning_effort},
        )
    else:
        model = ChatOpenAI(
            model=model_name,
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    tools = get_tools()
    try:
        return create_react_agent(model=model, tools=tools, prompt=SYSTEM_PROMPT)
    except TypeError:
        return create_react_agent(
            model=model, tools=tools, state_modifier=SYSTEM_PROMPT
        )


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
    logger.info(
        "Running agent",
        extra={
            "history_length": len(history),
            "user_input_preview": user_input[:120],
        },
    )
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
