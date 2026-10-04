import json
from pathlib import Path


def test_registry_has_25_priority_countries_and_150_entries():
    path = Path(__file__).resolve().parents[1] / "config" / "opportunity_sources.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    countries = data["countries"]
    entries = [item for values in countries.values() for item in values]
    assert len(countries) == 25
    assert len(entries) >= 150
    assert len({item["domain"] for item in entries}) >= 145


def test_registry_has_global_sources():
    path = Path(__file__).resolve().parents[1] / "config" / "opportunity_sources.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    domains = {item["domain"] for item in data["global_sources"]}
    for required in {"erasmus-plus.ec.europa.eu", "euraxess.ec.europa.eu", "eures.europa.eu"}:
        assert required in domains
