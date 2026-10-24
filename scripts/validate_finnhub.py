"""Temporary, read-only validation of Finnhub news and daily candle access."""

from __future__ import annotations

import json
import math
import os
import re
import socket
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

API_BASE = "https://finnhub.io/api/v1"
TICKER = "AAPL"
START_DATE = date(2026, 10, 1)
END_DATE = date(2026, 10, 7)
REQUEST_TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 2_000_000
NEW_YORK = ZoneInfo("America/New_York")
NEWS_FIELDS = ("datetime", "headline", "source", "url", "summary")
CANDLE_FIELDS = ("t", "o", "h", "l", "c", "v")


@dataclass
class ApiResponse:
    http_status: int | None
    payload: Any
    json_valid: bool
    error: str | None = None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _safe_error(message: str, token: str) -> str:
    sanitized = message.replace(token, "[credential redacted]")
    sanitized = re.sub(r"https?://\S+", "[URL redacted]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(
        r"(?i)(token|api[_-]?key)\s*[=:]\s*[^&\s,;]+",
        r"\1=[credential redacted]",
        sanitized,
    )
    sanitized = " ".join(sanitized.split())
    return sanitized[:240] or "provider returned an unspecified error"


def _provider_error(payload: Any, token: str) -> str | None:
    if not isinstance(payload, dict):
        return None
    for field in ("error", "message"):
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return _safe_error(value, token)
    return None


def _request_json(path: str, params: dict[str, str], token: str) -> ApiResponse:
    url = f"{API_BASE}{path}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "X-Finnhub-Token": token,
            "Accept": "application/json",
            "User-Agent": "financial-news-sentiment-validation/temporary",
        },
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            status = response.status
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        status = error.code
        body = error.read(16_384)
        try:
            payload = json.loads(body)
            json_valid = True
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = None
            json_valid = False
        provider_message = _provider_error(payload, token)
        return ApiResponse(
            status,
            payload,
            json_valid,
            provider_message or "provider returned an HTTP error",
        )
    except TimeoutError:
        return ApiResponse(None, None, False, "request timed out")
    except URLError as error:
        reason = error.reason
        if isinstance(reason, (TimeoutError, socket.timeout)):
            message = "request timed out"
        else:
            message = "network connection failed; details omitted"
        return ApiResponse(None, None, False, message)
    except OSError:
        return ApiResponse(None, None, False, "network request failed; details omitted")

    if len(body) > MAX_RESPONSE_BYTES:
        return ApiResponse(status, None, False, "response exceeded the 2 MB safety limit")

    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ApiResponse(status, None, False, "response was not valid JSON")

    provider_message = _provider_error(payload, token)
    return ApiResponse(status, payload, True, provider_message)


def _http_outcome(status: int | None) -> str:
    if status in (401, 403):
        return "denied"
    if status == 429:
        return "rate limited"
    if status is not None and status >= 400:
        return "inconclusive"
    if status is None:
        return "inconclusive"
    return "response received"


def _fields(records: list[Any]) -> list[str]:
    return sorted({key for record in records if isinstance(record, dict) for key in record})


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _usable_timestamp(value: Any) -> datetime | None:
    if not _is_number(value) or value <= 0:
        return None
    try:
        return datetime.fromtimestamp(value, UTC).astimezone(NEW_YORK)
    except (OverflowError, OSError, ValueError):
        return None


def _usable_url(value: Any) -> bool:
    if not _has_text(value):
        return False
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _print_error(error: str | None) -> None:
    if error:
        print(f"Error: {error}")


def _print_news(token: str) -> None:
    path = "/company-news"
    response = _request_json(
        path,
        {"symbol": TICKER, "from": START_DATE.isoformat(), "to": END_DATE.isoformat()},
        token,
    )
    payload = response.payload
    record_list = payload if isinstance(payload, list) else None
    records_returned = len(record_list) if record_list is not None else None
    counts = {field: 0 for field in NEWS_FIELDS}
    usable_dates: list[date] = []
    non_object_records = 0

    if record_list is not None:
        for record in record_list:
            if not isinstance(record, dict):
                non_object_records += 1
                for field in NEWS_FIELDS:
                    counts[field] += 1
                continue
            for field in NEWS_FIELDS:
                value = record.get(field)
                usable = _usable_timestamp(value) is not None if field == "datetime" else (
                    _usable_url(value) if field == "url" else _has_text(value)
                )
                if not usable:
                    counts[field] += 1
            published = _usable_timestamp(record.get("datetime"))
            if published is not None:
                usable_dates.append(published.date())

    status = _http_outcome(response.http_status)
    if response.http_status is not None and response.http_status >= 400:
        status = "rate limited" if response.http_status == 429 else (
            "denied" if response.http_status in (401, 403) else "inconclusive"
        )
    elif response.error and any(word in response.error.lower() for word in ("auth", "access", "permission", "plan")):
        status = "denied"
    elif not response.json_valid or record_list is None:
        status = "inconclusive"
    elif not record_list:
        status = "empty"
    elif response.error:
        status = "denied" if any(word in response.error.lower() for word in ("auth", "access", "permission", "plan")) else "inconclusive"
    else:
        status = "successful response"

    print("\nTest 1 - Finnhub company news")
    print(f"Endpoint: {path}")
    print(f"Ticker/date range: {TICKER}, {START_DATE} through {END_DATE} (inclusive)")
    print(f"HTTP status: {response.http_status if response.http_status is not None else 'unavailable'}")
    print(f"JSON valid: {'yes' if response.json_valid else 'no'}")
    print(f"Top-level JSON list: {'yes' if record_list is not None else 'no'}")
    print(f"Status: {status}")
    print(f"Returned fields: {', '.join(_fields(record_list or [])) or 'none'}")
    print(f"Records returned: {records_returned if records_returned is not None else 'not available'}")
    if record_list is not None:
        print("Missing/unusable counts: " + ", ".join(f"{field}={counts[field]}" for field in NEWS_FIELDS))
        if non_object_records:
            print(f"Non-object records: {non_object_records}")
        outside_range = sum(not START_DATE <= value <= END_DATE for value in usable_dates)
        print(f"Usable timestamp dates outside requested range (New York): {outside_range}")
        if usable_dates:
            print(f"Usable timestamp date coverage (New York): {min(usable_dates)} through {max(usable_dates)}")
    _print_error(response.error)


