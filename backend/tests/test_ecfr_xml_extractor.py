import unittest

from bellwether_backend.extractors.ecfr_xml_extractor import extract_ecfr_sections


class EcfrXmlExtractorTest(unittest.TestCase):
    def test_extracts_ecfr_sections_in_range(self):
        xml = """
        <DIV5>
          <DIV8 N="1.1200" TYPE="SECTION"><HEAD>§ 1.1200 Outside</HEAD><P>Outside text.</P></DIV8>
          <DIV8 N="1.1300" TYPE="SECTION"><HEAD>§ 1.1300 Who is subject?</HEAD><P>You must keep records.</P></DIV8>
          <DIV8 N="1.1465" TYPE="SECTION"><HEAD>§ 1.1465 Updating list</HEAD><P>FDA will update the list.</P></DIV8>
        </DIV5>
        """
        sections = extract_ecfr_sections(xml, min_section=1.1300, max_section=1.1465)
        self.assertEqual([section["section"] for section in sections], ["21 CFR 1.1300", "21 CFR 1.1465"])
        self.assertEqual(sections[0]["section_label"], "§ 1.1300 Who is subject?")


if __name__ == "__main__":
    unittest.main()
