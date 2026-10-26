from __future__ import annotations

import json
from datetime import UTC, date, time
from pathlib import Path

import pytest

from financial_news_sentiment.market.nasdaq_calendar import (
    CalendarDataError,
    DateOutOfCoverageError,
    NasdaqCalendar,
    load_nasdaq_calendar,
)

LEDGER_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "reference"
    / "nasdaq_schedule_2026.json"
)


@pytest.fixture
def calendar() -> NasdaqCalendar:
    return load_nasdaq_calendar()


def test_regular_weekday_uses_reviewed_annual_schedule(calendar: NasdaqCalendar) -> None:
    session = calendar.session_for(date(2026, 11, 24))

    assert session is not None
    assert session.market_open.isoformat() == "2026-11-24T09:30:00-05:00"
    assert session.market_close.isoformat() == "2026-11-24T16:00:00-05:00"
    assert session.market_open.astimezone(UTC).isoformat() == (
        "2026-11-24T14:30:00+00:00"
    )
    assert calendar.supported_years == frozenset({2026})
    assert (calendar.coverage_start, calendar.coverage_end) == (
        date(2026, 1, 1),
        date(2026, 12, 31),
    )


def test_weekend_has_no_session(calendar: NasdaqCalendar) -> None:
    assert calendar.session_for(date(2026, 11, 28)) is None


def test_official_thanksgiving_closure_has_no_session(calendar: NasdaqCalendar) -> None:
    assert calendar.session_for(date(2026, 11, 26)) is None


def test_ledger_contains_the_official_2026_closures_and_early_closes(
    calendar: NasdaqCalendar,
) -> None:
    assert calendar.full_closures == frozenset(
        {
            date(2026, 1, 1),
            date(2026, 1, 19),
            date(2026, 2, 16),
            date(2026, 4, 3),
            date(2026, 5, 25),
            date(2026, 6, 19),
            date(2026, 7, 3),
            date(2026, 9, 7),
            date(2026, 11, 26),
            date(2026, 12, 25),
        }
    )
    assert calendar.early_closes == {
        date(2026, 11, 27): time(13),
        date(2026, 12, 24): time(13),
    }


def test_official_early_close_uses_one_pm_eastern(calendar: NasdaqCalendar) -> None:
    session = calendar.session_for(date(2026, 11, 27))

    assert session is not None
    assert session.market_open.isoformat() == "2026-11-27T09:30:00-05:00"
    assert session.market_close.isoformat() == "2026-11-27T13:00:00-05:00"
    assert session.market_close.astimezone(UTC).isoformat() == (
        "2026-11-27T18:00:00+00:00"
    )


@pytest.mark.parametrize(
    ("session_date", "expected_offset", "expected_utc_open", "expected_utc_close"),
    [
        (
            date(2026, 10, 30),
            "-0400",
            "2026-10-30T13:30:00+00:00",
            "2026-10-30T20:00:00+00:00",
        ),
        (
            date(2026, 11, 2),
            "-0500",
            "2026-11-02T14:30:00+00:00",
            "2026-11-02T21:00:00+00:00",
        ),
    ],
    ids=["before-dst-end", "after-dst-end"],
)
def test_dst_changes_utc_instants_not_new_york_session_times(
    calendar: NasdaqCalendar,
    session_date: date,
    expected_offset: str,
    expected_utc_open: str,
    expected_utc_close: str,
) -> None:
    session = calendar.session_for(session_date)

    assert session is not None
    assert session.market_open.strftime("%H:%M:%S%z") == f"09:30:00{expected_offset}"
    assert session.market_close.strftime("%H:%M:%S%z") == f"16:00:00{expected_offset}"
    assert session.market_open.astimezone(UTC).isoformat() == expected_utc_open
    assert session.market_close.astimezone(UTC).isoformat() == expected_utc_close


def test_malformed_json_ledger_is_rejected(tmp_path: Path) -> None:
    ledger_path = tmp_path / "malformed.json"
    ledger_path.write_text('{"year": 2026,', encoding="utf-8")

    with pytest.raises(CalendarDataError, match="Invalid JSON"):
        load_nasdaq_calendar(ledger_path)


def test_malformed_or_conflicting_ledger_entries_are_rejected(tmp_path: Path) -> None:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    ledger["early_closes"][0]["date"] = "2026-11-26"
    ledger_path = tmp_path / "conflicting.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(CalendarDataError, match="both a full closure and early close"):
        load_nasdaq_calendar(ledger_path)


def test_unreviewed_ledger_is_not_supported(tmp_path: Path) -> None:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    ledger["review_status"] = "pending"
    ledger_path = tmp_path / "unreviewed.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(CalendarDataError, match="has not been reviewed"):
        load_nasdaq_calendar(ledger_path)


@pytest.mark.parametrize("outside_date", [date(2025, 12, 31), date(2027, 1, 4)])
def test_dates_outside_verified_coverage_raise(
    calendar: NasdaqCalendar, outside_date: date
) -> None:
    with pytest.raises(DateOutOfCoverageError, match="outside verified Nasdaq coverage"):
        calendar.session_for(outside_date)
