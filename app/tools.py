import json
import logging
import os
from typing import Any

import requests
from gnews import GNews
from langchain_core.tools import StructuredTool


logger = logging.getLogger(__name__)
FMP_STABLE_BASE_URL = "https://financialmodelingprep.com/stable"


class FMPAPIError(RuntimeError):
    pass


def _get_fmp_api_key() -> str:
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        raise ValueError("FMP_API_KEY is not set")
    return api_key


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _extract_first_record(data: Any) -> Any:
    if isinstance(data, list):
        return data[0] if data else {}
    return data if data else {}


def _call_fmp(endpoint_name: str, path: str, **params: Any) -> Any:
    api_key = _get_fmp_api_key()
    url = f"{FMP_STABLE_BASE_URL}/{path}"
    request_params = {**params, "apikey": api_key}
    logger.debug(
        "Calling FMP endpoint",
        extra={
            "endpoint_name": endpoint_name,
            "url": url,
            "params": {
                key: value for key, value in request_params.items() if key != "apikey"
            },
        },
    )
    response = requests.get(url, params=request_params, timeout=30)
    _raise_for_fmp_response(response, endpoint_name)
    return response.json()


def _call_fmp_with_fallback(
    endpoint_name: str,
    primary_path: str,
    fallback_path: str | None = None,
    **params: Any,
) -> Any:
    try:
        return _call_fmp(endpoint_name, primary_path, **params)
    except FMPAPIError as exc:
        if fallback_path is None or "status 404" not in str(exc):
            raise
        logger.warning(
            "FMP endpoint fallback triggered",
            extra={
                "endpoint_name": endpoint_name,
                "primary_path": primary_path,
                "fallback_path": fallback_path,
            },
        )
        return _call_fmp(endpoint_name, fallback_path, **params)


def _raise_for_fmp_response(response: requests.Response, endpoint_name: str) -> None:
    if response.ok:
        return

    response_text = response.text.strip()
    logger.warning(
        "FMP API request failed",
        extra={
            "endpoint_name": endpoint_name,
            "status_code": response.status_code,
            "url": response.url,
            "response_preview": response_text[:300],
        },
    )

    try:
        payload = response.json()
    except ValueError:
        payload = None

    error_message = ""
    if isinstance(payload, dict):
        error_message = str(payload.get("Error Message", "")).strip()

    if response.status_code == 403 and "Legacy Endpoint" in error_message:
        raise FMPAPIError(
            "FMP rejected this request because the app is using legacy endpoints. "
            "Update the Financial Modeling Prep endpoints to the current API versions "
            "for your subscription tier."
        )

    raise FMPAPIError(
        f"FMP API request failed for {endpoint_name} with status {response.status_code}."
    )


def get_valuation(symbol: str) -> str:
    data = _call_fmp_with_fallback(
        "dcf_advanced",
        "dcf-advanced",
        fallback_path="discounted-cash-flow",
        symbol=symbol,
    )
    if not data:
        logger.warning(
            "FMP valuation endpoint returned empty data", extra={"symbol": symbol}
        )
        return _safe_json({})
    return _safe_json(_extract_first_record(data))


def get_symbol_data(symbol: str) -> str:
    endpoints = {
        "profile": "profile",
        "quote": "quote",
        "income_statement": "income-statement",
        "analyst_ratings": "grades",
    }
    stock_data: dict[str, Any] = {}

    for endpoint_name, endpoint_path in endpoints.items():
        if endpoint_name == "profile":
            data = _call_fmp_with_fallback(
                endpoint_name,
                endpoint_path,
                fallback_path="profile-symbol",
                symbol=symbol,
            )
        else:
            data = _call_fmp(endpoint_name, endpoint_path, symbol=symbol)
        if data:
            stock_data[endpoint_name] = _extract_first_record(data)
        else:
            logger.warning(
                "FMP symbol endpoint returned empty data",
                extra={"symbol": symbol, "endpoint_name": endpoint_name},
            )
            stock_data[endpoint_name] = {}

    valuation = json.loads(get_valuation(symbol))
    stock_data["valuation"] = valuation
    return _safe_json(stock_data)


def get_news(ticker: str) -> str:
    logger.debug("Fetching stock news", extra={"ticker": ticker})
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
    ratio = (
        float(pe_ratio)
        if pe_ratio is not None
        else default_pe_by_industry.get(industry_key, 10)
    )
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
