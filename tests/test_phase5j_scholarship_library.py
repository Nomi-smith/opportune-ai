import json
from pathlib import Path

def test_scholarship_library_imported():
    path = Path(__file__).resolve().parents[1] / "config" / "scholarship_library.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["entries"]) >= 25
    names = {x["name"] for x in data["entries"]}
    assert "DAAD Scholarships" in names
    assert "Chinese Government Scholarship (CSC)" in names

def test_catalogue_urls_are_specific():
    path = Path(__file__).resolve().parents[1] / "config" / "scholarship_library.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    daad = next(x for x in data["entries"] if x["name"] == "DAAD Scholarships")
    assert "stipendium/datenbank" in daad["source_url"]
    erasmus = next(x for x in data["entries"] if x["name"] == "Erasmus Mundus Joint Masters")
    assert "opportunities/individuals/students" in erasmus["source_url"]

def test_library_never_claims_seed_entries_are_live():
    path = Path(__file__).resolve().parents[1] / "config" / "scholarship_library.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert all(x["status_policy"] == "runtime_verify" for x in data["entries"])
