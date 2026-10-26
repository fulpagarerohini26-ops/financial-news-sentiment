# Symbol Lookup
https://docs.google.com/spreadsheets/d/1I3pBxjfXB056-g_JYf_6o3Rns3BV2kMGG1nCatb91ls/edit?pli=1&gid=0#gid=0

## Nasdaq annual session schedule

`nasdaq_schedule_2026.json` is the reviewed 2026 Nasdaq regular-session ledger. Its source URLs point to Nasdaq Trader's official U.S. Equity and Options Markets Holiday Schedule and the 2026 trading-calendar PDF. The ledger records the full-year coverage, `America/New_York` regular hours, full closures, early closes, source-check date, reviewer, and review status. The schedule contains derived date and clock-time facts; it does not use an exchange-calendar package or infer future years.

To update or add a year:

1. Start from the year-specific official Nasdaq Trader calendar and the Nasdaq U.S. Stock Market Holiday Schedule. Record the exact source URLs and the date they were checked.
2. Transcribe and independently check every full-day closure and early close for that year against the official schedule. Record the regular local open and close and the exact supported date range. Do not extrapolate recurring holidays into another year.
3. Have a maintainer review the complete ledger against the cited sources and confirm the derived schedule may be stored in the repository. Set `reviewer` and `review_status` only after that review; the adapter rejects unreviewed ledgers.
4. Add or update date-specific tests for at least a regular session, a closure, an early close, and applicable timezone transitions. Keep those tests and the ledger change together.
5. Run `uv run pytest tests/unit/test_nasdaq_calendar_adapter.py` and have the ledger reviewed with the source change before merging. Do not extend coverage until the official annual schedule is published and reviewed.