def _ny_epoch(day: date) -> int:
    return int(datetime.combine(day, time.min, NEW_YORK).timestamp())


def _usable_candle_row(payload: dict[str, Any], index: int) -> bool:
    timestamp = payload["t"][index]
    values = [payload[field][index] for field in ("o", "h", "l", "c", "v")]
    if _usable_timestamp(timestamp) is None or not all(_is_number(value) for value in values):
        return False
    open_price, high, low, close, volume = values
    return (
        open_price > 0
        and high > 0
        and low > 0
        and close > 0
        and volume >= 0
        and high >= max(open_price, close, low)
        and low <= min(open_price, close, high)
    )


def _print_candles(token: str) -> None:
    path = "/stock/candle"
    response = _request_json(
        path,
        {
            "symbol": TICKER,
            "resolution": "D",
            "from": str(_ny_epoch(START_DATE)),
            "to": str(_ny_epoch(END_DATE + timedelta(days=1)) - 1),
        },
        token,
    )
    payload = response.payload
    is_object = isinstance(payload, dict)
    arrays = {field: payload.get(field) for field in CANDLE_FIELDS} if is_object else {}
    array_types_ok = is_object and all(isinstance(arrays[field], list) for field in CANDLE_FIELDS)
    lengths = {field: len(arrays[field]) for field in CANDLE_FIELDS} if array_types_ok else {}
    arrays_consistent = array_types_ok and len(set(lengths.values())) == 1
    row_count = next(iter(lengths.values())) if arrays_consistent else None
    response_status = payload.get("s") if is_object else None
    usable_rows = 0
    session_dates: list[date] = []

    if arrays_consistent and row_count is not None:
        for index in range(row_count):
            if _usable_candle_row(payload, index):
                usable_rows += 1
            timestamp = _usable_timestamp(payload["t"][index])
            if timestamp is not None:
                session_dates.append(timestamp.date())

    if response.http_status is not None and response.http_status >= 400:
        outcome = "rate limited" if response.http_status == 429 else (
            "denied" if response.http_status in (401, 403) else "inconclusive"
        )
    elif not response.json_valid or not is_object:
        outcome = "inconclusive"
    elif response_status == "no_data":
        outcome = "empty"
    elif response_status != "ok":
        outcome = "denied" if response.error and any(word in response.error.lower() for word in ("auth", "access", "permission", "plan")) else "inconclusive"
    elif not array_types_ok or not arrays_consistent:
        outcome = "inconclusive"
    elif row_count == 0:
        outcome = "empty"
    elif usable_rows != row_count:
        outcome = "inconclusive"
    else:
        outcome = "successful response"

    print("\nTest 2 - Finnhub historical daily stock candles")
    print(f"Endpoint: {path}")
    print(f"Ticker/date range: {TICKER}, {START_DATE} through {END_DATE} (inclusive, New York dates)")
    print("Resolution: D")
    print(f"HTTP status: {response.http_status if response.http_status is not None else 'unavailable'}")
    print(f"JSON valid: {'yes' if response.json_valid else 'no'}")
    print(f"Returned fields: {', '.join(sorted(payload.keys())) if is_object else 'none'}")
    print(f"Provider candle status: {response_status if isinstance(response_status, str) else 'unavailable'}")
    print(f"Access result: {outcome}")
    if lengths:
        print("Array lengths: " + ", ".join(f"{field}={lengths[field]}" for field in CANDLE_FIELDS))
        print(f"Array lengths consistent: {'yes' if arrays_consistent else 'no'}")
        print(f"Usable daily OHLCV rows: {usable_rows}/{row_count}")
        print(f"Closing prices interpretable as finite positive numbers: {sum(_is_number(value) and value > 0 for value in arrays['c'])}/{row_count}")
        if session_dates:
            outside_range = sum(not START_DATE <= value <= END_DATE for value in session_dates)
            print(f"Returned timestamp dates (New York): {min(session_dates)} through {max(session_dates)}")
            print(f"Timestamp dates outside requested range: {outside_range}")
    elif array_types_ok:
        print("Array lengths: all zero")
        print("Array lengths consistent: yes")
        print("Usable daily OHLCV rows: 0/0")
    else:
        print("Array lengths consistent: not evaluable")
    _print_error(response.error)
    print("Plan note: this short-range result does not establish account-wide plan entitlement.")


def main() -> int:
    token = os.environ.get("FINNHUB_API_KEY", "").strip()
    print("Finnhub diagnostic report (response bodies and credentials are never printed)")
    print(f"Ticker/date range: {TICKER}, {START_DATE} through {END_DATE} (inclusive)")
    if not token:
        print("Credential status: FINNHUB_API_KEY is missing from the process environment; no requests sent.")
        for title, endpoint in (("Test 1 - Finnhub company news", "/company-news"), ("Test 2 - Finnhub historical daily stock candles", "/stock/candle")):
            print(f"\n{title}")
            print(f"Endpoint: {endpoint}")
            print("HTTP status: not requested")
            print("Status: inconclusive (missing environment variable)")
        return 2

    _print_news(token)
    _print_candles(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())