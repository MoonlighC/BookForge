from __future__ import annotations

from pathlib import Path
import tempfile
from threading import Event
import unittest

from bookforge.core.calibre import (
    CalibreCancelledError,
    CalibreProcessError,
    CalibreRunResult,
)
from bookforge.core.converter import (
    ConversionCancelled,
    ConversionError,
    ConverterService,
)
from bookforge.core.metadata import BookMetadata, MetadataOverrides


class WritingCalibreAdapter:
    is_available = True
    executable = Path(__file__)

    def __init__(self) -> None:
        self.arguments: tuple[str, ...] = ()

    def run(
        self,
        input_path: Path,
        output_path: Path,
        *,
        cancel_event=None,
        on_output=None,
        arguments=(),
    ) -> CalibreRunResult:
        self.arguments = tuple(arguments)
        if on_output is not None:
            on_output("50% writing\n")
        output_path.write_bytes(input_path.read_bytes())
        return CalibreRunResult(("ebook-convert",), "50% writing\ndone")


class CancellingCalibreAdapter(WritingCalibreAdapter):
    def run(self, input_path: Path, output_path: Path, **kwargs) -> CalibreRunResult:
        output_path.write_bytes(b"partial")
        raise CalibreCancelledError("cancelled", output="partial log")


class FailingCalibreAdapter(WritingCalibreAdapter):
    def run(self, input_path: Path, output_path: Path, **kwargs) -> CalibreRunResult:
        output_path.write_bytes(b"partial")
        raise CalibreProcessError("failed", output="conversion failed")


class ConverterServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = WritingCalibreAdapter()
        self.converter = ConverterService(self.adapter)  # type: ignore[arg-type]

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

    def test_failed_conversion_does_not_publish_partial_output(self) -> None:
        converter = ConverterService(FailingCalibreAdapter())  # type: ignore[arg-type]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "Book.txt"
            source.write_text("original", encoding="utf-8")
            with self.assertRaises(ConversionError):
                converter.convert(source, root, "epub")
            self.assertEqual(source.read_text(encoding="utf-8"), "original")
            self.assertFalse((root / "Book.epub").exists())
            self.assertFalse(list(root.glob("*.bookforge-*")))

    def test_metadata_arguments_are_passed_without_modifying_source(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "Исходник.txt"
            original_bytes = "Исходный текст".encode("utf-8")
            source.write_bytes(original_bytes)
            cover = root / "cover.png"
            cover.write_bytes(b"cover")
            original = BookMetadata(title="Old", authors=("Old Author",))
            edited = BookMetadata(
                title="Книга",
                authors=("Анна", "Борис"),
                language="ru",
                publisher="Издатель",
                series="Серия",
                series_index=2.5,
                tags=("тест", "классика"),
                cover_path=cover,
            )
            overrides = MetadataOverrides.between(original, edited)

            self.converter.convert(
                source, root, "epub", metadata_overrides=overrides
            )

            self.assertEqual(source.read_bytes(), original_bytes)
            self.assertEqual(
                self.adapter.arguments,
                (
                    "--title=Книга",
                    "--language=ru",
                    "--publisher=Издатель",
                    "--series=Серия",
                    "--authors=Анна & Борис",
                    "--series-index=2.5",
                    "--tags=тест,классика",
                    f"--cover={cover}",
                ),
            )


if __name__ == "__main__":
    unittest.main()
