import json
import os
from typing import Any

import requests
from gnews import GNews
from langchain_core.tools import StructuredTool


def _get_fmp_api_key() -> str:
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        raise ValueError("FMP_API_KEY is not set")
    return api_key


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def get_valuation(symbol: str) -> str:
    api_key = _get_fmp_api_key()
    url = f"https://financialmodelingprep.com/api/v3/discounted-cash-flow/{symbol}?apikey={api_key}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data:
        return _safe_json({})
    return _safe_json(data)


def get_symbol_data(symbol: str) -> str:
    api_key = _get_fmp_api_key()
    base_url = "https://financialmodelingprep.com/api/v3"
    endpoints = {
        "profile": f"/profile/{symbol}",
        "quote": f"/quote/{symbol}",
        "income_statement": f"/income-statement/{symbol}",
        "analyst_ratings": f"/rating/{symbol}",
    }
    stock_data: dict[str, Any] = {}

    for endpoint_name, endpoint_url in endpoints.items():
        url = f"{base_url}{endpoint_url}?apikey={api_key}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data:
            stock_data[endpoint_name] = data[0] if isinstance(data, list) else data
        else:
            stock_data[endpoint_name] = {}

    valuation = json.loads(get_valuation(symbol))
    stock_data["valuation"] = valuation
    return _safe_json(stock_data)


def get_news(ticker: str) -> str:
    google_news = GNews(language="en", period="90d")
    stock_news = google_news.get_news(f"{ticker} stock news")
    publishers = ["Yahoo Finance", "Bloomberg", "The Motley Fool"]
    filtered_news = []
    for news in stock_news[:10]:
        publisher = news.get("publisher", {}).get("title")
        if publisher in publishers:
            filtered_news.append(news)
    return _safe_json(filtered_news)


def stock_pricing_pe(eps: float, industry: str, pe_ratio: float | None = None) -> str:
    industry_key = industry.lower().replace(" ", "")
    default_pe_by_industry = {
        "technology": 30,
        "finance": 15,
        "healthcare": 25,
        "energy": 20,
        "consumer": 20,
        "industrial": 20,
        "utilities": 15,
        "materials": 20,
        "realestate": 20,
        "telecom": 15,
    }
    ratio = float(pe_ratio) if pe_ratio is not None else default_pe_by_industry.get(industry_key, 10)
    target_price = float(eps) * ratio
    return _safe_json(
        {
            "target_price": target_price,
            "industry": industry,
            "pe_ratio": ratio,
        }
    )


def get_tools() -> list[StructuredTool]:
    return [
        StructuredTool.from_function(
            func=get_symbol_data,
            name="get_symbol_data",
            description="Get company profile, quote, income statement, analyst ratings, and valuation data for a stock symbol.",
        ),
        StructuredTool.from_function(
            func=get_news,
            name="get_news",
            description="Get recent English-language stock news for a company ticker.",
        ),
        StructuredTool.from_function(
            func=stock_pricing_pe,
            name="stock_pricing_pe",
            description="Estimate a target stock price using EPS, industry, and an optional PE ratio.",
        ),
    ]
