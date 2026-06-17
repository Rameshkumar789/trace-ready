from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from traceready_backend.intelligence.phase08_scenario_regression import (
    FDA_REQUEST_OBLIGATION_ID,
    KDE_OBLIGATION_BY_CTE,
    RECORDS_MAINTENANCE_OBLIGATION_ID,
    SCOPE_OBLIGATION_ID,
    SORTABLE_EXPORT_OBLIGATION_ID,
    TLC_ASSIGNMENT_CTES,
    TLC_ASSIGNMENT_OBLIGATION_ID,
    TRACEABILITY_PLAN_OBLIGATION_ID,
)
from traceready_backend.intelligence.schemas import CteType


GENERATED_AT = "2026-06-16T00:00:00Z"


class WebSourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    title: str
    url: str
    retrieved_at: str
    usage: str


class UnseenWebChallenge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: str
    name: str
    scenario_text: str
    source_references: list[WebSourceReference]
    expected_food_scope: str
    expected_ctes: list[str]
    expected_obligation_ids: list[str]
    negative_expectations: list[str] = Field(default_factory=list)
    rationale: str


class UnseenWebChallengeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: str
    status: str
    predicted_ctes: list[str]
    expected_ctes: list[str]
    missing_ctes: list[str]
    unexpected_ctes: list[str]
    predicted_obligation_ids: list[str]
    expected_obligation_ids: list[str]
    missing_obligation_ids: list[str]
    unexpected_obligation_ids: list[str]
    notes: list[str] = Field(default_factory=list)


class UnseenWebChallengePackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: dict[str, Any]
    challenges: list[UnseenWebChallenge]
    results: list[UnseenWebChallengeResult]


def build_unseen_web_challenge_package() -> UnseenWebChallengePackage:
    challenges = _challenge_set()
    results = [_evaluate_challenge(challenge) for challenge in challenges]
    return UnseenWebChallengePackage(
        summary=_summary(challenges, results),
        challenges=challenges,
        results=results,
    )


def write_unseen_web_challenge_artifacts(package: UnseenWebChallengePackage, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "summary": output_dir / "phase8-unseen-web-challenge-summary.json",
        "challengeSet": output_dir / "phase8-unseen-web-challenge-set.json",
        "results": output_dir / "phase8-unseen-web-challenge-results.json",
    }
    _write_json(outputs["summary"], package.summary)
    _write_json(outputs["challengeSet"], [challenge.model_dump(mode="json") for challenge in package.challenges])
    _write_json(outputs["results"], [result.model_dump(mode="json") for result in package.results])
    return {key: str(path) for key, path in outputs.items()}


def _evaluate_challenge(challenge: UnseenWebChallenge) -> UnseenWebChallengeResult:
    predicted_ctes = _infer_ctes(challenge.scenario_text)
    predicted_obligations = _obligations_for_ctes(predicted_ctes)
    expected_ctes = challenge.expected_ctes
    expected_obligations = challenge.expected_obligation_ids
    missing_ctes = sorted(set(expected_ctes) - set(predicted_ctes))
    unexpected_ctes = sorted(set(predicted_ctes) - set(expected_ctes))
    missing_obligations = sorted(set(expected_obligations) - set(predicted_obligations))
    unexpected_obligations = sorted(set(predicted_obligations) - set(expected_obligations))
    notes: list[str] = []
    if unexpected_ctes:
        notes.append("The current inference layer may be over-triggering CTEs for this unseen scenario.")
    if missing_ctes:
        notes.append("The current inference layer may be under-detecting CTEs for this unseen scenario.")
    if "shelf-stable" in challenge.scenario_text.lower() and CteType.TRANSFORMATION.value in unexpected_ctes:
        notes.append("Important gap: form-change / non-FTL finished-product logic needs stronger handling before customer audits.")
    status = "pass" if not missing_ctes and not unexpected_ctes and not missing_obligations and not unexpected_obligations else "gap"
    return UnseenWebChallengeResult(
        challenge_id=challenge.challenge_id,
        status=status,
        predicted_ctes=predicted_ctes,
        expected_ctes=expected_ctes,
        missing_ctes=missing_ctes,
        unexpected_ctes=unexpected_ctes,
        predicted_obligation_ids=predicted_obligations,
        expected_obligation_ids=expected_obligations,
        missing_obligation_ids=missing_obligations,
        unexpected_obligation_ids=unexpected_obligations,
        notes=notes,
    )


