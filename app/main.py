import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from app.agent import run_agent

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
IMAGE_PATH = ROOT_DIR / "QR_phatra.jpg"


def main() -> None:
    st.set_page_config(page_title="Financial Advisor App", page_icon=":speech_balloon:")

    if "msgs" not in st.session_state:
        st.session_state.msgs = []

    st.sidebar.header("Configuration")
    if IMAGE_PATH.exists():
        st.sidebar.image(str(IMAGE_PATH), use_container_width=True)

    api_key = os.getenv("OPENAI_API_KEY")
    fmp_api_key = os.getenv("FMP_API_KEY")

    st.title("Stock Expert")
    st.write("Ask questions about stock valuation, financials, and more!")

    if not st.session_state.msgs:
        st.markdown(
            """
        Hi, I'm Stock Financial Advisor. Provide me with the name or symbol of a stock and I will provide you with a detailed analysis of the stock.
        """
        )

    for message in st.session_state.msgs:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if not api_key or not fmp_api_key:
        st.warning(
            "Please set OPENAI_API_KEY and FMP_API_KEY in your .env file to start the chat"
        )
        return

    prompt = st.chat_input("e.g. AAPL or Microsoft", key="chat_input")
    if not prompt:
        return

    with st.chat_message("user"):
        st.markdown(prompt)
    history = st.session_state.msgs.copy()
    st.session_state.msgs.append({"role": "user", "content": prompt})

    try:
        with st.spinner("Thinking..."):
            response = run_agent(prompt, history)
    except Exception as exc:
        st.error(f"Agent error: {exc}")
        return

    st.session_state.msgs.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)


if __name__ == "__main__":
    main()
