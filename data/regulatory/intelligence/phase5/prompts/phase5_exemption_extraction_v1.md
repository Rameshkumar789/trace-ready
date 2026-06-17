# AI-Assisted Exemption Extraction

Extract exemption-rule drafts with eligibility conditions, effect, documentation needs, and decision questions.

## Extraction focus

- exemption type
- eligibility condition
- full, partial, modified, or unknown effect
- requirements affected
- documentation needed
- entity, food, and CTE applicability

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
    "ExemptionEffect": {
      "enum": [
        "full",
        "partial",
        "modified_requirements",
        "not_exempt",
        "unknown"
      ],
      "title": "ExemptionEffect",
      "type": "string"
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
    "exemption_rule_id": {
      "minLength": 1,
      "title": "Exemption Rule Id",
      "type": "string"
    },
    "exemption_type": {
      "minLength": 1,
      "title": "Exemption Type",
      "type": "string"
    },
    "eligibility_condition": {
      "minLength": 1,
      "title": "Eligibility Condition",
      "type": "string"
    },
    "effect": {
      "$ref": "#/$defs/ExemptionEffect"
    },
    "affected_requirements": {
      "items": {
        "type": "string"
      },
      "title": "Affected Requirements",
      "type": "array"
    },
    "documentation_needed": {
      "items": {
        "type": "string"
      },
      "title": "Documentation Needed",
      "type": "array"
    },
    "applies_to_entities": {
      "items": {
        "type": "string"
      },
      "title": "Applies To Entities",
      "type": "array"
    },
    "applies_to_foods": {
      "items": {
        "type": "string"
      },
      "title": "Applies To Foods",
      "type": "array"
    },
    "applies_to_ctes": {
      "items": {
        "$ref": "#/$defs/CteType"
      },
      "title": "Applies To Ctes",
      "type": "array"
    },
    "decision_questions": {
      "items": {
        "type": "string"
      },
      "title": "Decision Questions",
      "type": "array"
    },
    "reviewer_warning": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Reviewer Warning"
    }
  },
  "required": [
    "citations",
    "metadata",
    "exemption_rule_id",
    "exemption_type",
    "eligibility_condition",
    "effect"
  ],
  "title": "ExemptionRule",
  "type": "object"
}

## Source chunks

