from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from src.pne_census_attainment import census_results, component, secondary_component
from src.pne_goal_11b_census import ratio_result


def age(total=100, secondary=40, higher=10):
    return {"sourceValues": {
        key: {"value": value, "status": "available"}
        for key, value in {"total": total, "secondary_complete": secondary,
                           "higher_complete": higher}.items()
    }}


def test_same_universe_and_disjoint_ages():
    row = {"eighteenToTwentyFour": age(), "twentyFiveToTwentyNine": age(200, 70, 30)}
    result = ratio_result(component(row, "medio_concluido_18_29"))
    assert result["numerator"] == 150
    assert result["denominator"] == 300
    assert result["value"] == 50


@pytest.mark.parametrize("status", ["suppressed", "unavailable", "not_applicable"])
def test_missing_components_are_not_zero(status):
    item = deepcopy(age())
    item["sourceValues"]["secondary_complete"] = {"value": None, "status": status}
    result = ratio_result(secondary_component(item))
    assert result["dataStatus"] == status
    assert result["value"] is None


def test_zero_denominator_and_observed_zero_are_distinct():
    assert ratio_result(secondary_component(age(0, 0, 0)))["value"] is None
    assert ratio_result(secondary_component(age(100, 0, 0)))["value"] == 0


def test_official_snapshot_nova_santa_rita():
    young = census_results("medio_concluido_18_29", "RS")["4313375"]
    adult = census_results("medio_concluido_18_mais", "RS")["4313375"]
    assert young["numerator"] == 3065 and young["denominator"] == 5105
    assert young["value"] == pytest.approx(60.039177277179235)
    assert adult["numerator"] == 10764 and adult["denominator"] == 21404
    assert adult["value"] == pytest.approx(50.289665483087276)