def _infer_ctes(text: str) -> list[str]:
    normalized = text.lower()
    ctes: list[str] = []
    _append_if(ctes, CteType.HARVESTING.value, normalized, [r"\bharvest", r"\bfarm harvest"])
    _append_if(ctes, CteType.COOLING.value, normalized, [r"\bcool", r"\bhydrocool", r"\bforced air"])
    _append_if(ctes, CteType.INITIAL_PACKING.value, normalized, [r"\binitial pack", r"\bpackinghouse", r"\bpack(s|ed)? .*for the first time"])
    _append_if(ctes, CteType.FIRST_LAND_BASED_RECEIVING.value, normalized, [r"\bfishing vessel", r"\bland(s|ed)? .*dock", r"\bfirst land"])
    _append_if(ctes, CteType.RECEIVING.value, normalized, [r"\breceiv", r"\binbound"])
    _append_if(ctes, CteType.TRANSFORMATION.value, normalized, [r"\btransform", r"\bfresh-cut", r"\bchop", r"\bslic", r"\bsmok", r"\bgrind", r"\brepack", r"\brelabel", r"\bcommingl", r"\bmix"])
    _append_if(ctes, CteType.SHIPPING.value, normalized, [r"\bship", r"\bsend(s|ing)? .*to", r"\boutbound", r"\bdistribution center", r"\bdistributor"])
    if "traceability plan" in normalized:
        ctes.insert(0, CteType.TRACEABILITY_PLAN.value)
    return _ordered_unique(ctes)


def _append_if(ctes: list[str], cte: str, text: str, patterns: list[str]) -> None:
    if any(re.search(pattern, text) for pattern in patterns):
        ctes.append(cte)


def _obligations_for_ctes(ctes: list[str]) -> list[str]:
    obligations = [SCOPE_OBLIGATION_ID, TRACEABILITY_PLAN_OBLIGATION_ID, RECORDS_MAINTENANCE_OBLIGATION_ID, FDA_REQUEST_OBLIGATION_ID, SORTABLE_EXPORT_OBLIGATION_ID]
    for cte in ctes:
        obligation_id = KDE_OBLIGATION_BY_CTE.get(cte)
        if obligation_id:
            obligations.append(obligation_id)
        if cte in TLC_ASSIGNMENT_CTES:
            obligations.append(TLC_ASSIGNMENT_OBLIGATION_ID)
    return _ordered_unique(obligations)


def _expected_obligations(ctes: list[str]) -> list[str]:
    return _obligations_for_ctes(ctes)


