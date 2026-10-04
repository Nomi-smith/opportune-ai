from datetime import date
from types import SimpleNamespace
from intelligence.freshness import availability_reason, _dates

def test_day_month_year_is_parsed():
    assert date(2026,6,1) in _dates("Deadline date 1 June 2026, 23:59")

def test_closed_and_past_page_is_rejected():
    item=SimpleNamespace(
        title="UPC-MERIT Scholarship",
        deadline="",
        description="Status Closed. Deadline date 1 June 2026, 23:59 (CEST).",
        metadata={}
    )
    ok, reason=availability_reason(item)
    assert not ok
    assert "closed" in reason.lower()

def test_source_library_is_large():
    import csv
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/"config"/"scholarship_sources.csv"
    with path.open(encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    assert len(rows) >= 500

def test_google_source_file_exists():
    from pathlib import Path
    assert (Path(__file__).resolve().parents[1] / "sources" / "google_grounded.py").exists()
