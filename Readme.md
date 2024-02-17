# Stock Expert Agent with Function Calling

## Introduction

This is a stock expert agent that can help you to make decisions on stock trading. It has abilities to access the stock data, analyze the stock data, news, and provide recommendation. It is built on OpenAI Assistant API.

## Why need function calling?

![Why need function calling](https://miro.medium.com/v2/resize:fit:1400/format:webp/1*gWh9ICOtpjb0sJxoqb0eUQ.png)
Function calling allow user to use natural language to call task/function correctly. It also allows user to pass parameters to the function.

## OpenAI Assistant API

OpenAI Assistant API is a powerful tool that can help you to build a conversational AI.

<!-- insert image url-->

![OpenAI Assistant API](https://cdn.openai.com/API/docs/images/diagram-assistant.webp)
Source: [OPENAI - How Assistants work](https://platform.openai.com/docs/assistants/how-it-works/objects)

| OBJECT    | WHAT IT REPRESENTS                                                                                                                                                                                                           |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Assistant | Purpose-built AI that uses OpenAI’s models and calls tools                                                                                                                                                                   |
| Thread    | A conversation session between an Assistant and a user. Threads store Messages and automatically handle truncation to fit content into a model’s context.                                                                    |
| Message   | A message created by an Assistant or a user. Messages can include text, images, and other files. Messages stored as a list on the Thread.                                                                                    |
| Run       | An invocation of an Assistant on a Thread. The Assistant uses its configuration and the Thread’s Messages to perform tasks by calling models and tools. As part of a Run, the Assistant appends Messages to the Thread.      |
| Run Step  | A detailed list of steps the Assistant took as part of a Run. An Assistant can call tools or create Messages during its run. Examining Run Steps allows you to introspect how the Assistant is getting to its final results. |

### how assistant API run works

![Assistant API Run](https://miro.medium.com/v2/resize:fit:1400/format:webp/0*4UeouxPZ5cx0JeAh.png)
Run is asynchrounous. So we need to wait for the run to complete before we can get the result. We can get the result when status is `completed`.

## Create Assistant (No-code)

1. Go to [OpenAI](https://platform.openai.com/). Login or create an account.
2. Navigate to the `Assistants` tab.
3. Click on `+ Create` to start creating a new assistant.
   ![OpenAI Interface](https://i.imgur.com/yzpMgUV.png)
4. Fill in the details for the assistant. Name, prompt, function, code interpreter, and files.
   4.1 for Function calling, we need to specify schema. e.g.
   ```json
   {
     "name": "get_news",
     "description": "Get latest news on specified stock name or symbol. Return headline and links.",
     "parameters": {
       "type": "object",
       "properties": {
         "ticker": {
           "type": "string",
           "description": "Symbol of stock or company name. Used as a query for stock data API calling"
         }
       },
       "required": ["ticker"]
     }
   }
   ```
5. to use the assistant, grab assistant id from the settings.

## FMP API

FMP API provides the stock data and news. [Docs](https://financialmodelingprep.com/developer/docs/)

## gnews API

gnews API provides the news data. [Docs](https://gnews.io/docs/v4)

# How to deploy app on streamlit

1. create repository on github with requirements.txt
2. go to [https://www.streamlit.io/](https://share.streamlit.io/)
3. login and create New App
4. connect to github
5. select the repository
6. make sure you specify the right file to run the app
7. for API keys, you can use the environment variables
8. deploy the app

**Appendix**:

- [Mastering OpenAI Assistants API: Building an AI Financial Analyst to Forecast Stock Trend](https://levelup.gitconnected.com/mastering-openai-assistants-api-building-an-ai-financial-analyst-to-forecast-stock-trend-17a45c77607a)
