"""Source-safe checks for Conks page segmentation before private recovery."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.prepare_conks_offline_evidence import run_output_dir, split_pages


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

    def test_run_id_rejects_traversal_and_absolute_paths_before_output_creation(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp) / "private"
            for value in ("../outside", "/tmp/absolute-run", "nested/run", ".."):
                with self.subTest(value=value):
                    with self.assertRaisesRegex(ValueError, "safe path component"):
                        run_output_dir(root, value)
                    self.assertFalse(root.exists())
            safe = run_output_dir(root, "conks-md-substrate-002")
            self.assertEqual(safe, root / "runs/conks-md-substrate-002")
            self.assertFalse(safe.exists())


if __name__ == "__main__":
    unittest.main()
