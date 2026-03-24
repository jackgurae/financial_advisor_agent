import logging
import os
from collections.abc import Iterator
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
            streaming=True,
        )
    else:
        model = ChatOpenAI(
            model=model_name,
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY"),
            streaming=True,
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


def _log_agent_chunk(chunk: Any, metadata: dict[str, Any]) -> None:
    node_name = metadata.get("langgraph_node", "unknown")
    logger.debug(
        "Agent stream chunk received",
        extra={
            "langgraph_node": node_name,
            "metadata_keys": sorted(metadata.keys()),
            "chunk_type": type(chunk).__name__,
        },
    )

    tool_calls = getattr(chunk, "tool_calls", None)
    if tool_calls:
        logger.info(
            "Agent requested tool calls",
            extra={
                "langgraph_node": node_name,
                "tool_calls": tool_calls,
            },
        )

    content = getattr(chunk, "content", None)
    text = _message_to_text(content).strip() if content is not None else ""
    if text:
        logger.debug(
            "Agent text chunk",
            extra={
                "langgraph_node": node_name,
                "text_preview": text[:300],
            },
        )


def _build_messages(
    user_input: str, history: list[dict[str, str]]
) -> list[HumanMessage | AIMessage]:
    messages: list[HumanMessage | AIMessage] = []
    for message in history:
        role = message.get("role")
        content = message.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=user_input))
    return messages


def stream_agent(user_input: str, history: list[dict[str, str]]) -> Iterator[str]:
    logger.info(
        "Streaming agent",
        extra={
            "history_length": len(history),
            "user_input_preview": user_input[:120],
        },
    )
    agent = build_agent()
    messages = _build_messages(user_input, history)

    for chunk, metadata in agent.stream(
        {"messages": messages},
        stream_mode="messages",
    ):
        _log_agent_chunk(chunk, metadata)
        if metadata.get("langgraph_node") == "tools":
            text = _message_to_text(getattr(chunk, "content", "")).strip()
            if text:
                logger.info(
                    "Tool node response received",
                    extra={"text_preview": text[:500]},
                )
        if metadata.get("langgraph_node") != "agent":
            continue
        text = _message_to_text(chunk.content)
        if text:
            yield text


def run_agent(user_input: str, history: list[dict[str, str]]) -> str:
    logger.info(
        "Running agent",
        extra={
            "history_length": len(history),
            "user_input_preview": user_input[:120],
        },
    )
    agent = build_agent()
    messages = _build_messages(user_input, history)

    result = agent.invoke({"messages": messages})
    result_messages = result.get("messages", [])
    logger.info(
        "Agent invocation completed",
        extra={"result_message_count": len(result_messages)},
    )
    for message in reversed(result_messages):
        if isinstance(message, AIMessage):
            text = _message_to_text(message.content).strip()
            if text:
                logger.debug(
                    "Returning final AI response",
                    extra={"text_preview": text[:500]},
                )
                return text
    raise ValueError("Agent returned no assistant response")
