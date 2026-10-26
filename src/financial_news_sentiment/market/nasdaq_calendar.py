"""Nasdaq regular-session dates from the reviewed annual schedule ledger."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

_TIMEZONE_NAME = "America/New_York"
_TIMEZONE = ZoneInfo(_TIMEZONE_NAME)
_DEFAULT_LEDGER = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "reference"
    / "nasdaq_schedule_2026.json"
)


class CalendarDataError(ValueError):
    """The annual Nasdaq schedule is missing, malformed, or unreviewed."""


class DateOutOfCoverageError(ValueError):
    """The requested date is outside the verified schedule coverage."""


@dataclass(frozen=True, slots=True)
class NasdaqSession:
    """A regular Nasdaq session with timezone-aware local open and close."""

    session_date: date
    market_open: datetime
    market_close: datetime


@dataclass(frozen=True, slots=True)
class NasdaqCalendar:
    """A validated, reviewed annual schedule with explicit date coverage."""

    coverage_start: date
    coverage_end: date
    regular_open: time
    regular_close: time
    full_closures: frozenset[date]
    early_closes: dict[date, time]

    @property
    def supported_years(self) -> frozenset[int]:
        """Return years represented by this calendar's verified date range."""
        return frozenset(range(self.coverage_start.year, self.coverage_end.year + 1))

    @classmethod
    def from_ledger(cls, ledger: object) -> NasdaqCalendar:
        """Validate a decoded ledger object and construct a calendar."""
        top = _object(
            ledger,
            "ledger",
            {
                "year",
                "timezone",
                "source_urls",
                "source_checked",
                "reviewer",
                "review_status",
                "coverage",
                "regular_session",
                "full_closures",
                "early_closes",
            },
        )

        year = top["year"]
        if not isinstance(year, int) or isinstance(year, bool):
            raise CalendarDataError("ledger.year must be an integer")
        if top["timezone"] != _TIMEZONE_NAME:
            raise CalendarDataError(f"ledger.timezone must be {_TIMEZONE_NAME!r}")
        _validate_sources(top["source_urls"])
        _parse_date(top["source_checked"], "ledger.source_checked")
        _nonempty_string(top["reviewer"], "ledger.reviewer")
        if top["review_status"] != "reviewed":
            raise CalendarDataError("Nasdaq schedule ledger has not been reviewed")

        coverage = _object(top["coverage"], "ledger.coverage", {"start", "end"})
        coverage_start = _parse_date(coverage["start"], "coverage.start")
        coverage_end = _parse_date(coverage["end"], "coverage.end")
        if (
            coverage_start > coverage_end
            or coverage_start.year != year
            or coverage_end.year != year
        ):
            raise CalendarDataError("coverage must be an ordered range within ledger.year")

        regular = _object(
            top["regular_session"], "ledger.regular_session", {"open", "close"}
        )
        regular_open = _parse_time(regular["open"], "regular_session.open")
        regular_close = _parse_time(regular["close"], "regular_session.close")
        if regular_open >= regular_close:
            raise CalendarDataError("regular session open must be before close")

        closures = _parse_date_list(top["full_closures"], "full_closures")
        early_closes = _parse_early_closes(top["early_closes"])
        if closures.intersection(early_closes):
            raise CalendarDataError("a date cannot be both a full closure and early close")
        all_exceptions = closures.union(early_closes)
        if any(not coverage_start <= day <= coverage_end for day in all_exceptions):
            raise CalendarDataError("schedule exception falls outside coverage")
        if any(day.year != year for day in all_exceptions):
            raise CalendarDataError("schedule exception year must match ledger.year")
        if any(day.weekday() >= 5 for day in all_exceptions):
            raise CalendarDataError("schedule exceptions must fall on weekdays")
        for day, close in early_closes.items():
            if not regular_open < close < regular_close:
                raise CalendarDataError(
                    f"early close for {day.isoformat()} must be between regular open and close"
                )

        return cls(
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            regular_open=regular_open,
            regular_close=regular_close,
            full_closures=frozenset(closures),
            early_closes=early_closes,
        )

    def session_for(self, session_date: date) -> NasdaqSession | None:
        """Return the verified regular session, or None for an in-range non-session."""
        if type(session_date) is not date:
            raise TypeError("session_date must be a datetime.date")
        if not self.coverage_start <= session_date <= self.coverage_end:
            raise DateOutOfCoverageError(
                f"{session_date.isoformat()} is outside verified Nasdaq coverage "
                f"{self.coverage_start.isoformat()} through {self.coverage_end.isoformat()}"
            )
        if session_date.weekday() >= 5 or session_date in self.full_closures:
            return None

        close_time = self.early_closes.get(session_date, self.regular_close)
        market_open = datetime.combine(session_date, self.regular_open, _TIMEZONE)
        market_close = datetime.combine(session_date, close_time, _TIMEZONE)
        return NasdaqSession(session_date, market_open, market_close)


