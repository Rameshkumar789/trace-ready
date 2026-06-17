# AI-Assisted Obligation Extraction

Extract obligation drafts from authoritative FSMA 204 source chunks without approving compliance logic.

## Extraction focus

- covered subject
- triggering condition
- required action
- required object or records
- deadline or timing requirement when explicit
- exceptions or cross-references when explicit

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
    "obligation_id": {
      "minLength": 1,
      "title": "Obligation Id",
      "type": "string"
    },
    "subject": {
      "minLength": 1,
      "title": "Subject",
      "type": "string"
    },
    "condition": {
      "minLength": 1,
      "title": "Condition",
      "type": "string"
    },
    "action": {
      "minLength": 1,
      "title": "Action",
      "type": "string"
    },
    "object": {
      "minLength": 1,
      "title": "Object",
      "type": "string"
    },
    "required_output": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Required Output"
    },
    "deadline": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Deadline"
    },
    "exceptions": {
      "items": {
        "type": "string"
      },
      "title": "Exceptions",
      "type": "array"
    },
    "applies_to_ctes": {
      "items": {
        "$ref": "#/$defs/CteType"
      },
      "title": "Applies To Ctes",
      "type": "array"
    },
    "applies_to_food_scope": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Applies To Food Scope"
    },
    "noncompliance_risk": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Noncompliance Risk"
    }
  },
  "required": [
    "citations",
    "metadata",
    "obligation_id",
    "subject",
    "condition",
    "action",
    "object"
  ],
  "title": "Obligation",
  "type": "object"
}

## Source chunks