def _challenge_set() -> list[UnseenWebChallenge]:
    refs = _source_refs()
    return [
        UnseenWebChallenge(
            challenge_id="unseen_web:romaine_salad_kit",
            name="Fresh romaine salad kit through processor and foodservice DC",
            scenario_text=(
                "A farm harvests fresh romaine, cools it, and sends it to an initial packinghouse that assigns a lot. "
                "A fresh-cut processor receives the romaine, chops and mixes it into refrigerated salad kits, ships cases to a distribution center, "
                "and the distribution center receives and ships cases to restaurants."
            ),
            source_references=[refs["fda_ftl"], refs["fda_rule"], refs["produce_traceability"]],
            expected_food_scope="Fresh leafy greens and fresh-cut leafy greens are Food Traceability List foods.",
            expected_ctes=["harvesting", "cooling", "initial_packing", "receiving", "transformation", "shipping"],
            expected_obligation_ids=_expected_obligations(["harvesting", "cooling", "initial_packing", "receiving", "transformation", "shipping"]),
            rationale="This is not an FDA benchmark scenario; it is a customer-like leafy-greens flow derived from public FTL and traceability materials.",
        ),
        UnseenWebChallenge(
            challenge_id="unseen_web:fresh_mango_salsa",
            name="Refrigerated fresh mango salsa made from FTL ingredients",
            scenario_text=(
                "A processor receives fresh mangoes, fresh tomatoes, and fresh peppers. The facility chops and mixes the fresh ingredients into refrigerated fresh mango salsa, "
                "assigns a new production lot, and ships tubs to a grocery distribution center."
            ),
            source_references=[refs["fda_ftl"], refs["fda_rule"]],
            expected_food_scope="Fresh tropical tree fruit, tomatoes, peppers, and fresh-cut fruits or vegetables are Food Traceability List foods.",
            expected_ctes=["receiving", "transformation", "shipping"],
            expected_obligation_ids=_expected_obligations(["receiving", "transformation", "shipping"]),
            rationale="Tests transformation of a mixed fresh product that is not one of the FDA benchmark examples.",
        ),
        UnseenWebChallenge(
            challenge_id="unseen_web:tomato_paste_shelf_stable",
            name="Fresh tomatoes processed into shelf-stable canned tomato paste",
            scenario_text=(
                "A processor receives fresh tomatoes, cooks and concentrates them into shelf-stable canned tomato paste, and ships sealed cans to a distributor."
            ),
            source_references=[refs["fda_ftl"], refs["fda_rule"]],
            expected_food_scope="Fresh tomatoes are on the Food Traceability List, but the shelf-stable canned finished product is not expected to remain in fresh FTL form.",
            expected_ctes=["receiving"],
            expected_obligation_ids=_expected_obligations(["receiving"]),
            negative_expectations=["Do not trigger transformation or outbound shipping duties for the shelf-stable non-FTL finished product without a reviewer-approved form-change rule."],
            rationale="This deliberately tests form-change logic rather than copying the FDA canned-tuna benchmark.",
        ),
        UnseenWebChallenge(
            challenge_id="unseen_web:refrigerated_smoked_salmon",
            name="Fresh salmon transformed into refrigerated smoked salmon",
            scenario_text=(
                "A seafood processor receives fresh salmon fillets, hot-smokes them into refrigerated smoked salmon, assigns a new lot, and ships cases to a foodservice distributor."
            ),
            source_references=[refs["fda_ftl"], refs["fda_rule"], refs["seafood_traceability"]],
            expected_food_scope="Finfish and refrigerated smoked finfish are Food Traceability List foods.",
            expected_ctes=["receiving", "transformation", "shipping"],
            expected_obligation_ids=_expected_obligations(["receiving", "transformation", "shipping"]),
            rationale="Tests seafood transformation without using the FDA tuna benchmark.",
        ),
        UnseenWebChallenge(
            challenge_id="unseen_web:dockside_mahi_mahi",
            name="Fresh mahi-mahi first received from a fishing vessel",
            scenario_text=(
                "A fishing vessel lands fresh mahi-mahi at a processor dock. The first land-based receiver takes possession on land, assigns a traceability lot, and ships loins to a distributor."
            ),
            source_references=[refs["fda_ftl"], refs["fda_rule"], refs["seafood_traceability"]],
            expected_food_scope="Mahi-mahi is a listed histamine-producing finfish example on the Food Traceability List.",
            expected_ctes=["first_land_based_receiving", "shipping"],
            expected_obligation_ids=_expected_obligations(["first_land_based_receiving", "shipping"]),
            rationale="Tests first-land-based receiving on a finfish other than tuna.",
        ),
        UnseenWebChallenge(
            challenge_id="unseen_web:restaurant_fresh_papaya_romaine",
            name="Restaurant receiving fresh papaya and romaine",
            scenario_text=(
                "A restaurant receives fresh papaya and fresh romaine from a distributor, stores the cases for service, and sells prepared portions directly to consumers."
            ),
            source_references=[refs["fda_ftl"], refs["fda_rule"]],
            expected_food_scope="Fresh papaya is a tropical tree fruit example and romaine is a leafy green example on the Food Traceability List.",
            expected_ctes=["receiving"],
            expected_obligation_ids=_expected_obligations(["receiving"]),
            rationale="Tests restaurant receiving without using the FDA traceability-plan restaurant example as the scenario.",
        ),
        UnseenWebChallenge(
            challenge_id="unseen_web:refrigerated_peanut_butter",
            name="Refrigerated peanut butter manufacturer",
            scenario_text=(
                "A manufacturer grinds roasted peanuts into refrigerated peanut butter, assigns a production lot, and ships jars to a retail distribution center."
            ),
            source_references=[refs["fda_ftl"], refs["fda_rule"]],
            expected_food_scope="Nut butters, including peanut butter, are Food Traceability List foods.",
            expected_ctes=["transformation", "shipping"],
            expected_obligation_ids=_expected_obligations(["transformation", "shipping"]),
            rationale="Tests a non-produce, non-seafood FTL category not covered by the FDA scenario benchmarks.",
        ),
        UnseenWebChallenge(
            challenge_id="unseen_web:fresh_basil_repack",
            name="Fresh basil repacked by a distributor",
            scenario_text=(
                "A distributor receives fresh basil cases, repacks and relabels them into smaller customer cases, and ships them to grocery stores."
            ),
            source_references=[refs["fda_ftl"], refs["fda_rule"], refs["produce_traceability"]],
            expected_food_scope="Fresh herbs, including basil, are Food Traceability List foods.",
            expected_ctes=["receiving", "transformation", "shipping"],
            expected_obligation_ids=_expected_obligations(["receiving", "transformation", "shipping"]),
            rationale="Tests repacking/relabeling transformation behavior for fresh herbs.",
        ),
    ]


