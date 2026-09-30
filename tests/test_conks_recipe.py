"""Source-safe checks for Conks page segmentation before private recovery."""

import unittest

from scripts.prepare_conks_offline_evidence import split_pages


class ConksRecipeTest(unittest.TestCase):
    def test_expected_printed_pages_are_split_without_dropping_text(self) -> None:
        text = "private front matter\n" + "".join(
            f"<!-- page {page} -->\nPage {page}\nA source sentence on {page}.\n"
            for page in range(2, 21)
        )
        pages = split_pages(text)
        self.assertEqual(sorted(pages), list(range(2, 21)))
        self.assertIn("A source sentence on 8.", pages[8])
        self.assertNotIn("private front matter", pages[2])

    def test_missing_page_marker_fails_before_run(self) -> None:
        text = "".join(f"<!-- page {page} -->\nPage {page}\n"
                       for page in range(2, 21) if page != 8)
        with self.assertRaisesRegex(ValueError, "expected exactly"):
            split_pages(text)


if __name__ == "__main__":
    unittest.main()
