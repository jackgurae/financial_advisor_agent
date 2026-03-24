import os

import streamlit as st
from dotenv import load_dotenv

from app.agent import run_agent

load_dotenv()


def main() -> None:
    st.set_page_config(page_title="Financial Advisor App", page_icon=":speech_balloon:")

    if "msgs" not in st.session_state:
        st.session_state.msgs = []
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    st.sidebar.header("Configuration")

    api_key = os.getenv("OPENAI_API_KEY")
    fmp_api_key = os.getenv("FMP_API_KEY")
    app_password = os.getenv("APP_PASSWORD")

    st.title("Stock Expert")
    st.write("Ask questions about stock valuation, financials, and more!")

    if app_password:
        if not st.session_state.authenticated:
            password_input = st.text_input(
                "Enter application password", type="password"
            )
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
