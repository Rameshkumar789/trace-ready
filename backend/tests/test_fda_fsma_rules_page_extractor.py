import unittest

from bellwether_backend.extractors.fda_fsma_rules_page_extractor import (
    extract_fsma_rules_guidance_entries,
    extract_fsma_rules_guidance_sections,
)


class FdaFsmaRulesPageExtractorTest(unittest.TestCase):
    def test_extracts_rule_and_guidance_rows(self):
        html = """
        <h2>Rules</h2>
        <table><tbody>
          <tr><td>Final Rule: <a href="/traceability">Requirements for Additional Traceability Records for Certain Foods</a><br>Docket Number: <a href="https://www.regulations.gov/search?filter=FDA-2014-N-0053">FDA-2014-N-0053</a></td><td>2022/11</td></tr>
        </tbody></table>
        <h2>Guidance for Industry &amp; Others</h2>
        <table><tbody>
          <tr><td>Draft Guidance for Industry: <a href="/qa">Questions and Answers About Requirements for Additional Traceability Records for Certain Foods</a><br>Docket Number: <a href="https://example.test/FDA-2025-D-2837">FDA-2025-D-2837</a></td><td>2026/02</td></tr>
        </tbody></table>
        """
        entries = extract_fsma_rules_guidance_entries(html)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["category"], "Rules")
        self.assertEqual(entries[0]["docket"], "FDA-2014-N-0053")
        self.assertEqual(entries[0]["primary_url"], "https://www.fda.gov/traceability")
        self.assertEqual(entries[1]["category"], "Guidance for Industry & Others")
        sections = extract_fsma_rules_guidance_sections(html)
        self.assertEqual(sections[0]["section"], "FDA-2014-N-0053")


if __name__ == "__main__":
    unittest.main()