def load_nasdaq_calendar(
    ledger_path: Path | None = None,
) -> NasdaqCalendar:
    """Load and validate the default or explicitly supplied annual JSON ledger."""
    path = ledger_path if ledger_path is not None else _DEFAULT_LEDGER
    try:
        contents = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CalendarDataError(f"Unable to read Nasdaq calendar ledger {path}: {exc}") from exc
    try:
        ledger = json.loads(contents)
    except json.JSONDecodeError as exc:
        raise CalendarDataError(f"Invalid JSON in Nasdaq calendar ledger {path}: {exc}") from exc
    return NasdaqCalendar.from_ledger(ledger)


def _object(value: object, label: str, expected_keys: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise CalendarDataError(f"{label} must be an object with string keys")
    result = cast(dict[str, object], value)
    actual_keys = set(result)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        unexpected = sorted(actual_keys - expected_keys)
        raise CalendarDataError(
            f"{label} fields do not match schema (missing={missing}, unexpected={unexpected})"
        )
    return result


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalendarDataError(f"{label} must be a non-empty string")
    return value


def _parse_date(value: object, label: str) -> date:
    if not isinstance(value, str):
        raise CalendarDataError(f"{label} must be an ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise CalendarDataError(f"{label} must be an ISO date string") from exc
    if parsed.isoformat() != value:
        raise CalendarDataError(f"{label} must use YYYY-MM-DD format")
    return parsed


def _parse_time(value: object, label: str) -> time:
    if not isinstance(value, str):
        raise CalendarDataError(f"{label} must be an HH:MM local time string")
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise CalendarDataError(f"{label} must be an HH:MM local time string") from exc
    if parsed.tzinfo is not None or parsed.isoformat(timespec="minutes") != value:
        raise CalendarDataError(f"{label} must use an unzoned HH:MM local time")
    return parsed


def _validate_sources(value: object) -> None:
    if not isinstance(value, list) or not value:
        raise CalendarDataError("source_urls must be a non-empty list")
    seen: set[str] = set()
    for index, item in enumerate(value):
        url = _nonempty_string(item, f"source_urls[{index}]")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise CalendarDataError(f"source_urls[{index}] must be an HTTPS URL")
        if url in seen:
            raise CalendarDataError(f"source_urls contains duplicate URL {url!r}")
        seen.add(url)


def _parse_date_list(value: object, label: str) -> set[date]:
    if not isinstance(value, list):
        raise CalendarDataError(f"{label} must be a list of ISO dates")
    result: set[date] = set()
    for index, item in enumerate(value):
        parsed = _parse_date(item, f"{label}[{index}]")
        if parsed in result:
            raise CalendarDataError(f"{label} contains duplicate date {parsed.isoformat()}")
        result.add(parsed)
    return result


def _parse_early_closes(value: object) -> dict[date, time]:
    if not isinstance(value, list):
        raise CalendarDataError("early_closes must be a list")
    result: dict[date, time] = {}
    for index, item in enumerate(value):
        record = _object(item, f"early_closes[{index}]", {"date", "close"})
        day = _parse_date(record["date"], f"early_closes[{index}].date")
        close = _parse_time(record["close"], f"early_closes[{index}].close")
        if day in result:
            raise CalendarDataError(f"early_closes contains duplicate date {day.isoformat()}")
        result[day] = close
    return result
