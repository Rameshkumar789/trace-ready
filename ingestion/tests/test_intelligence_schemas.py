import unittest

from pydantic import ValidationError

from traceready_ingestion.intelligence.schemas import (
    CitationRef,
    ConfidenceLevel,
    CteType,
    DraftMetadata,
    ExtractionMethod,
    RequirementStatus,
    ReviewStatus,
    ScenarioActor,
    ScenarioBenchmark,
    ScenarioEvent,
    ScenarioExpectedFinding,
    ScenarioExpectation,
    SortableExportField,
    TlcRule,
    TlcRuleKind,
)


def citation() -> CitationRef:
    return CitationRef(
        source_id="source",
        chunk_id="chunk",
        citation_anchor="anchor",
        authority_rank="codified_rule",
        source_url="https://example.test/source",
        support_text="support",
    )


def metadata() -> DraftMetadata:
    return DraftMetadata(
        extraction_method=ExtractionMethod.HUMAN_AUTHORED,
        confidence=ConfidenceLevel.MEDIUM,
        review_status=ReviewStatus.DRAFT,
        source_chunk_ids=["chunk"],
    )


class IntelligenceSchemasTest(unittest.TestCase):
    def test_tlc_rule_requires_rule_text(self):
        with self.assertRaises(ValidationError):
            TlcRule(
                tlc_rule_id="tlc_rule",
                rule_kind=TlcRuleKind.ASSIGNMENT,
                applies_to_ctes=[CteType.TRANSFORMATION],
                applies_to_food_scope="FTL foods",
                required_status=RequirementStatus.CONDITIONAL,
                citations=[citation()],
                metadata=metadata(),
            )

    def test_sortable_export_field_requires_snake_case_key(self):
        with self.assertRaises(ValidationError):
            SortableExportField(
                sortable_export_field_id="field",
                workbook_tab="Receiving",
                field_name="Traceability Lot Code",
                field_key="Traceability Lot Code",
                data_type="text",
                required_status=RequirementStatus.REQUIRED,
                source_mapping="receiving event",
                citations=[citation()],
                metadata=metadata(),
            )

    def test_scenario_events_must_reference_known_actors(self):
        with self.assertRaises(ValidationError):
            ScenarioBenchmark(
                scenario_benchmark_id="scenario",
                scenario_name="Scenario",
                scenario_source="FDA scenario",
                food_scope="FTL food",
                actors=[
                    ScenarioActor(actor_id="actor_a", actor_name="Actor A", role="shipper"),
                ],
                events=[
                    ScenarioEvent(
                        event_id="event_a",
                        cte_type=CteType.SHIPPING,
                        actor_id="actor_missing",
                        event_description="Shipment occurs.",
                    ),
                ],
                expectations=[
                    ScenarioExpectation(
                        expectation_id="expectation_a",
                        event_id="event_a",
                        expected_finding=ScenarioExpectedFinding.NEEDS_REVIEW,
                        expected_behavior="Reviewer validates expected behavior.",
                    )
                ],
                citations=[citation()],
                metadata=metadata(),
            )


if __name__ == "__main__":
    unittest.main()
