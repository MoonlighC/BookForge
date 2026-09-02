from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bookforge.core.calibre import CalibreRunResult
from bookforge.core.converter import ConversionError, ConverterService


class WritingCalibreAdapter:
    is_available = True
    executable = Path(__file__)

    def run(self, input_path: Path, output_path: Path) -> CalibreRunResult:
        output_path.write_bytes(input_path.read_bytes())
        return CalibreRunResult(("ebook-convert",), "done")


class ConverterServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.converter = ConverterService(WritingCalibreAdapter())  # type: ignore[arg-type]

    def test_same_format_uses_converted_suffix(self) -> None:
        source = Path("Dune.epub")
        output = self.converter.output_path_for(source, Path("outputs"), "epub")
        self.assertEqual(output, Path("outputs") / "Dune_converted.epub")

    def test_existing_output_requires_explicit_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "Книга с пробелами.epub"
            source.write_bytes("hello".encode("utf-8"))
            output = root / "Книга с пробелами.pdf"
            output.write_bytes(b"old")

            with self.assertRaisesRegex(ConversionError, "already exists"):
                self.converter.convert(source, root, "pdf")

            result = self.converter.convert(source, root, "pdf", overwrite=True)
            self.assertEqual(result.output_path, output)
            self.assertEqual(output.read_bytes(), source.read_bytes())


if __name__ == "__main__":
    unittest.main()
