"""P3 — inbound trading-partner format normalizers (EDI 856, EPCIS, GDSN)."""

from pathlib import Path

from bellwether_backend.audit_engine.customer_evidence import read_spreadsheet_evidence
from bellwether_backend.audit_engine.inbound_parsers import (
    parse_edi_856,
    parse_epcis_xml,
    parse_gdsn_xml,
)

EDI_856 = (
    "ISA*00*~GS*SH*~ST*856*0001~"
    "BSN*00*SHIP123*20260310*1200~"
    "HL*1**S~N1*SF*SUNRISE FARMS*92*SUP-A~N1*ST*ACME DC*92*DC-1~"
    "HL*2*1*O~"
    "HL*3*2*I~LIN**UP*00012345678905~SN1**240*CA~REF*LT*LOT-8841~"
    "HL*4*2*I~LIN**UP*00098765432109~SN1**120*CA~REF*LT*LOT-9007~"
)

EPCIS_XML = """<?xml version="1.0"?>
<epcis:EPCISDocument xmlns:epcis="urn:epcglobal:epcis:xsd:1">
  <EPCISBody><EventList>
    <ObjectEvent>
      <eventTime>2026-03-05T10:00:00Z</eventTime>
      <bizStep>urn:epcglobal:cbv:bizstep:shipping</bizStep>
      <epcList><epc>urn:epc:id:sgtin:0614141.107346.LOT-8841</epc></epcList>
      <bizLocation><id>urn:epc:id:sgln:0614141.00777.0</id></bizLocation>
    </ObjectEvent>
    <TransformationEvent>
      <eventTime>2026-03-06T08:00:00Z</eventTime>
      <inputEPCList><epc>LOT-8841</epc></inputEPCList>
      <outputEPCList><epc>LOT-NEW-1</epc></outputEPCList>
    </TransformationEvent>
  </EventList></EPCISBody>
</epcis:EPCISDocument>
"""

GDSN_XML = """<?xml version="1.0"?>
<catalogue><tradeItem><gtin>00012345678905</gtin>
<descriptionShort>Romaine Hearts 3ct</descriptionShort></tradeItem></catalogue>
"""


def test_edi_856_extracts_line_items():
    rows = parse_edi_856(EDI_856)
    assert len(rows) == 2
    assert rows[0]["product_id"] == "00012345678905"
    assert rows[0]["traceability_lot_code"] == "LOT-8841"
    assert rows[0]["event_datetime"] == "2026-03-10"
    assert rows[0]["from_partner_id"] == "SUP-A" and rows[0]["to_partner_id"] == "DC-1"
    assert rows[0]["event_type"] == "shipping"
    assert rows[1]["traceability_lot_code"] == "LOT-9007"


def test_epcis_object_and_transformation_events():
    rows = parse_epcis_xml(EPCIS_XML)
    assert len(rows) == 2
    obj = rows[0]
    assert obj["event_type"] == "shipping" and "LOT-8841" in obj["traceability_lot_code"]
    xform = rows[1]
    assert xform["event_type"] == "transformation"
    assert xform["source_lot_or_tlc"] == "LOT-8841" and xform["output_lot_or_tlc"] == "LOT-NEW-1"


def test_gdsn_product_master():
    rows = parse_gdsn_xml(GDSN_XML)
    assert len(rows) == 1
    assert rows[0]["product_id"] == "00012345678905"
    assert rows[0]["product_name"] == "Romaine Hearts 3ct"


def test_read_spreadsheet_evidence_dispatches_edi_and_xml(tmp_path: Path):
    edi_file = tmp_path / "asn.edi"
    edi_file.write_text(EDI_856, encoding="utf-8")
    edi_records = read_spreadsheet_evidence(edi_file)
    assert edi_records and any(r.normalized_value == "LOT-8841" for r in edi_records)

    xml_file = tmp_path / "events.xml"
    xml_file.write_text(EPCIS_XML, encoding="utf-8")
    epcis_records = read_spreadsheet_evidence(xml_file)
    assert epcis_records and all(r.sheet_name == "epcis" for r in epcis_records)
