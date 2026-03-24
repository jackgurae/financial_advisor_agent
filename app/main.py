import logging
import os
import re

import streamlit as st
from dotenv import load_dotenv

from app.agent import stream_agent
from app.tools import FMPAPIError

load_dotenv()


logger = logging.getLogger(__name__)


_LATEX_BLOCK_PATTERN = re.compile(r"(\$\$.*?\$\$|\\\[.*?\\\])", re.DOTALL)


def _render_chat_content(content: str) -> None:
    with st.container():
        parts = _LATEX_BLOCK_PATTERN.split(content)
        for part in parts:
            if not part:
                continue
            stripped = part.strip()
            if not stripped:
                continue
            if stripped.startswith("$$") and stripped.endswith("$$"):
                st.latex(stripped[2:-2].strip())
                continue
            if stripped.startswith("\\[") and stripped.endswith("\\]"):
                st.latex(stripped[2:-2].strip())
                continue
            st.markdown(part)


def _configure_logging() -> None:
    log_level = os.getenv("APP_LOG_LEVEL", "INFO").upper()
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
    else:
        root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def main() -> None:
    _configure_logging()
    st.set_page_config(page_title="Financial Advisor App", page_icon=":speech_balloon:")

    if "msgs" not in st.session_state:
        st.session_state.msgs = []
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    api_key = os.getenv("OPENAI_API_KEY")
    fmp_api_key = os.getenv("FMP_API_KEY")
    app_password = os.getenv("APP_PASSWORD", "").strip()

    st.title("Stock Expert")
    st.write("Ask questions about stock valuation, financials, and more!")

    if not app_password:
        st.error("APP_PASSWORD must be set in your .env or deployment secrets.")
        return

    if not st.session_state.authenticated:
        password_input = st.text_input("Enter application password", type="password")
        if st.button("Unlock"):
            if password_input == app_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid password")
        return

    if not st.session_state.msgs:
        st.markdown(
            """
        Hi, I'm Stock Financial Advisor. Provide me with the name or symbol of a stock and I will provide you with a detailed analysis of the stock.
        """
        )
        st.info(
            "Responses are formatted as structured markdown sections for easier reading. "
            "Open the 'About This Agent' subpage in the sidebar to inspect the current prompt and tool setup."
        )

    for message in st.session_state.msgs:
        with st.chat_message(message["role"]):
            _render_chat_content(message["content"])

    if not api_key or not fmp_api_key:
        st.warning(
            "Please set OPENAI_API_KEY and FMP_API_KEY in your .env file to start the chat"
        )
        return

    prompt = st.chat_input("e.g. AAPL or Microsoft", key="chat_input")
    if not prompt:
        return

    logger.info("Received user prompt", extra={"prompt_preview": prompt[:120]})

    with st.chat_message("user"):
        _render_chat_content(prompt)
    history = st.session_state.msgs.copy()
    st.session_state.msgs.append({"role": "user", "content": prompt})

    try:
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            with st.spinner("Thinking..."):
                response_parts: list[str] = []
                for chunk in stream_agent(prompt, history):
                    response_parts.append(chunk)
                    response_placeholder.markdown("".join(response_parts))
                response = "".join(response_parts)
    except FMPAPIError as exc:
        logger.warning("FMP API warning", extra={"error": str(exc)})
        st.warning(str(exc))
        return
    except Exception as exc:
        logger.exception("Unhandled agent error")
        st.error(f"Agent error: {exc}")
        return

    if not isinstance(response, str):
        response = str(response)

    response = response.strip()

    if not response:
        st.error("Agent returned no assistant response")
        return

    response_placeholder.empty()
    with response_placeholder.container():
        _render_chat_content(response)

    st.session_state.msgs.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
