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


class FMPFallbackTriggered(FMPAPIError):
    def __init__(self, endpoint_name: str, status_code: int, url: str, message: str):
        super().__init__(message)
        self.endpoint_name = endpoint_name
        self.status_code = status_code
        self.url = url


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
    except FMPFallbackTriggered as exc:
        if fallback_path is None:
            raise
        logger.warning(
            "FMP endpoint fallback triggered",
            extra={
                "endpoint_name": endpoint_name,
                "primary_path": primary_path,
                "fallback_path": fallback_path,
                "status_code": exc.status_code,
                "primary_url": exc.url,
            },
        )
        data = _call_fmp(endpoint_name, fallback_path, **params)
        logger.info(
            "FMP endpoint fallback succeeded",
            extra={
                "endpoint_name": endpoint_name,
                "primary_path": primary_path,
                "fallback_path": fallback_path,
            },
        )
        return data
    except FMPAPIError:
        raise


def _raise_for_fmp_response(response: requests.Response, endpoint_name: str) -> None:
    if response.ok:
        return

    response_text = response.text.strip()

    if response.status_code == 404:
        logger.info(
            "FMP API primary endpoint unavailable; fallback may be used",
            extra={
                "endpoint_name": endpoint_name,
                "status_code": response.status_code,
                "url": response.url,
                "response_preview": response_text[:300],
            },
        )
        raise FMPFallbackTriggered(
            endpoint_name=endpoint_name,
            status_code=response.status_code,
            url=response.url,
            message=(
                f"FMP API request failed for {endpoint_name} with status "
                f"{response.status_code}."
            ),
        )

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


def _is_empty_record(data: Any) -> bool:
    if data is None:
        return True
    if isinstance(data, (list, dict, str, tuple, set)):
        return len(data) == 0
    return False


def _error_payload(status: str, message: str, **extra: Any) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        **extra,
    }


def get_valuation(symbol: str) -> str:
    try:
        data = _call_fmp_with_fallback(
            "dcf_valuation",
            "dcf-advanced",
            fallback_path="discounted-cash-flow",
            symbol=symbol,
        )
    except FMPAPIError as exc:
        logger.warning(
            "FMP valuation lookup failed",
            extra={"symbol": symbol, "error": str(exc)},
        )
        return _safe_json(
            _error_payload(
                "unavailable",
                "FMP valuation data is currently unavailable for this ticker.",
                symbol=symbol,
                error=str(exc),
            )
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
    endpoint_errors: dict[str, str] = {}

    for endpoint_name, endpoint_path in endpoints.items():
        try:
            if endpoint_name == "profile":
                data = _call_fmp_with_fallback(
                    endpoint_name,
                    "profile-symbol",
                    fallback_path=endpoint_path,
                    symbol=symbol,
                )
            else:
                data = _call_fmp(endpoint_name, endpoint_path, symbol=symbol)
        except FMPAPIError as exc:
            logger.warning(
                "FMP symbol endpoint failed",
                extra={
                    "symbol": symbol,
                    "endpoint_name": endpoint_name,
                    "error": str(exc),
                },
            )
            endpoint_errors[endpoint_name] = str(exc)
            stock_data[endpoint_name] = _error_payload(
                "unavailable",
                f"FMP {endpoint_name.replace('_', ' ')} data is unavailable.",
                symbol=symbol,
                endpoint=endpoint_name,
                error=str(exc),
            )
            continue
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

    non_error_records = [
        value
        for value in stock_data.values()
        if not (isinstance(value, dict) and value.get("status") == "unavailable")
    ]

    if non_error_records and all(
        _is_empty_record(value) for value in non_error_records
    ):
        logger.warning(
            "FMP returned no symbol data across all endpoints",
            extra={"symbol": symbol},
        )
        return _safe_json(
            {
                "symbol": symbol,
                "status": "not_found",
                "message": (
                    "FMP returned no symbol data for this ticker. "
                    "Use search_company_ticker to look up the correct ticker by company name."
                ),
                "search_suggestion": symbol,
            }
        )

    if not non_error_records:
        logger.warning(
            "FMP symbol lookup unavailable across all endpoints",
            extra={"symbol": symbol, "endpoint_errors": endpoint_errors},
        )
        return _safe_json(
            {
                "symbol": symbol,
                "status": "lookup_unavailable",
                "message": (
                    "FMP symbol lookup is currently unavailable for this ticker. "
                    "Try search_company_ticker to confirm the company symbol."
                ),
                "errors": endpoint_errors,
                "search_suggestion": symbol,
            }
        )

    return _safe_json(stock_data)


def search_company_ticker(query: str, limit: int = 10) -> str:
    normalized_query = query.strip()
    normalized_limit = max(1, min(limit, 20))

    if not normalized_query:
        return _safe_json(
            {
                "query": query,
                "status": "invalid_request",
                "message": "A company name or ticker search query is required.",
                "results": [],
            }
        )

    try:
        data = _call_fmp(
            "search_company_ticker",
            "search-name",
            query=normalized_query,
            limit=normalized_limit,
        )
    except FMPAPIError as exc:
        logger.warning(
            "FMP company ticker search failed",
            extra={
                "query": normalized_query,
                "limit": normalized_limit,
                "error": str(exc),
            },
        )
        return _safe_json(
            {
                "query": normalized_query,
                "status": "unavailable",
                "message": "FMP company ticker search is currently unavailable.",
                "results": [],
                "error": str(exc),
            }
        )

    if not data:
        logger.warning(
            "FMP company ticker search returned empty data",
            extra={"query": normalized_query, "limit": normalized_limit},
        )
        return _safe_json(
            {
                "query": normalized_query,
                "status": "not_found",
                "message": "FMP could not find matching company ticker data.",
                "results": [],
            }
        )

    return _safe_json(
        {
            "query": normalized_query,
            "status": "ok",
            "results": data,
        }
    )


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
            func=search_company_ticker,
            name="search_company_ticker",
            description="Search Financial Modeling Prep for matching companies and tickers by company name or partial ticker. Use this when a ticker is unknown or symbol data is not found.",
        ),
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
