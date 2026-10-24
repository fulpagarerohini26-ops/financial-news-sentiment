"""Verification gate for an exact Nasdaq calendar; not application code."""

from __future__ import annotations

from zoneinfo import ZoneInfo

import pytest

exchange_calendars = pytest.importorskip("exchange_calendars")


def _exact_xnas_calendar():
    calendar = exchange_calendars.get_calendar("XNAS")
    if calendar.name != "XNAS":
        pytest.xfail(
            f"XNAS resolved to {calendar.name}; refusing to validate an NYSE alias as Nasdaq"
        )
    return calendar


@pytest.mark.xfail(
    strict=True,
    reason="exchange-calendars 4.13.2 has no canonical XNAS calendar",
)
def test_xnas_is_a_canonical_calendar_not_an_alias() -> None:
    names = exchange_calendars.get_calendar_names(include_aliases=False)
    assert "XNAS" in names


@pytest.mark.parametrize(
    ("session_date", "expected_open_utc", "expected_close_utc"),
    [
        ("2026-11-24", "2026-11-24T14:30:00+00:00", "2026-11-24T21:00:00+00:00"),
        ("2026-11-28", None, None),
        ("2026-11-26", None, None),
        ("2026-11-27", "2026-11-27T14:30:00+00:00", "2026-11-27T18:00:00+00:00"),
        ("2026-10-30", "2026-10-30T13:30:00+00:00", "2026-10-30T20:00:00+00:00"),
        ("2026-11-02", "2026-11-02T14:30:00+00:00", "2026-11-02T21:00:00+00:00"),
    ],
    ids=["full-session", "saturday", "thanksgiving", "early-close", "before-dst-end", "after-dst-end"],
)
def test_nasdaq_schedule_matches_published_hours(
    session_date: str,
    expected_open_utc: str | None,
    expected_close_utc: str | None,
) -> None:
    calendar = _exact_xnas_calendar()
    sessions = calendar.schedule.loc[session_date:session_date]

    if expected_open_utc is None:
        assert sessions.empty
        return

    assert len(sessions) == 1
    session = sessions.iloc[0]
    market_open = session["open"].to_pydatetime()
    market_close = session["close"].to_pydatetime()
    assert market_open.isoformat() == expected_open_utc
    assert market_close.isoformat() == expected_close_utc

    expected_open_eastern, expected_close_eastern = {
        "2026-11-24": ("09:30:00-0500", "16:00:00-0500"),
        "2026-11-27": ("09:30:00-0500", "13:00:00-0500"),
        "2026-10-30": ("09:30:00-0400", "16:00:00-0400"),
        "2026-11-02": ("09:30:00-0500", "16:00:00-0500"),
    }[session_date]
    new_york = ZoneInfo("America/New_York")
    assert market_open.astimezone(new_york).strftime("%H:%M:%S%z") == expected_open_eastern
    assert market_close.astimezone(new_york).strftime("%H:%M:%S%z") == expected_close_eastern


def test_out_of_coverage_dates_are_not_treated_as_holidays() -> None:
    # XNYS is named explicitly here to characterize package bounds only.
    calendar = exchange_calendars.get_calendar("XNYS")
    assert calendar.schedule.index.min().strftime("%Y-%m-%d") == "2006-10-19"
    assert calendar.schedule.index.max().strftime("%Y-%m-%d") == "2027-10-19"

    for outside_date in ("1999-12-31", "2036-01-02"):
        with pytest.raises(Exception) as error:
            calendar.is_session(outside_date)
        assert type(error.value).__name__ == "DateOutOfBounds"

        # Raw schedule slicing is not a safe coverage check: it returns no rows.
        assert calendar.schedule.loc[outside_date:outside_date].empty