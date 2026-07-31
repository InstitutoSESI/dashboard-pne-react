from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from data_pipeline.src.pne.diagnostic_presentation_policy import POLICY
from data_pipeline.src.pne.goal_indicator_contract import CONTRACT
from data_pipeline.src.pne2026_public_diagnostic_v2 import (
    build_pne2026_public_diagnostic_v2,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_BASELINE = json.loads(
    (
        REPO_ROOT
        / "data_pipeline"
        / "tests"
        / "fixtures"
        / "pne2026_diagnostic_2b2a_baseline.json"
    ).read_text(encoding="utf-8")
)
BASELINE = json.loads(
    (
        REPO_ROOT
        / "data_pipeline"
        / "tests"
        / "fixtures"
        / "pne2026_diagnostic_2b2c1_1_baseline.json"
    ).read_text(encoding="utf-8")
)
FROZEN_PRESENTATION = json.loads(
    (
        REPO_ROOT
        / "data_pipeline"
        / "src"
        / "data"
        / "pne2026_diagnostic_presentation_v2.json"
    ).read_text(encoding="utf-8")
)
RELATIONS = {
    relation["relationId"]: relation for relation in CONTRACT["relations"]
}
RELATIONS_BY_PAIR = {
    (relation["goalId"], relation["indicatorId"]): relation
    for relation in CONTRACT["relations"]
}
def _legacy_mode(relation: dict) -> str:
    if relation["relationId"] == "relation.11.b.fundamental_concluido_18_mais":
        return "progress"
    return relation.get("legacyV2Mode", relation["mode"])


POLICY_ENTRIES = sorted(
    [
        {
            "relationId": RELATIONS_BY_PAIR[
                (item["goalId"], item["indicatorId"])
            ]["relationId"],
            "displayOrder": item["resultOrder"],
            "themeId": item["themeId"],
            "summaryPriority": (
                "essential" if item["tier"] == "essential" else "standard"
            ),
            "displayGroup": (
                f"summary-{item['priorityOrder']}"
                if item["priorityOrder"] is not None
                else "detail"
            ),
        }
        for item in FROZEN_PRESENTATION["results"]
        if item.get("monitoringMode", "progress") != "hidden"
    ],
    key=lambda entry: entry["displayOrder"],
)


class _GitBlobSnapshot:
    def __enter__(self):
        self.process = subprocess.Popen(
            ["git", "cat-file", "--batch"],
            cwd=REPO_ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        return self

    def json(self, path: str):
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        self.process.stdin.write(f"HEAD:{path}\n".encode())
        self.process.stdin.flush()
        header = self.process.stdout.readline().decode().strip()
        if header.endswith(" missing"):
            raise FileNotFoundError(path)
        _, object_type, size_text = header.split()
        if object_type != "blob":
            raise TypeError(f"{path} não é blob: {header}")
        payload = self.process.stdout.read(int(size_text))
        self.process.stdout.read(1)
        return json.loads(payload)

    def __exit__(self, *_):
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        self.process.stdin.close()
        self.process.stdout.close()
        self.process.wait()


def _flat_by_relation(payload: dict) -> dict[str, dict]:
    by_pair = {
        (relation["goalId"], relation["indicatorId"]): relation
        for relation in CONTRACT["relations"]
    }
    flattened = {}
    for goal in payload.get("goals") or []:
        for result in goal.get("results") or []:
            relation = by_pair[(goal["goalId"], result["indicatorId"])]
            flattened[relation["relationId"]] = result
    return flattened


def _priority_order(entry: dict) -> int | None:
    group = entry.get("displayGroup", "")
    return int(group.removeprefix("summary-")) if group.startswith("summary-") else None


def _reference(result: dict | None, relation: dict) -> dict | None:
    if result is None or not relation["canDistance"]:
        return None
    reference = result.get("indicatorReference")
    if not reference:
        return None
    return {
        "value": reference.get("value"),
        "year": reference.get("year"),
        "direction": reference.get("direction"),
    }


def _trajectory(result: dict | None, relation: dict) -> dict | None:
    if result is None or not relation["canProjection"]:
        return None
    trajectory = result.get("trajectory")
    if not trajectory:
        return None
    return {
        key: trajectory.get(key)
        for key in (
            "historicalReading",
            "estimatedAchievementYear",
            "achievementReading",
        )
    }


def _state_comparison(result: dict | None, relation: dict) -> dict | None:
    if (
        result is None
        or relation["stateReferencePolicy"] == "none"
        or not result.get("stateComparison")
    ):
        return None
    comparison = result["stateComparison"]
    return {
        key: comparison.get(key)
        for key in ("state", "municipalityValue", "stateValue", "unit")
    }


def _normalized_records(
    municipality_id: str,
    public_payload: dict,
    technical_payload: dict,
) -> list[dict]:
    visible = _flat_by_relation(public_payload)
    technical = {
        item["indicatorId"]: item
        for item in technical_payload.get("indicators") or []
    }
    records = []
    for entry in POLICY_ENTRIES:
        relation = RELATIONS[entry["relationId"]]
        result = visible.get(relation["relationId"])
        technical_indicator = technical.get(relation["indicatorId"]) or {}
        methodology = technical_indicator.get("methodology") or {}
        current = (result or {}).get("current") or {}
        records.append(
            {
                "municipalityId": municipality_id,
                "relationId": relation["relationId"],
                "present": result is not None,
                "mode": _legacy_mode(relation),
                "value": current.get("value"),
                "year": current.get("year"),
                "numerator": methodology.get("numerator"),
                "denominator": methodology.get("denominator"),
                "unit": current.get("unit"),
                "reference": _reference(result, relation),
                "deadline": (
                    (_reference(result, relation) or {}).get("year")
                    if relation["canDistance"]
                    else None
                ),
                "distance": (
                    (result or {}).get("distance")
                    if relation["canDistance"]
                    else None
                ),
                "status": (
                    (result or {}).get("status")
                    if relation["canStatus"]
                    else None
                ),
                "classification": (
                    (result or {}).get("classification")
                    if relation["canStatus"]
                    else None
                ),
                "trajectory": _trajectory(result, relation),
                "stateComparison": _state_comparison(result, relation),
                "themeId": entry["themeId"],
                "displayOrder": entry["displayOrder"],
                "summaryPriority": entry["summaryPriority"],
                "priorityOrder": _priority_order(entry),
                "absenceReason": None if result is not None else "unavailable",
            }
        )
    return records


def _normalized_summary(records: list[dict]) -> dict:
    present = [record for record in records if record["present"]]
    classifying = [
        record
        for record in present
        if RELATIONS[record["relationId"]]["includeInReferenceSummary"]
    ]
    return {
        "availableResultCount": len(present),
        "unavailableResultCount": len(POLICY_ENTRIES) - len(present),
        "essentialAvailableCount": sum(
            record["summaryPriority"] == "essential" for record in present
        ),
        "complementaryAvailableCount": sum(
            record["summaryPriority"] == "standard" for record in present
        ),
        "advanceCount": sum(
            record["classification"] == "advance" for record in classifying
        ),
        "maintainCount": sum(
            record["classification"] == "maintain" for record in classifying
        ),
        "unclassifiedCount": sum(
            record["classification"] is None for record in classifying
        ),
        "stateComparisonCount": sum(
            record["stateComparison"] is not None for record in classifying
        ),
        "stateAboveOrNearCount": sum(
            (record["stateComparison"] or {}).get("state") in {"above", "near"}
            for record in classifying
        ),
        "stateBelowCount": sum(
            (record["stateComparison"] or {}).get("state") == "below"
            for record in classifying
        ),
    }


def _digest(value) -> str:
    def normalize_numbers(item):
        if isinstance(item, float) and item.is_integer():
            return int(item)
        if isinstance(item, list):
            return [normalize_numbers(child) for child in item]
        if isinstance(item, dict):
            return {
                key: normalize_numbers(child)
                for key, child in item.items()
            }
        return item

    normalized = json.dumps(
        normalize_numbers(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(normalized).hexdigest()


class Pne2026DiagnosticSnapshotParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        before_records = []
        after_records = []
        hidden = Counter()
        visible_counts = []
        above_100 = 0
        raw_available = 0
        duplicates = 0
        before_summaries = []
        after_summaries = []

        with _GitBlobSnapshot() as snapshot:
            registry = snapshot.json("public/data/municipios_index.json")
            for municipality in registry["municipios"]:
                municipality_id = municipality["id_municipio"]
                diagnostic = snapshot.json(
                    f"public/data/municipios/{municipality_id}/diagnostico.json"
                )
                pne_cycle = snapshot.json(
                    f"public/data/municipios/{municipality_id}/index.json"
                )["pne_2026_2036"]
                before = diagnostic["pne2026PublicDiagnosticV2"]
                after = build_pne2026_public_diagnostic_v2(
                    diagnostic, pne_cycle
                )
                normalized_before = _normalized_records(
                    municipality_id, before, diagnostic
                )
                normalized_after = _normalized_records(
                    municipality_id, after, diagnostic
                )
                before_records.extend(normalized_before)
                after_records.extend(normalized_after)
                before_summary = _normalized_summary(normalized_before)
                after_summary = _normalized_summary(normalized_after)
                before_summaries.append(
                    {
                        "municipalityId": municipality_id,
                        "summary": before_summary,
                    }
                )
                after_summaries.append(
                    {
                        "municipalityId": municipality_id,
                        "summary": after_summary,
                    }
                )
                for key, expected in after_summary.items():
                    if after["summary"].get(key) != expected:
                        raise AssertionError(
                            f"{municipality_id}: summary.{key}="
                            f"{after['summary'].get(key)}; esperado {expected}"
                        )
                present = [row for row in normalized_after if row["present"]]
                visible_counts.append(len(present))
                duplicates += len(present) - len(
                    {row["relationId"] for row in present}
                )
                above_100 += sum(
                    isinstance(row["value"], (int, float))
                    and row["value"] > 100
                    for row in present
                )
                raw_results = _flat_by_relation(before)
                raw_available += len(raw_results)
                for relation_id in raw_results:
                    relation = RELATIONS[relation_id]
                    if _legacy_mode(relation) == "hidden":
                        hidden[relation_id] += 1

        cls.before_records = before_records
        cls.after_records = after_records
        cls.before_summaries = before_summaries
        cls.after_summaries = after_summaries
        cls.metrics = {
            "municipalities": len(visible_counts),
            "previouslyAvailable": raw_available,
            "visible": sum(row["present"] for row in after_records),
            "progress": sum(
                row["present"] and row["mode"] == "progress"
                for row in after_records
            ),
            "complementary": sum(
                row["present"] and row["mode"] == "complementary"
                for row in after_records
            ),
            "hidden": sum(hidden.values()),
            "minimum": min(visible_counts),
            "maximum": max(visible_counts),
            "duplicates": duplicates,
            "above100": above_100,
        }

    def test_record_by_record_normalized_parity(self):
        self.assertEqual(self.before_records, self.after_records)
        self.assertEqual(
            _digest(self.before_records),
            _digest(self.after_records),
        )

    def test_required_municipal_counts(self):
        self.assertEqual(
            self.metrics,
            {
                "municipalities": BASELINE["municipalCounts"]["municipalities"],
                "previouslyAvailable": BASELINE["municipalCounts"][
                    "previouslyAvailable"
                ],
                "visible": BASELINE["municipalCounts"]["visibleAvailable"],
                "progress": BASELINE["municipalCounts"]["progressAvailable"],
                "complementary": BASELINE["municipalCounts"][
                    "complementaryAvailable"
                ],
                "hidden": BASELINE["municipalCounts"]["hiddenExcluded"],
                "minimum": BASELINE["municipalCounts"]["visibleMinimum"],
                "maximum": BASELINE["municipalCounts"]["visibleMaximum"],
                "duplicates": BASELINE["municipalCounts"][
                    "duplicateGoalIndicatorMunicipality"
                ],
                "above100": BASELINE["municipalCounts"][
                    "visibleValuesAbove100"
                ],
            },
        )

    def test_historical_baseline_is_preserved_with_one_documented_delta(self):
        self.assertEqual(
            HISTORICAL_BASELINE["schemaVersion"],
            "pne2026-diagnostic-2b2a-baseline-v1",
        )
        self.assertEqual(
            BASELINE["intentionalDifferencesFrom2b2a"]["relationId"],
            "relation.4.a.basico_15_17",
        )
        self.assertTrue(
            BASELINE["intentionalDifferencesFrom2b2a"]["allOtherRelationsEqual"]
        )
        old_counts = HISTORICAL_BASELINE["municipalCounts"]
        new_counts = BASELINE["municipalCounts"]
        self.assertEqual(
            new_counts["visibleAvailable"],
            old_counts["visibleAvailable"],
        )
        self.assertEqual(
            new_counts["progressAvailable"],
            old_counts["progressAvailable"] - 497,
        )
        self.assertEqual(
            new_counts["complementaryAvailable"],
            old_counts["complementaryAvailable"] + 497,
        )

    def test_classification_and_summary_inputs_are_identical(self):
        before = [
            (
                row["municipalityId"],
                row["relationId"],
                row["classification"],
                row["status"],
            )
            for row in self.before_records
            if row["present"] and row["mode"] == "progress"
        ]
        after = [
            (
                row["municipalityId"],
                row["relationId"],
                row["classification"],
                row["status"],
            )
            for row in self.after_records
            if row["present"] and row["mode"] == "progress"
        ]
        self.assertEqual(before, after)
        self.assertEqual(Counter(item[2] for item in before), Counter(item[2] for item in after))
        self.assertEqual(self.before_summaries, self.after_summaries)
        self.assertEqual(
            _digest(self.before_summaries),
            _digest(self.after_summaries),
        )


if __name__ == "__main__":
    unittest.main()
