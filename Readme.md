# Stock Expert Agent

## Introduction

This is a stock expert agent that can help you to make decisions on stock trading. It has abilities to access the stock data, analyze the stock data, news, and provide recommendation. It is built on OpenAI Assistant API.

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

## FMP API

FMP API provides the stock data and news. [Docs](https://financialmodelingprep.com/developer/docs/)

## gnews API

gnews API provides the news data. [Docs](https://gnews.io/docs/v4)

## How to deploy app on streamlit

1. create repository on github with requirements.txt
2. go to [https://www.streamlit.io/](https://share.streamlit.io/)
3. login and create New App
4. connect to github
5. select the repository
6. make sure you specify the right file to run the app
7. for API keys, you can use the environment variables
8. deploy the app
