# AI-Assisted TLC Rule Extraction

Extract traceability-lot-code rule drafts for assignment, preservation, source reference, transformation handling, uniqueness, and linkage.

## Extraction focus

- TLC assignment trigger
- TLC preservation through shipping/receiving
- TLC source and source-reference handling
- transformation input-to-output TLC linkage
- uniqueness or lot identity requirements

## Required JSON schema

{
  "$defs": {
    "CitationRef": {
      "additionalProperties": false,
      "properties": {
        "source_id": {
          "minLength": 1,
          "title": "Source Id",
          "type": "string"
        },
        "chunk_id": {
          "minLength": 1,
          "title": "Chunk Id",
          "type": "string"
        },
        "citation_anchor": {
          "minLength": 1,
          "title": "Citation Anchor",
          "type": "string"
        },
        "authority_rank": {
          "minLength": 1,
          "title": "Authority Rank",
          "type": "string"
        },
        "source_url": {
          "minLength": 1,
          "title": "Source Url",
          "type": "string"
        },
        "section_ref": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Section Ref"
        },
        "page_number": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Page Number"
        },
        "support_text": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Support Text"
        }
      },
      "required": [
        "source_id",
        "chunk_id",
        "citation_anchor",
        "authority_rank",
        "source_url"
      ],
      "title": "CitationRef",
      "type": "object"
    },
    "ConfidenceLevel": {
      "enum": [
        "high",
        "medium",
        "low",
        "unsupported",
        "conflict"
      ],
      "title": "ConfidenceLevel",
      "type": "string"
    },
    "CteType": {
      "enum": [
        "harvesting",
        "cooling",
        "initial_packing",
        "first_land_based_receiving",
        "shipping",
        "receiving",
        "transformation",
        "traceability_plan",
        "other"
      ],
      "title": "CteType",
      "type": "string"
    },
    "DraftMetadata": {
      "additionalProperties": false,
      "properties": {
        "extraction_method": {
          "$ref": "#/$defs/ExtractionMethod"
        },
        "confidence": {
          "$ref": "#/$defs/ConfidenceLevel"
        },
        "review_status": {
          "$ref": "#/$defs/ReviewStatus",
          "default": "draft"
        },
        "reviewer_notes": {
          "items": {
            "type": "string"
          },
          "title": "Reviewer Notes",
          "type": "array"
        },
        "source_chunk_ids": {
          "items": {
            "type": "string"
          },
          "title": "Source Chunk Ids",
          "type": "array"
        }
      },
      "required": [
        "extraction_method",
        "confidence"
      ],
      "title": "DraftMetadata",
      "type": "object"
    },
    "ExtractionMethod": {
      "enum": [
        "deterministic",
        "ai_assisted",
        "human_authored",
        "imported_template"
      ],
      "title": "ExtractionMethod",
      "type": "string"
    },
    "RequirementStatus": {
      "enum": [
        "required",
        "conditional",
        "optional",
        "not_applicable",
        "unknown"
      ],
      "title": "RequirementStatus",
      "type": "string"
    },
    "ReviewStatus": {
      "enum": [
        "draft",
        "needs_review",
        "approved",
        "rejected",
        "superseded",
        "conflict_detected"
      ],
      "title": "ReviewStatus",
      "type": "string"
    },
    "TlcRuleKind": {
      "enum": [
        "assignment",
        "preservation",
        "source_reference",
        "transformation_handling",
        "uniqueness",
        "linkage",
        "other"
      ],
      "title": "TlcRuleKind",
      "type": "string"
    }
  },
  "additionalProperties": false,
  "properties": {
    "citations": {
      "items": {
        "$ref": "#/$defs/CitationRef"
      },
      "minItems": 1,
      "title": "Citations",
      "type": "array"
    },
    "metadata": {
      "$ref": "#/$defs/DraftMetadata"
    },
    "tlc_rule_id": {
      "minLength": 1,
      "title": "Tlc Rule Id",
      "type": "string"
    },
    "rule_kind": {
      "$ref": "#/$defs/TlcRuleKind"
    },
    "applies_to_ctes": {
      "items": {
        "$ref": "#/$defs/CteType"
      },
      "minItems": 1,
      "title": "Applies To Ctes",
      "type": "array"
    },
    "applies_to_food_scope": {
      "minLength": 1,
      "title": "Applies To Food Scope",
      "type": "string"
    },
    "assignment_rule": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Assignment Rule"
    },
    "preservation_rule": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Preservation Rule"
    },
    "source_reference_rule": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Source Reference Rule"
    },
    "transformation_handling": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Transformation Handling"
    },
    "uniqueness_rule": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Uniqueness Rule"
    },
    "lineage_rule": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Lineage Rule"
    },
    "required_status": {
      "$ref": "#/$defs/RequirementStatus",
      "default": "conditional"
    },
    "evidence_examples": {
      "items": {
        "type": "string"
      },
      "title": "Evidence Examples",
      "type": "array"
    },
    "unresolved_questions": {
      "items": {
        "type": "string"
      },
      "title": "Unresolved Questions",
      "type": "array"
    }
  },
  "required": [
    "citations",
    "metadata",
    "tlc_rule_id",
    "rule_kind",
    "applies_to_ctes",
    "applies_to_food_scope"
  ],
  "title": "TlcRule",
  "type": "object"
}