def _source_refs() -> dict[str, WebSourceReference]:
    return {
        "fda_ftl": WebSourceReference(
            source_id="web-fda-food-traceability-list-2026-04-01",
            title="FDA Food Traceability List",
            url="https://www.fda.gov/food/food-safety-modernization-act-fsma/food-traceability-list",
            retrieved_at=GENERATED_AT,
            usage="Identifies FTL food categories used to construct unseen challenge foods.",
        ),
        "fda_rule": WebSourceReference(
            source_id="web-fda-food-traceability-final-rule-page-2026-06-16",
            title="FDA FSMA Final Rule on Requirements for Additional Traceability Records for Certain Foods",
            url="https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods",
            retrieved_at=GENERATED_AT,
            usage="Defines CTE, TLC, traceability plan, records, FDA request, and sortable spreadsheet concepts for challenge expectations.",
        ),
        "produce_traceability": WebSourceReference(
            source_id="web-produce-traceability-overview",
            title="Produce traceability overview",
            url="https://en.wikipedia.org/wiki/Produce_traceability",
            retrieved_at=GENERATED_AT,
            usage="Provides non-FDA general produce supply-chain context for farm-to-retail challenge narratives.",
        ),
        "seafood_traceability": WebSourceReference(
            source_id="web-seafood-traceability-context",
            title="Seafood traceability and supply-chain complexity context",
            url="https://www.seriouseats.com/seafood-fraud-mislabeled-fish-resolution",
            retrieved_at=GENERATED_AT,
            usage="Provides non-FDA general seafood supply-chain context for unseen seafood challenge narratives.",
        ),
    }


def _summary(challenges: list[UnseenWebChallenge], results: list[UnseenWebChallengeResult]) -> dict[str, Any]:
    status_counts = Counter(result.status for result in results)
    return {
        "generatedAt": GENERATED_AT,
        "purpose": "Unseen web-derived challenge set for evaluating generalization; not an approved regulatory source package.",
        "challengeCount": len(challenges),
        "statusCounts": dict(sorted(status_counts.items())),
        "passRate": round(status_counts["pass"] / len(results), 3) if results else 0,
        "gapCount": status_counts["gap"],
        "challengeIds": [challenge.challenge_id for challenge in challenges],
        "knownLimits": [
            "Challenge scenarios are web-derived and synthetic; they are not reviewer-approved legal interpretations.",
            "The current inference layer is deterministic and keyword-based, so failures identify rule-engine gaps rather than model-statistical performance.",
            "Form-change and finished-product scope logic must be strengthened before relying on unseen customer scenarios.",
        ],
    }


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
