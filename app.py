# Import necessary libraries
from openai._client import OpenAI
import streamlit as st
import requests
import numpy_financial as npf
import time
import numpy as np
import json
import requests
from streamlit_extras.stylable_container import stylable_container
import os
import sys
from gnews import GNews
import yfinance as yf
import matplotlib.pyplot as plt
sys.path.append('/')

#fetch API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")
fmp_api_key = os.getenv("FMP_API_KEY")
assistant_id = 'asst_uoTf4l8h8zbe6kd6PqzoU6Qf' # financial advisor agent
st.session_state.start_chat = False
# Initialize session state variables
if "file_id_list" not in st.session_state:
    st.session_state.file_id_list = []

# Set up the Streamlit page with a title and icon
st.set_page_config(page_title="Financial Advisor App", page_icon=":speech_balloon:")

# Create a sidebar for API key configuration and additional features
st.sidebar.header("Configuration")
# input box for openai api key
api_key = st.sidebar.text_input("Enter your OpenAI API key", type="password")
fmp_api_key = st.sidebar.text_input("Enter your Financial Modeling Prep API key", type="password")
st.sidebar.markdown(
    """
    You can get an API key from [OpenAI](https://platform.openai.com/signup) and [Financial Modeling Prep](https://financialmodelingprep.com/developer/docs/)
    """
)
if api_key and fmp_api_key:
    OpenAI.api_key = api_key
    client = OpenAI(api_key=api_key)
    st.session_state.start_chat = True
    st.session_state.msgs = []

    if "thread_id" not in st.session_state:
        assistant = client.beta.assistants.retrieve(assistant_id)
        st.session_state.assistant_instructions = assistant.instructions
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
        print(f'Thread ID: {thread.id}')

if "trigger_assistant" not in st.session_state:
    st.session_state.trigger_assistant = False

import requests
import json

def get_symbol_data(symbol):
    """
    Retrieves and combines stock data from Financial Modeling Prep API.

    Args:
        symbol (str): The stock symbol (e.g., 'AAPL')
        api_key (str): Your Financial Modeling Prep API key

    Returns:
        dict: A dictionary containing the combined stock data
    """
    base_url = 'https://financialmodelingprep.com/api/v3'

    endpoints = {
        'profile': f'/profile/{symbol}',
        'quote': f'/quote/{symbol}',
        'income-statement': f'/income-statement/{symbol}',
        # 'news': f'/stock_news?tickers={symbol}&limit=5',  # Get 5 headlines
        'analyst-ratings': f'/rating/{symbol}'  # Research (analyst ratings)
    }

    stock_data = {}
    for endpoint_name, endpoint_url in endpoints.items():
        url = base_url + endpoint_url + f'?apikey={fmp_api_key}'
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if data:  # Some endpoints might return a list
                stock_data[endpoint_name] = data[0] if isinstance(data, list) else data
            else:
                print(f"No data for endpoint: {endpoint_name}")
        else:
            print(f"API request failed for {endpoint_name}: {response.status_code}")

    # Add valuation for a more complete picture 
    stock_data['valuation'] = get_valuation(symbol, api_key)
    # convert to string for OPENAI Assistant API
    stock_data_str = json.dumps(stock_data)
    return stock_data_str

def get_news(ticker):

    google_news = GNews(language="en", period="90d")
    stock_news = google_news.get_news(f"{ticker}+' stock news'")
    filtered_news = []

    publishers = ["Yahoo Finance", "Bloomberg", "The Motley Fool"] #You can select your publishers
    for news in stock_news[:10]:
        if news["publisher"]["title"] in publishers:
            filtered_news.append(news)
    filtered_news = json.dumps(filtered_news)
    return filtered_news

def get_valuation(symbol, api_key):
    """Fetches valuation metrics (e.g., DCF)."""
    url = f'https://financialmodelingprep.com/api/v3/discounted-cash-flow/{symbol}?apikey={api_key}'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data:
            return data
    return {}  # Return empty in case of errors or no data

# stock pricing using pe ratio
def stock_pricing_pe(eps, industry, pe_ratio=None):
    """Calculates the stock price using the price-to-earnings (PE) ratio."""
    # pares eps to float
    eps = float(eps)
    if pe_ratio == None:
        # Get the average PE ratio for the industry
        pe_by_industry = {
            'technology': 30,
            'finance': 15,
            'healthcare': 25,
            'energy': 20,
            'consumer': 20,
            'industrial': 20,
            'utilities': 15,
            'materials': 20,
            'realestate': 20,
            'telecom': 15
        }
        pe_ratio = pe_by_industry.get(industry, 10)  # Default to 20 if industry not found
    else:
        pe_ratio = float(pe_ratio)

    return {"target_price": eps * pe_ratio, "industry": industry, "pe_ratio": pe_ratio}
    