[
  {
    "source_id": "ecfr-21-cfr-1-subpart-s",
    "chunk_id": "ecfr-21-cfr-1-subpart-s-21-cfr-1-1305-2",
    "citation_anchor": "21 CFR 1.1305",
    "authority_rank": "codified_rule",
    "source_url": "https://www.ecfr.gov/api/versioner/v1/full/2026-06-11/title-21.xml?part=1",
    "section_ref": "21 CFR 1.1305",
    "page_number": null,
    "text": "(a) Exemptions for certain small producers. (1) Certain produce farms. (i) This subpart does not apply to farms or the farm activities of farm mixed-type facilities with respect to the produce they grow, when the farm is not a covered farm under part 112 of this chapter in accordance with \u00a7 112.4(a) of this chapter, (ii) This subpart does not apply to produce farms when the average annual sum of the monetary value of their sales of produce and the market value of produce they manufacture, process, pack, or hold without sale ( e.g., held for a fee) during the previous 3-year period is no more than $25,000 (on a rolling basis), adjusted for inflation using 2020 as the baseline year for calculating the adjustment. (2) Certain shell egg producers. This subpart does not apply to shell egg producers with fewer than 3,000 laying hens at a particular farm, with respect to the shell eggs they produce at that farm. (3) Certain other producers of raw agricultural commodities. This subpart does not apply to producers of raw agricultural commodities other than produce or shell eggs ( e.g., aquaculture operations) when the average annual sum of the monetary value of their sales of raw agricultural commodities and the market value of the raw agricultural commodities they manufacture, process, pack, or hold without sale ( e.g., held for a fee) during the previous 3-year period is no more than $25,000 (on a rolling basis), adjusted for inflation using 2020 as the baseline year for calculating the adjustment. (b) Exemption for farms when food is sold or donated directly to consumers. This subpart does not apply to a farm with respect to food produced on the farm (including food that is also packaged on the farm) that is sold or donated directly to a consumer by the owner, operator, or agent in charge of the farm. (c) Inapplicability to certain food produced and packaged on a farm. This subpart does not apply to food produced and packaged on a farm, provided that: (1) The packaging of the food remains in place until the food reaches the consumer, and such packaging maintains the integrity of the product and prevents subsequent contamination or alteration of the product; and (2) The labeling of the food that reaches the consumer includes the name, complete address (street address, town, State, country, and zip or other postal code for a domestic farm and comparable information for a foreign farm), and business phone number of the farm on which the food was produced and packaged. FDA will waive the requirement to include a business phone number, as appropriate, to accommodate a religious belief of the individual in charge of the farm. (d) Exemptions and partial exemptions for foods that receive certain types of processing. This subpart does not apply to the following foods that receive certain types of processing: (1) Produce that receives commercial processing that adequately reduces the presence of microorganisms of public health significance, provided the conditions set forth in \u00a7 112.2(b) of this chapter are met for the produce; (2) Shell eggs when all eggs produced at the particular farm receive a treatment (as defined in \u00a7 118.3 of this chapter) in accordance with \u00a7 118.1(a)(2) of this chapter; (3) Food that you subject to a kill step, provided that you maintain records containing: (i) The information specified in \u00a7 1.1345 for your receipt of the food to which you apply the kill step (unless you have entered into a written agreement concerning your application of a kill step to the food in accordance with paragraph (d)(6) of this section); and (ii) A record of your application of the kill step; (4) Food that you change such that the food is no longer on the Food Traceability List, provided that you maintain records containing the information specified in \u00a7 1.1345 for your receipt of the food you change (unless you have entered into a written agreement concerning your changing of the food such that the food is no longer on the Food Traceability List in accordance with paragraph (d)(6) of this section); (5) Food that you receive that has previously been subjected to a kill step or that has previously been changed such that the food is no longer on the Food Traceability List; (6) Food that will be subjected to a kill step by an entity other than a retail food establishment, restaurant, or consumer; or that will be changed by an entity other than a retail food establishment, restaurant, or consumer, such that the food will no longer be on the Food Traceability List, provided that: (i) There is a written agreement between the shipper of the food and the receiver stating that the receiver will apply a kill step to the food or change the food such that it is no longer on the Food Traceability List; or (ii) There is a written agreement between the shipper of the food and the receiver stating that an entity in the supply chain subsequent to the receiver will apply a kill step to the food or change the food such that it is no longer on the Food Traceability List and that the receiver will only ship the food to another entity that agrees, in writing, it will: (A) Apply a kill step to the food or change the food such that it is no longer on the Food Traceability List; or (B) Enter into a similar written agreement with a subsequent receiver stating that a kill step will be applied to the food or that the food will be changed such that it is no longer on the Food Traceability List. (iii) A written agreement entered into in accordance with paragraph (d)(6)(i) or (ii) of this section must include the effective date, printed names and signatures of the persons entering into the agreement, and the substance of the agreement; and (iv) A written agreement entered into in accordance with paragraph (d)(6)(i) or (ii) must be maintained by both parties for as long as it is in effect and must be renewed at least once every 3 years. (e) Exemption for produce that is rarely consumed raw. This subpart does not apply to produce that is listed as rarely consumed raw in \u00a7 112.2(a)(1) of this chapter. (f) Exemption for raw bivalve molluscan shellfish. This subpart does not apply to raw bivalve molluscan shellfish that are covered by the requirements of the National Shellfish Sanitation Program, subject to the requirements of part 123, subpart C, and \u00a7 1240.60 of this chapter, or covered by a final equivalence determination by FDA for raw bivalve molluscan shellfish. (g) Exemption for persons who manufacture, process, pack, or hold certain foods subject to regulation by the U.S. Department of Agriculture (USDA). This subpart does not apply to persons who manufacture, process, pack, or hold food on the Food Traceability List during or after the time when the food is within the exclusive jurisdiction of the USDA under the Federal Meat Inspection Act (21 U.S.C. 601 et seq. ), the Poultry Products Inspection Act (21 U.S.C. 451 et seq. ), or the Egg Products Inspection Act (21 U.S.C. 1031 et seq. ). (h) Partial exemption for commingled raw agricultural commodities. (1) Except as specified in paragraph (h)(3) of this section, this subpart does not apply to commingled raw agricultural commodities (which, as defined in \u00a7 1.1310, do not include types of fruits and vegetables to which the standards for the growing, harvesting, packing, and holding of produce for human consumption in part 112 of this chapter apply). (2) Except as specified in paragraph (h)(3) of this section, this subpart does not apply to a raw agricultural commodity that will become a commingled raw agricultural commodity, provided that: (i) There is a written agreement between the shipper of the raw agricultural commodity and the receiver stating that the receiver will include the commodity as part of a commingled raw agricultural commodity; or (ii) There is a written agreement between the shipper of the raw agricultural commodity and the receiver stating that an entity in the supply chain subsequent to the receiver will include the commodity as part of a commingled raw agricultural commodity and that the receiver will only ship the raw agricultural commodity to another entity that agrees, in writing, it will either: (A) Include the raw agricultural commodity as part of a commingled raw agricultural commodity; or (B) Enter into a similar written agreement with a subsequent receiver stating that the raw agricultural commodity will become part of a commingled raw agricultural commodity; (iii) A written agreement entered into in accordance with paragraph (h)(2)(i) or (ii) of this section must include the effective date, printed names and signatures of the persons entering into the agreement, and the substance of the agreement; and (iv) A written agreement entered into in accordance with paragraph (h)(2)(i) or (ii) must be maintained by both parties for as long as it is in effect and must be renewed at least once every 3 years; (3) With respect to a commingled raw agricultural commodity that qualifies for either of the exemptions set forth in paragraphs (h)(1) and (2) of this section, if a person who manufactures, processes, packs, or holds such commodity is required to register with FDA under section 415 of the Federal Food, Drug, and Cosmetic Act with respect to the manufacturing, processing, packing, or holding of the applicable raw agricultural commodity, such person must maintain records identifying the immediate previous source of such raw agricultural commodity and the immediate subsequent recipient of such food in accordance with \u00a7\u00a7 1.337 and 1.345. Such records must be maintained for 2 years. (i) Exemption for small retail food establishments and small restaurants. This subpart does not apply to retail food establishments and restaurants with an average annual monetary value of food sold or provided during the previous 3-year period of no more than $250,000 (on a rolling basis), adjusted for inflation using 2020 as the baseline year for calculating the adjustment. (j) Partial exemption for retail food establishments and restaurants purchasing directly from a farm. (1) Except as specified in paragraph (j)(2) of this section, this subpart does not apply to a retail food establishment or restaurant with respect to a food that is produced on a farm (including food produced and packaged on the farm) and both sold and shipped directly to the retail food establishment or restaurant by the owner, operator, or agent in charge of that farm. (2) When a retail food establishment or restaurant purchases a food directly from a farm in accordance with paragraph (j)(1) of this section, the retail food establishment or restaurant must maintain a record documenting the name and address of the farm that was the source of the food. The retail food establishment or restaurant must maintain such a record for 180 days. (k) Partial exemption for retail food establishments and restaurants making certain purchases from another retail food establishment or restaurant. (1) Except as specified in paragraph (k)(2) of this section, this subpart does not apply to either entity when a purchase is made by a retail food establishment or restaurant from another retail food establishment or restaurant, and the purchase occurs on an ad hoc basis outside of the buyer's usual purchasing practice ( e.g., not pursuant to a contractual agreement to purchase food from the seller). (2) When a retail food establishment or restaurant purchases a food on the Food Traceability List from another retail food establishment or restaurant in accordance with paragraph (k)(1) of this section, the retail food establishment or restaurant that makes the purchase must maintain a record ( e.g., a sales receipt) documenting the name of the product purchased, the date of purchase, and the name and address of the place of purchase. (l) Partial exemption for farm to school and farm to institution programs. (1) Except as specified in paragraph (l)(2) of this section, this subpart does not apply to an institution operating a child nutrition program authorized under the Richard B. Russell National School Lunch Act or Section 4 of the Child Nutrition Act of 1966, or any other entity conducting a farm to school or farm to institution program, with respect to a food that is produced on a farm (including food produced and packaged on the farm) and sold or donated to the school or institution. (2) When a school or institution conducting a farm to school or farm to institution program obtains a food from a farm in accordance with paragraph (l)(1) of this section, the school food authority or relevant food procurement entity must maintain a record documenting the name and address of the farm that was the source of the food. The school food authority or relevant food procurement entity must maintain such record for 180 days. (m) Partial exemption for owners, operators, or agents in charge of fishing vessels. (1) Except as specified in paragraph (m)(2) of this section, with respect to a food that is obtained from a fishing vessel, this subpart does not apply to the owner, operator, or agent in charge of the fishing vessel, and this subpart also does not apply to persons who manufacture, process, pack, or hold the food until such time as the food is sold by the owner, operator, or agent in charge of the fishing vessel. (2) With respect to any person who receives the partial exemption set forth in paragraph (m)(1) of this section, if such person is required to register with FDA under section 415 of the Federal Food, Drug, and Cosmetic Act with respect to the manufacturing, processing, packing, or holding of the applicable food, such person must maintain records identifying the immediate previous source of such food and the immediate subsequent recipient of such food in accordance with \u00a7\u00a7 1.337 and 1.345. Such records must be maintained for 2 years. (n) Exemption for transporters. This subpart does not apply to transporters of food. (o) Exemption for nonprofit food establishments. This subpart does not apply to nonprofit food establishments. (p) Exemption for persons who manufacture, process, pack, or hold food for personal consumption. This subpart does not apply to persons who manufacture, process, pack, or hold food for personal consumption. (q) Exemption for certain persons who hold food on behalf of individual consumers. This subpart does not apply to persons who hold food on behalf of specific individual consumers, provided that these persons: (1) Are not parties to the transaction involving the food they hold; and (2) Are not in the business of distributing food. (r) Exemption for food for research or evaluation. This subpart does not apply to food for research or evaluation use, provided that such food: (1) Is not intended for retail sale and is not sold or distributed to the public; and (2) Is accompanied by the statement \u201cFood for research or evaluation use.\u201d [87 FR 71077, Nov. 21, 2022, as amended at 88 FR 65815, Sept. 26, 2023]"
  }
]

Return a JSON array of records. No Markdown. No commentary.