## Source chunks

[
  {
    "source_id": "ecfr-21-cfr-1-subpart-s",
    "chunk_id": "ecfr-21-cfr-1-subpart-s-21-cfr-1-1320-5",
    "citation_anchor": "21 CFR 1.1320",
    "authority_rank": "codified_rule",
    "source_url": "https://www.ecfr.gov/api/versioner/v1/full/2026-06-11/title-21.xml?part=1",
    "section_ref": "21 CFR 1.1320",
    "page_number": null,
    "text": "(a) You must assign a traceability lot code when you do any of the following: Initially pack a raw agricultural commodity other than a food obtained from a fishing vessel; perform the first land-based receiving of a food obtained from a fishing vessel; or transform a food. (b) Except as otherwise specified in this subpart, you must not establish a new traceability lot code when you conduct other activities ( e.g., shipping) for a food on the Food Traceability List."
  },
  {
    "source_id": "ecfr-21-cfr-1-subpart-s",
    "chunk_id": "ecfr-21-cfr-1-subpart-s-21-cfr-1-1330-7",
    "citation_anchor": "21 CFR 1.1330",
    "authority_rank": "codified_rule",
    "source_url": "https://www.ecfr.gov/api/versioner/v1/full/2026-06-11/title-21.xml?part=1",
    "section_ref": "21 CFR 1.1330",
    "page_number": null,
    "text": "(a) Except as specified in paragraph (c) of this section, for each traceability lot of a raw agricultural commodity (other than a food obtained from a fishing vessel) on the Food Traceability List you initially pack, you must maintain records containing the following information and linking this information to the traceability lot: (1) The commodity and, if applicable, variety of the food received; (2) The date you received the food; (3) The quantity and unit of measure of the food received ( e.g., 75 bins, 200 pounds); (4) The location description for the farm where the food was harvested; (5) For produce, the name of the field or other growing area from which the food was harvested (which must correspond to the name used by the grower), or other information identifying the harvest location at least as precisely as the field or other growing area name; (6) For aquacultured food, the name of the container ( e.g., pond, pool, tank, cage) from which the food was harvested (which must correspond to the container name used by the aquaculture farmer) or other information identifying the harvest location at least as precisely as the container name; (7) The business name and phone number for the harvester of the food; (8) The date of harvesting; (9) The location description for where the food was cooled (if applicable); (10) The date of cooling (if applicable); (11) The traceability lot code you assigned; (12) The product description of the packed food; (13) The quantity and unit of measure of the packed food ( e.g., 6 cases, 25 reusable plastic containers, 100 tanks, 200 pounds); (14) The location description for where you initially packed the food ( i.e., the traceability lot code source), and (if applicable) the traceability lot code source reference; (15) The date of initial packing; and (16) The reference document type and reference document number. (b) For each traceability lot of sprouts (except soil- or substrate-grown sprouts harvested without their roots) you initially pack, you must also maintain records containing the following information and linking this information to the traceability lot: (1) The location description for the grower of seeds for sprouting and the date of seed harvesting, if either is available; (2) The location description for the seed conditioner or processor, the associated seed lot code, and the date of conditioning or processing; (3) The location description for the seed packinghouse (including any repackers), the date of packing (and of repacking, if applicable), and any associated seed lot code assigned by the seed packinghouse; (4) The location description for the seed supplier, any seed lot code assigned by the seed supplier (including the master lot and sub-lot codes), and any new seed lot code assigned by the sprouter; (5) A description of the seeds, including the seed type or taxonomic name, growing specifications, type of packaging, and (if applicable) antimicrobial treatment; (6) The date of receipt of the seeds by the sprouter; and (7) The reference document type and reference document number. (c) For each traceability lot of a raw agricultural commodity (other than a food obtained from a fishing vessel) on the Food Traceability List you initially pack that you receive from a person to whom this subpart does not apply, you must maintain records containing the following information and linking this information to the traceability lot: (1) The commodity and, if applicable, variety of the food received; (2) The date you received the food; (3) The quantity and unit of measure of the food received ( e.g., 75 bins, 200 pounds); (4) The location description for the person from whom you received the food; (5) The traceability lot code you assigned; (6) The product description of the packed food; (7) The quantity and unit of measure of the packed food ( e.g., 6 cases, 25 reusable plastic containers, 100 tanks, 200 pounds); (8) The location description for where you initially packed the food ( i.e., the traceability lot code source), and (if applicable) the traceability lot code source reference; (9) The date of initial packing; and (10) The reference document type and reference document number."
  },
  {
    "source_id": "ecfr-21-cfr-1-subpart-s",
    "chunk_id": "ecfr-21-cfr-1-subpart-s-21-cfr-1-1335-8",
    "citation_anchor": "21 CFR 1.1335",
    "authority_rank": "codified_rule",
    "source_url": "https://www.ecfr.gov/api/versioner/v1/full/2026-06-11/title-21.xml?part=1",
    "section_ref": "21 CFR 1.1335",
    "page_number": null,
    "text": "For each traceability lot of a food obtained from a fishing vessel for which you are the first land-based receiver, you must maintain records containing the following information and linking this information to the traceability lot: (a) The traceability lot code you assigned; (b) The species and/or acceptable market name for unpackaged food, or the product description for packaged food; (c) The quantity and unit of measure of the food ( e.g., 300 kg); (d) The harvest date range and locations (as identified under the National Marine Fisheries Service Ocean Geographic Code, the United Nations Food and Agriculture Organization Major Fishing Area list, or any other widely recognized geographical location standard) for the trip during which the food was caught; (e) The location description for the first land-based receiver ( i.e., the traceability lot code source), and (if applicable) the traceability lot code source reference; (f) The date the food was landed; and (g) The reference document type and reference document number."
  },
  {
    "source_id": "ecfr-21-cfr-1-subpart-s",
    "chunk_id": "ecfr-21-cfr-1-subpart-s-21-cfr-1-1340-9",
    "citation_anchor": "21 CFR 1.1340",
    "authority_rank": "codified_rule",
    "source_url": "https://www.ecfr.gov/api/versioner/v1/full/2026-06-11/title-21.xml?part=1",
    "section_ref": "21 CFR 1.1340",
    "page_number": null,
    "text": "(a) For each traceability lot of a food on the Food Traceability List you ship, you must maintain records containing the following information and linking this information to the traceability lot: (1) The traceability lot code for the food; (2) The quantity and unit of measure of the food ( e.g., 6 cases, 25 reusable plastic containers, 100 tanks, 200 pounds); (3) The product description for the food; (4) The location description for the immediate subsequent recipient (other than a transporter) of the food; (5) The location description for the location from which you shipped the food; (6) The date you shipped the food; (7) The location description for the traceability lot code source, or the traceability lot code source reference; and (8) The reference document type and reference document number. (b) You must provide (in electronic, paper, or other written form) the information in paragraphs (a)(1) through (7) of this section to the immediate subsequent recipient (other than a transporter) of each traceability lot that you ship. (c) This section does not apply to the shipment of a food that occurs before the food is initially packed (if the food is a raw agricultural commodity not obtained from a fishing vessel)."
  },
  {
    "source_id": "ecfr-21-cfr-1-subpart-s",
    "chunk_id": "ecfr-21-cfr-1-subpart-s-21-cfr-1-1345-10",
    "citation_anchor": "21 CFR 1.1345",
    "authority_rank": "codified_rule",
    "source_url": "https://www.ecfr.gov/api/versioner/v1/full/2026-06-11/title-21.xml?part=1",
    "section_ref": "21 CFR 1.1345",
    "page_number": null,
    "text": "(a) Except as specified in paragraphs (b) and (c) of this section, for each traceability lot of a food on the Food Traceability List you receive, you must maintain records containing the following information and linking this information to the traceability lot: (1) The traceability lot code for the food; (2) The quantity and unit of measure of the food ( e.g., 6 cases, 25 reusable plastic containers, 100 tanks, 200 pounds); (3) The product description for the food; (4) The location description for the immediate previous source (other than a transporter) for the food; (5) The location description for where the food was received; (6) The date you received the food; (7) The location description for the traceability lot code source, or the traceability lot code source reference; and (8) The reference document type and reference document number. (b) For each traceability lot of a food on the Food Traceability List you receive from a person to whom this subpart does not apply, you must maintain records containing the following information and linking this information to the traceability lot: (1) The traceability lot code for the food, which you must assign if one has not already been assigned (except that this paragraph does not apply if you are a retail food establishment or restaurant); (2) The quantity and unit of measure of the food ( e.g., 6 cases, 25 reusable plastic containers, 100 tanks, 200 pounds); (3) The product description for the food; (4) The location description for the immediate previous source (other than a transporter) for the food; (5) The location description for where the food was received ( i.e., the traceability lot code source), and (if applicable) the traceability lot code source reference; (6) The date you received the food; and (7) The reference document type and reference document number. (c) This section does not apply to receipt of a food that occurs before the food is initially packed (if the food is a raw agricultural commodity not obtained from a fishing vessel) or to the receipt of a food by the first land-based receiver (if the food is obtained from a fishing vessel)."
  },
  {
    "source_id": "ecfr-21-cfr-1-subpart-s",
    "chunk_id": "ecfr-21-cfr-1-subpart-s-21-cfr-1-1350-11",
    "citation_anchor": "21 CFR 1.1350",
    "authority_rank": "codified_rule",
    "source_url": "https://www.ecfr.gov/api/versioner/v1/full/2026-06-11/title-21.xml?part=1",
    "section_ref": "21 CFR 1.1350",
    "page_number": null,
    "text": "(a) Except as specified in paragraphs (b) and (c) of this section, for each new traceability lot of food you produce through transformation, you must maintain records containing the following information and linking this information to the new traceability lot: (1) For the food on the Food Traceability List used in transformation (if applicable), the following information: (i) The traceability lot code for the food; (ii) The product description for the food to which the traceability lot code applies; and (iii) For each traceability lot used, the quantity and unit of measure of the food used from that lot. (2) For the food produced through transformation, the following information: (i) The new traceability lot code for the food; (ii) The location description for where you transformed the food ( i.e., the traceability lot code source), and (if applicable) the traceability lot code source reference; (iii) The date transformation was completed; (iv) The product description for the food; (v) The quantity and unit of measure of the food ( e.g., 6 cases, 25 reusable plastic containers, 100 tanks, 200 pounds); and (vi) The reference document type and reference document number for the transformation event. (b) For each traceability lot produced through transformation of a raw agricultural commodity (other than a food obtained from a fishing vessel) on the Food Traceability List that was not initially packed prior to your transformation of the food, you must maintain records containing the information specified in \u00a7 1.1330(a) or (c), and, if the raw agricultural commodity is sprouts, the information specified in \u00a7 1.1330(b). (c) Paragraphs (a) and (b) of this section do not apply to retail food establishments and restaurants with respect to foods they do not ship ( e.g., foods they sell or send directly to consumers)."
  },
  {
    "source_id": "fda-traceability-lot-code",
    "chunk_id": "fda-traceability-lot-code-document-1",
    "citation_anchor": "Document",
    "authority_rank": "support",
    "source_url": "https://www.fda.gov/food/food-safety-modernization-act-fsma/traceability-lot-code",
    "section_ref": "Document",
    "page_number": null,
    "text": "An official website of the United States government Search Menu Submit search"
  },
  {
    "source_id": "fda-traceability-lot-code",
    "chunk_id": "fda-traceability-lot-code-regulated-product-s-15",
    "citation_anchor": "Regulated Product(s)",
    "authority_rank": "support",
    "source_url": "https://www.fda.gov/food/food-safety-modernization-act-fsma/traceability-lot-code",
    "section_ref": "Regulated Product(s)",
    "page_number": null,
    "text": "Food & Beverages Follow FDA on Facebook Follow FDA on X Follow FDA on Instagram Follow FDA on LinkedIn View FDA videos on YouTube Subscribe to FDA RSS feeds Contact Number 1-888-INFO-FDA (1-888-463-6332) Back to"
  },
  {
    "source_id": "fda-traceability-lot-code",
    "chunk_id": "fda-traceability-lot-code-traceability-lot-code-2",
    "citation_anchor": "Traceability Lot Code",
    "authority_rank": "support",
    "source_url": "https://www.fda.gov/food/food-safety-modernization-act-fsma/traceability-lot-code",
    "section_ref": "Traceability Lot Code",
    "page_number": null,
    "text": "| | | | The goal of the Food Traceability rule is to ensure Key Data Elements (KDEs) can be maintained across the supply chain for more efficient and effective tracing while providing firms flexibility within their existing tracing systems. The traceability lot code (TLC) is an integral component of the rule\u2019s requirements. It links to the other KDEs required, including the TLC Source, which provides the physical location where the traceability lot code for an FTL food was assigned. Requiring documentation of traceability lot codes and traceability lot code sources enables FDA to identify the source of the food faster \u2013 by enabling FDA to skip steps in the supply chain, link a food to the firms that have handled it, and ultimately lead FDA back to the source of the food during an outbreak investigation. Here\u2019s a closer look at traceability lot code, traceability lot code source, and traceability lot code source reference."
  },
  {
    "source_id": "fda-traceability-lot-code",
    "chunk_id": "fda-traceability-lot-code-what-are-some-examples-of-traceability-lot-codes-4",
    "citation_anchor": "What are some examples of traceability lot codes?",
    "authority_rank": "support",
    "source_url": "https://www.fda.gov/food/food-safety-modernization-act-fsma/traceability-lot-code",
    "section_ref": "What are some examples of traceability lot codes?",
    "page_number": null,
    "text": "Several food industry-supported traceability initiatives offer best practices and standards for uniquely identifying a lot of food using a combination of a globally unique product identifier, firm-assigned internal lot code, and standard date code. Other examples include a Julian date, a lot code, batch code or other production code. This information, taken together, could be used as a traceability lot code, provided it meets the definition of \u201ctraceability lot code\u201d in the final rule. Some examples of traceability lot codes are below:"
  }
]

Return a JSON array of records. No Markdown. No commentary.