[
  {
    "source_id": "ecfr-21-cfr-1-subpart-s",
    "chunk_id": "ecfr-21-cfr-1-subpart-s-21-cfr-1-1300-1",
    "citation_anchor": "21 CFR 1.1300",
    "authority_rank": "codified_rule",
    "source_url": "https://www.ecfr.gov/api/versioner/v1/full/2026-06-11/title-21.xml?part=1",
    "section_ref": "21 CFR 1.1300",
    "page_number": null,
    "text": "Except as otherwise specified in this subpart, the requirements in this subpart apply to persons who manufacture, process, pack, or hold foods that appear on the list of foods for which additional traceability records are required in accordance with section 204(d)(2) of the FDA Food Safety Modernization Act (Food Traceability List). FDA will publish the Food Traceability List on its website, www.fda.gov., in accordance with section 204(d)(2)(B) of the FDA Food Safety Modernization Act."
  },
  {
    "source_id": "ecfr-21-cfr-1-subpart-s",
    "chunk_id": "ecfr-21-cfr-1-subpart-s-21-cfr-1-1325-6",
    "citation_anchor": "21 CFR 1.1325",
    "authority_rank": "codified_rule",
    "source_url": "https://www.ecfr.gov/api/versioner/v1/full/2026-06-11/title-21.xml?part=1",
    "section_ref": "21 CFR 1.1325",
    "page_number": null,
    "text": "(a) Harvesting. (1) For each raw agricultural commodity (not obtained from a fishing vessel) on the Food Traceability List that you harvest, you must maintain records containing the following information: (i) The location description for the immediate subsequent recipient (other than a transporter) of the food; (ii) The commodity and, if applicable, variety of the food; (iii) The quantity and unit of measure of the food ( e.g., 75 bins, 200 pounds); (iv) The location description for the farm where the food was harvested; (v) For produce, the name of the field or other growing area from which the food was harvested (which must correspond to the name used by the grower), or other information identifying the harvest location at least as precisely as the field or other growing area name; (vi) For aquacultured food, the name of the container ( e.g., pond, pool, tank, cage) from which the food was harvested (which must correspond to the container name used by the aquaculture farmer) or other information identifying the harvest location at least as precisely as the container name; (vii) The date of harvesting; and (viii) The reference document type and reference document number. (2) For each raw agricultural commodity (not obtained from a fishing vessel) on the Food Traceability List that you harvest, you must provide (in electronic, paper, or other written form) your business name, phone number, and the information in paragraphs (a)(1)(i) through (vii) of this section to the initial packer of the raw agricultural commodity you harvest, either directly or through the supply chain. (b) Cooling before initial packing. (1) For each raw agricultural commodity (not obtained from a fishing vessel) on the Food Traceability List that you cool before it is initially packed, you must maintain records containing the following information: (i) The location description for the immediate subsequent recipient (other than a transporter) of the food; (ii) The commodity and, if applicable, variety of the food; (iii) The quantity and unit of measure of the food ( e.g., 75 bins, 200 pounds); (iv) The location description for where you cooled the food; (v) The date of cooling; (vi) The location description for the farm where the food was harvested; and (vii) The reference document type and reference document number. (2) For each raw agricultural commodity (not obtained from a fishing vessel) on the Food Traceability List that you cool before it is initially packed, you must provide (in electronic, paper, or other written form) the information in paragraphs (b)(1)(i) through (vi) of this section to the initial packer of the raw agricultural commodity you cool, either directly or through the supply chain."
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
    "source_id": "ecfr-21-cfr-1-subpart-s",
    "chunk_id": "ecfr-21-cfr-1-subpart-s-21-cfr-1-1455-31",
    "citation_anchor": "21 CFR 1.1455",
    "authority_rank": "codified_rule",
    "source_url": "https://www.ecfr.gov/api/versioner/v1/full/2026-06-11/title-21.xml?part=1",
    "section_ref": "21 CFR 1.1455",
    "page_number": null,
    "text": "(a) General requirements for records. (1) You must keep records as original paper or electronic records or true copies (such as photocopies, pictures, scanned copies, or other accurate reproductions of the original records). Electronic records may include valid, working electronic links to the information required to be maintained under this subpart. (2) All records must be legible and stored to prevent deterioration or loss. (b) Establishment and maintenance of records by another entity. You may have another entity establish and maintain records required under this subpart on your behalf, but you are responsible for ensuring that such records can be retrieved and provided onsite within 24 hours of request for official review. (c) Record availability. (1) You must make all records required under this subpart available to an authorized FDA representative, upon request, within 24 hours (or within some reasonable time to which FDA has agreed) after the request, along with any information needed to understand these records, such as internal or external coding systems, glossaries, abbreviations, and a description of how the records you provide correspond to the information required under this subpart. (2) Offsite storage of records is permitted if such records can be retrieved and provided onsite within 24 hours of request for official review. Electronic records are considered to be onsite if they are accessible from an onsite location. (3) When necessary to help FDA prevent or mitigate a foodborne illness outbreak, or to assist in the implementation of a recall, or to otherwise address a threat to the public health, including but not limited to situations where FDA has a reasonable belief that an article of food (and any other article of food that FDA reasonably believes is likely to be affected in a similar manner) presents a threat of serious adverse health consequences or death to humans or animals as a result of the food being adulterated under section 402 of the Federal Food, Drug, and Cosmetic Act or misbranded under section 403(w) of the Federal Food, Drug, and Cosmetic Act, you must make available, within 24 hours (or within some reasonable time to which FDA has agreed) of a request made in-person or remotely ( e.g., by phone) by an authorized FDA representative, the information you are required to maintain under this subpart, for the foods and date ranges or traceability lot codes specified in the request. (i) If FDA's request for the information specified in paragraph (c)(3) of this section is made by phone, we will also provide the request to you in writing upon your request; however, you must provide the requested information within 24 hours (or within some reasonable time to which FDA has agreed) of the phone request. (ii) Except as specified in paragraph (c)(3)(iii) and (iv) of this section, when the information requested by FDA under paragraph (c)(3) of this section is information you are required to maintain under \u00a7\u00a7 1.1325 through 1.1350, you must provide such information in an electronic sortable spreadsheet, along with any other information needed to understand the information in the spreadsheet. (iii) You may provide the information requested by FDA under paragraph (c)(3) of this section in a form other than an electronic sortable spreadsheet if you are: (A) A farm whose average annual sum of the monetary value of their sales of raw agricultural commodities and the market value of raw agricultural commodities they manufacture, process, pack, or hold without sale ( e.g., held for a fee) during the previous 3-year period is no more than $250,000 (on a rolling basis), adjusted for inflation using 2020 as the baseline year for calculating the adjustment; (B) A retail food establishment or restaurant with an average annual monetary value of food sold or provided during the previous 3-year period of no more than $1 million (on a rolling basis), adjusted for inflation using 2020 as the baseline year for calculating the adjustment; or (C) A person (other than a farm, retail food establishment, or restaurant) whose average annual sum of the monetary value of their sales of food and the market value of food they manufacture, process, pack, or hold without sale ( e.g., held for a fee) during the previous 3-year period is no more than $1 million (on a rolling basis), adjusted for inflation using 2020 as the baseline year for calculating the adjustment. (iv) FDA will withdraw a request for an electronic sortable spreadsheet under paragraph (c)(3)(ii) of this section, as appropriate, to accommodate a religious belief of a person asked to provide such a spreadsheet. (4) Upon FDA request, you must provide within a reasonable time an English translation of records required under this subpart maintained in a language other than English. (d) Record retention. Except as specified otherwise in this subpart, you must maintain records containing the information required by this subpart for 2 years from the date you created or obtained the records. (e) Electronic records. Records that are established or maintained to satisfy the requirements of this subpart and that meet the definition of electronic records in \u00a7 11.3(b)(6) of this chapter are exempt from the requirements of part 11 of this chapter. Records that satisfy the requirements of this subpart, but that also are required under other applicable statutory provisions or regulations, remain subject to part 11 of this chapter, if not otherwise exempt. (f) Use of existing records. You do not need to duplicate existing records you have ( e.g., records that you keep in the ordinary course of business or that you maintain to comply with other Federal, State, Tribal, territorial, or local regulations) if they contain the information required by this subpart. You may supplement any such existing records as necessary to include all of the information required by this subpart. (g) Use of multiple sets of records. You do not have to keep all of the information required by this subpart in a single set of records. However, your traceability plan must indicate the format and location of the records you are required to keep under this subpart, in accordance with \u00a7 1.1315(a)(1). (h) Public disclosure. Records obtained by FDA in accordance with this subpart are subject to the disclosure requirements under part 20 of this chapter."
  }
]

Return a JSON array of records. No Markdown. No commentary.