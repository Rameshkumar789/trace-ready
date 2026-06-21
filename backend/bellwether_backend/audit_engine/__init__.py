"""Bellwether audit engine — the per-customer RUNTIME subsystem.

This is the online path the API runs on every customer upload: parse the customer workbook
(customer_evidence), classify CTEs (cte_classification, field_mapping_governance), and execute
the approved rules (rule_execution). It only *consumes* the approved rule cards; it does not
build them. The offline knowledge-extraction pipeline lives in `intelligence/`.
"""
