import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pne_child_literacy_cycle import build_cycle_result


def test_published_current_year():
    result = build_cycle_result("4313375", meta=100, state_code="RS")
    assert result["available"] is True
    assert result["end_year"] == 2025
    assert result["end_value"] == pytest.approx(49)
    assert result["network"] == "municipal"


def test_current_missing_does_not_fall_back_to_an_old_result(monkeypatch):
    row = {"municipalityId": "4313375", "municipalityName": "Nova Santa Rita",
           "series": [{"year": 2024, "value": 80, "dataStatus": "available"},
                      {"year": 2025, "value": None, "dataStatus": "unavailable",
                       "reasonCode": "below_minimum_participation"}]}
    monkeypatch.setattr("src.pne_child_literacy_cycle._snapshot",
                        lambda _state: ([row], [], {"files": {}}))
    result = build_cycle_result("4313375", meta=100, state_code="RS")
    assert result["available"] is False
    assert result["end_value"] is None
    assert result["atingida"] is None
    assert result["reason_code"] == "below_minimum_participation"
    assert result["series"] == [{"ano": 2024, "valor": 80}]


def test_state_reference_preserves_official_value_and_separate_municipal_coverage(monkeypatch):
    from src.pne_state_reference import build_child_literacy_records
    municipal = [
        {"series": [{"year": 2025, "value": 20, "dataStatus": "available"}]},
        {"series": [{"year": 2025, "value": None, "dataStatus": "unavailable"}]},
    ]
    monkeypatch.setattr("src.child_literacy.load_snapshot", lambda **_kwargs: (
        municipal, [{"year": 2025, "value": 77, "dataStatus": "available"}], {},
    ))
    record = build_child_literacy_records("RS")[0]
    assert record["value"] == 77
    assert record["municipalities_valid"] == 1
    assert record["municipalities_expected"] == 2
    assert record["municipal_coverage_percent"] == 50
    assert record["denominator_coverage_percent"] is None
    assert record["numerator"] is None and record["denominator"] is None
