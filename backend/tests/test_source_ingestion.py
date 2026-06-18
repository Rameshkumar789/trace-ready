import unittest

from traceready_backend.extractors.html_extractor import extract_html_sections
from traceready_backend.versioning.hashing import sha256_text
from traceready_backend.versioning.source_versioning import next_source_version


class SourceIngestionTest(unittest.TestCase):
    def test_extracts_sections_and_hashes_source_versions(self):
        html = "<h2>21 CFR 1.1340 Shipping</h2><p>Shipping records must maintain TLC and recipient KDEs.</p>"
        sections = extract_html_sections(html)
        self.assertEqual(sections[0]["section"], "21 CFR 1.1340")
        self.assertEqual(sha256_text("abc"), sha256_text("abc"))
        version = next_source_version("src-test", [], "raw", "normalized")
        self.assertEqual(version.version, 1)


if __name__ == "__main__":
    unittest.main()
