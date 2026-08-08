from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


DATA_PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_PIPELINE_DIR.parent
sys.path.insert(0, str(DATA_PIPELINE_DIR))

from src.publication_transaction import promote_files_atomically  # noqa: E402


class PublicationTransactionTest(unittest.TestCase):
    def test_promove_lote_validado(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            root = Path(directory)
            stage = root / "stage"
            target = root / "target"
            (stage / "a").mkdir(parents=True)
            (stage / "a/one.json").write_text("novo-1", encoding="utf-8")
            (stage / "a/two.json").write_text("novo-2", encoding="utf-8")
            promote_files_atomically(
                stage,
                target,
                [Path("a/one.json"), Path("a/two.json")],
            )
            self.assertEqual((target / "a/one.json").read_text(), "novo-1")
            self.assertEqual((target / "a/two.json").read_text(), "novo-2")

    def test_falha_intermediaria_restabelece_todo_o_lote(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            root = Path(directory)
            stage = root / "stage"
            target = root / "target"
            (stage / "a").mkdir(parents=True)
            (target / "a").mkdir(parents=True)
            (stage / "a/one.json").write_text("novo-1", encoding="utf-8")
            (stage / "a/two.json").write_text("novo-2", encoding="utf-8")
            (target / "a/one.json").write_text("antigo-1", encoding="utf-8")
            (target / "a/two.json").write_text("antigo-2", encoding="utf-8")
            real_replace = os.replace

            def replace_with_failure(source, destination):
                source_path = Path(source)
                destination_path = Path(destination)
                if source_path == stage / "a/two.json" and destination_path == target / "a/two.json":
                    raise OSError("falha simulada na segunda promoção")
                return real_replace(source, destination)

            with patch("src.publication_transaction.os.replace", replace_with_failure):
                with self.assertRaisesRegex(OSError, "falha simulada"):
                    promote_files_atomically(
                        stage,
                        target,
                        [Path("a/one.json"), Path("a/two.json")],
                    )
            self.assertEqual((target / "a/one.json").read_text(), "antigo-1")
            self.assertEqual((target / "a/two.json").read_text(), "antigo-2")


if __name__ == "__main__":
    unittest.main()
