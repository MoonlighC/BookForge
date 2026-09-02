from __future__ import annotations

from pathlib import Path
import tempfile
from threading import Event
import unittest

from bookforge.core.calibre import CalibreCancelledError, CalibreRunResult
from bookforge.core.converter import (
    ConversionCancelled,
    ConversionError,
    ConverterService,
)


class WritingCalibreAdapter:
    is_available = True
    executable = Path(__file__)

    def run(
        self,
        input_path: Path,
        output_path: Path,
        *,
        cancel_event=None,
        on_output=None,
    ) -> CalibreRunResult:
        if on_output is not None:
            on_output("50% writing\n")
        output_path.write_bytes(input_path.read_bytes())
        return CalibreRunResult(("ebook-convert",), "50% writing\ndone")


class CancellingCalibreAdapter(WritingCalibreAdapter):
    def run(self, input_path: Path, output_path: Path, **kwargs) -> CalibreRunResult:
        output_path.write_bytes(b"partial")
        raise CalibreCancelledError("cancelled", output="partial log")


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

    def test_cancelled_conversion_does_not_publish_partial_output(self) -> None:
        converter = ConverterService(CancellingCalibreAdapter())  # type: ignore[arg-type]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "Book.txt"
            source.write_text("original", encoding="utf-8")
            with self.assertRaises(ConversionCancelled) as raised:
                converter.convert(source, root, "epub", cancel_event=Event())
            self.assertEqual(raised.exception.log, "partial log")
            self.assertFalse((root / "Book.epub").exists())
            self.assertFalse(list(root.glob("*.bookforge-*")))


if __name__ == "__main__":
    unittest.main()
