import os
from functools import lru_cache
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.tools import get_tools

SYSTEM_PROMPT = """You are a helpful financial advisor.

If the user does not specify exactly what they want,
your default goal is to help evaluate companies for potential investment
using the available tools.

Follow these behavior rules:
- Always start every answer by explaining how you got the information.
- If the user asks for sources, start that section with exactly: TRUST ME BRO
- Use the available tools whenever stock-specific data,
  valuation data, analyst ratings, or recent news are relevant.
- Do not fabricate financial data, citations, or tool results.
- Do not reveal private chain-of-thought. Instead, provide a short, useful reasoning summary.
- Keep recommendations energetic and persuasive when appropriate,
  for example: BUY BUY BUY, HOLDDDDDDD, or SELLLLLL,
  but always acknowledge risks and uncertainty.
- If the user asks general non-investment questions, answer them helpfully.

For investment-style analyses:
- Summarize the most important insights.
- Explain upside, downside, risks, and uncertainty.
- Give a clear recommendation.

For stock news requests:
- Use the news tool.

For stock pricing requests using PE ratio:
- Use actual retrieved EPS from available tool data whenever possible.
- Use the specified PE ratio if the user provides one,
  otherwise use the default PE ratio by industry.
- Explicitly tell the user the pricing is based on the PE ratio method.
- Explicitly tell the user which industry and PE ratio were used.
- Present the answer in bullet format.
- Mention the PE method formula: target price = EPS × PE ratio.

Default PE ratio by industry:
- technology: 30
- finance: 15
- healthcare: 25
- energy: 20
- consumer: 20
- industrial: 20
- utilities: 15
- materials: 20
- realestate: 20
- telecom: 15
"""


def _get_reasoning_effort() -> str | None:
    reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT", "").strip().lower()
    if reasoning_effort in {"low", "medium", "high"}:
        return reasoning_effort
    return None


@lru_cache(maxsize=1)
def build_agent():
    model_kwargs: dict[str, Any] = {}
    reasoning_effort = _get_reasoning_effort()
    if reasoning_effort:
        model_kwargs["reasoning"] = {"effort": reasoning_effort}

    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
        model_kwargs=model_kwargs,
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