# Define the function to process messages with citations
def process_message_with_citations(message):
    """Extract content and annotations from the message and format citations as footnotes."""
    #  handle MessageContentImageFile
    if message.content[0].type == "image":
        return f"![{message.content[0].filename}]({message.content[0].url})"
    else:
        message_content = message.content[0].text
    annotations = message_content.annotations if hasattr(message_content, 'annotations') else []
    citations = []

    # Iterate over the annotations and add footnotes
    for index, annotation in enumerate(annotations):
        # Replace the text with a footnote
        message_content.value = message_content.value.replace(annotation.text, f' [{index + 1}]')

        # Gather citations based on annotation attributes
        if (file_citation := getattr(annotation, 'file_citation', None)):
            # Retrieve the cited file details (dummy response here since we can't call OpenAI)
            cited_file = {'filename': 'cited_document.pdf'}  # This should be replaced with actual file retrieval
            citations.append(f'[{index + 1}] {file_citation.quote} from {cited_file["filename"]}')
        elif (file_path := getattr(annotation, 'file_path', None)):
            # Placeholder for file download citation
            cited_file = {'filename': 'downloaded_document.pdf'}  # This should be replaced with actual file retrieval
            citations.append(f'[{index + 1}] Click [here](#) to download {cited_file["filename"]}')  # The download link should be replaced with the actual download path

    # Add footnotes to the end of the message content
    full_response = message_content.value + '\n\n' + '\n'.join(citations)
    return full_response


if "trigger_assistant" not in st.session_state:
    st.session_state.trigger_assistant = False

if "msgs" not in st.session_state:
    st.session_state.msgs = []

# Main chat interface setup
st.title("Stock Expert")
st.write("Ask questions about stock valuation, financials, and more!")

if st.session_state.msgs == []:
    st.markdown("""
        Hi, I'm Stock Financial Advisor. Provide me with the name or symbol of a stock and I will provide you with a detailed analysis of the stock.
        """)

# Only show the chat interface if the chat has been started
if st.session_state.start_chat:

    # Display existing messages in the chat
    for message in st.session_state.msgs:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    
    # Chat input for the user
    prompt = st.chat_input("e.g. AAPL or Microsoft", key="chat_input")
    if prompt or st.session_state.trigger_assistant:
        
        if st.session_state.trigger_assistant:
            print("trigger assistant")
            prompt = st.session_state.trigger_assistant
            st.session_state.trigger_assistant = False

        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.msgs.append({"role": "user", "content": prompt})
        msgs = st.session_state.msgs

        with st.spinner("Thinking..."):
            thread_id = st.session_state.thread_id
            # Add the user's message to the existing thread
            client.beta.threads.messages.create(
                thread_id=st.session_state.thread_id,
                role="user",
                content=prompt
            )

            # Create a run with additional instructions
            run = client.beta.threads.runs.create(
                thread_id=st.session_state.thread_id,
                assistant_id=assistant_id,
                #this instruction will overwrite the instruction in the assistant
                # instructions=st.session_state.assistant_instructions + "\n\n" + "", 
            )

            # Poll for the run to complete and retrieve the assistant's messages

            while run.status != 'completed':
                run = client.beta.threads.runs.retrieve(
                    thread_id=st.session_state.thread_id,
                    run_id=run.id
                )
                time.sleep(1)
                if run.status == "requires_action":
                    tools_output = []
                    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                        f = tool_call.function
                        print(f)
                        f_name = f.name
                        f_args = json.loads(f.arguments)

                        print(f"Launching function {f_name} with args {f_args}")
                        tool_result = eval(f_name)(**f_args)
                        tools_output.append(
                            {
                                "tool_call_id": tool_call.id,
                                "output": str(tool_result),
                            }
                        )
                    print(f"Will submit {tools_output}")
                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=st.session_state.thread_id,
                        run_id=run.id,
                        tool_outputs=tools_output,
                    )
                if run.status == "completed":
                    print(f"Run status: {run.status}")
                    
                if run.status == "failed":
                    print("Abort")
                    #print the error message
                    print(run.last_error)

            # Retrieve messages added by the assistant
            messages = client.beta.threads.messages.list(
                thread_id=st.session_state.thread_id
            )

            # Process and display assistant messages
            assistant_messages_for_run = [
                message for message in messages 
                if message.run_id == run.id and message.role == "assistant"
            ]  
            for message in assistant_messages_for_run:
                full_response = process_message_with_citations(message)
                st.session_state.msgs.append({"role": "assistant", "content": full_response})
                with st.chat_message("assistant"):
                    st.markdown(full_response, unsafe_allow_html=True)
        
else:
    # write warning
    st.warning("Please enter your OpenAI API key to start the chat")