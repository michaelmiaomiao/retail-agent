import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from report_utils import render_wsl_report
from wsl_utils import build_records, diff_records, parse_wsl_html


class WslPipelineTests(unittest.TestCase):
    def test_parse_wsl_html_dedupes_and_normalizes_urls(self) -> None:
        html = (ROOT / "tests/fixtures/wsl_listing.html").read_text(encoding="utf-8")

        items = parse_wsl_html(html)

        self.assertEqual(len(items), 2)
        self.assertEqual(
            items[0]["url"],
            "https://www.costco.com/p/-/charmin-ultra-soft-bath-tissue-2-ply-213-sheets-30-rolls/4000404576",
        )
        self.assertEqual(
            items[1]["url"],
            "https://www.costco.com/p/-/kirkland-signature-paper-towels-2-ply-160-sheets-12-individually-wrapped-rolls/100234271",
        )

    def test_diff_logic_is_resilient_to_minor_title_changes(self) -> None:
        previous = build_records(
            [
                {
                    "title_en": "Kirkland Signature Paper Towels, 2-Ply, 160 Sheets, 12 Individually Wrapped Rolls | Costco",
                    "url": "https://www.costco.com/p/-/kirkland-signature-paper-towels-2-ply-160-sheets-12-individually-wrapped-rolls/100234271?langId=-1",
                }
            ]
        )
        current = build_records(
            [
                {
                    "title_en": "Kirkland Signature Paper Towels 2 Ply 160 Sheets 12 Individually Wrapped Rolls",
                    "url": "https://www.costco.com/p/-/kirkland-signature-paper-towels-2-ply-160-sheets-12-individually-wrapped-rolls/100234271",
                }
            ]
        )

        diff = diff_records(current, previous)

        self.assertEqual(diff["counts"]["new"], 0)
        self.assertEqual(diff["counts"]["removed"], 0)
        self.assertEqual(diff["counts"]["still_active"], 1)

    def test_render_wsl_report_smoke(self) -> None:
        current = build_records(
            [
                {
                    "title_en": "Charmin Ultra Soft Bath Tissue, 2-Ply, 213 Sheets, 30 Rolls",
                    "url": "https://www.costco.com/p/-/charmin-ultra-soft-bath-tissue-2-ply-213-sheets-30-rolls/4000404576",
                }
            ]
        )
        previous = []
        diff_payload = {
            "fetch_error": "",
            "comparison": diff_records(current, previous),
        }

        report = render_wsl_report(diff_payload, today="2026-03-08")

        self.assertIn("# Costco While Supplies Last Weekly Snapshot (2026-03-08)", report)
        self.assertIn("## New this week", report)
        self.assertIn("Charmin Ultra Soft Bath Tissue", report)
        self.assertIn("## Still active", report)


if __name__ == "__main__":
    unittest.main()
