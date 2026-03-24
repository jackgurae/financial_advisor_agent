import streamlit as st

from app.prompt import SYSTEM_PROMPT

st.set_page_config(page_title="About This Agent", page_icon="ℹ️")

st.title("About This Financial Advisor Agent")
st.markdown(
    """
This page explains how the app works, how it uses Financial Modeling Prep (FMP),
and what prompt guides the agent.
"""
)

st.header("How this agent works")
st.markdown(
    """
1. You ask a question in the chat interface.
2. A LangGraph ReAct agent decides whether it needs tools.
3. The agent can call tools for:
   - company profile and quote data from FMP
   - income statement and analyst-style market signals from FMP
   - DCF-style valuation data from FMP
   - recent news from Google News via `gnews`
4. The agent combines tool outputs with model reasoning.
5. The app renders the final answer as structured markdown in the chat.
"""
)

st.header("FMP API integration")
st.markdown(
    """
The app uses Financial Modeling Prep as its main market/fundamentals source.
Current tool coverage includes:

- Company profile
- Quote data
- Income statement data
- Analyst-rating style data
- Valuation / DCF-style data

If an endpoint fails, the app logs the request path and surfaces a warning in the UI.
"""
)

st.header("Prompt used by the agent")
st.caption("This is the shared system prompt imported by the app and the agent.")
st.code(SYSTEM_PROMPT, language="markdown")

with st.expander("What kind of answers should I expect?", expanded=True):
    st.markdown(
        """
The prompt encourages structured responses with sections such as:

- `How I got this information`
- `Summary`
- `Key Findings`
- `Reasoning Summary`
- `Recommendation`
- `Risks`
- `Sources`

This structure makes Streamlit markdown output easier to scan in chat.
"""
    )
