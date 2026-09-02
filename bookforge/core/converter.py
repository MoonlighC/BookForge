"""High-level validation and conversion workflow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
from threading import Event
from uuid import uuid4

from bookforge.core.calibre import (
    CalibreAdapter,
    CalibreCancelledError,
    CalibreNotFoundError,
    CalibreProcessError,
)


@dataclass(frozen=True, slots=True)
class BookFormat:
    extension: str
    label: str
    description: str
    input_order: int
    output_order: int


BOOK_FORMATS = (
    BookFormat("azw3", "AZW3", "Recommended for Kindle", 1, 0),
    BookFormat("epub", "EPUB", "Widely supported e-book format", 0, 1),
    BookFormat("mobi", "MOBI", "Legacy Kindle-compatible format", 2, 2),
    BookFormat("pdf", "PDF", "Fixed-layout document", 6, 3),
    BookFormat("fb2", "FB2", "FictionBook format", 3, 4),
    BookFormat("docx", "DOCX", "Microsoft Word document", 4, 5),
    BookFormat("txt", "TXT", "Plain text", 5, 6),
)
INPUT_FORMATS = tuple(sorted(BOOK_FORMATS, key=lambda item: item.input_order))
OUTPUT_FORMATS = tuple(sorted(BOOK_FORMATS, key=lambda item: item.output_order))
SUPPORTED_INPUT_SUFFIXES = frozenset(
    f".{item.extension}" for item in INPUT_FORMATS
)
SUPPORTED_OUTPUT_FORMATS = tuple(item.extension for item in OUTPUT_FORMATS)
_FORMATS_BY_EXTENSION = {item.extension: item for item in BOOK_FORMATS}


class ConversionError(RuntimeError):
    """A user-facing conversion or validation error."""

    def __init__(self, message: str, *, log: str = "") -> None:
        super().__init__(message)
        self.log = log


class ConversionCancelled(ConversionError):
    """Raised when the active conversion was cancelled by the user."""


@dataclass(frozen=True, slots=True)
class ConversionResult:
    output_path: Path
    log: str


class ConverterService:
    """Validate a request and coordinate conversion through Calibre."""

    def __init__(self, calibre: CalibreAdapter | None = None) -> None:
        self._calibre = calibre or CalibreAdapter()

    @property
    def calibre_available(self) -> bool:
        return self._calibre.is_available

    @property
    def calibre_executable(self) -> Path | None:
        return self._calibre.executable

    def output_path_for(
        self, input_path: Path, output_folder: Path, output_format: str
    ) -> Path:
        format_spec = get_output_format(output_format)
        output_stem = input_path.stem
        if input_path.suffix.lower() == f".{format_spec.extension}":
            output_stem = f"{output_stem}_converted"
        output_path = output_folder / f"{output_stem}.{format_spec.extension}"

        if _paths_are_same(input_path, output_path):
            raise ConversionError("Input and output paths cannot be identical.")

        return output_path

    def preflight(
        self, input_path: Path, output_folder: Path, output_format: str
    ) -> Path:
        """Validate one request without starting Calibre."""
        source = input_path.expanduser().resolve()
        destination_folder = output_folder.expanduser().resolve()
        self._validate_source(source)
        self._validate_destination_folder(destination_folder)
        output_path = self.output_path_for(source, destination_folder, output_format)
        if _paths_are_same(source, output_path):
            raise ConversionError("Input and output paths cannot be identical.")
        return output_path

    def convert(
        self,
        input_path: Path,
        output_folder: Path,
        output_format: str = "azw3",
        *,
        overwrite: bool = False,
        cancel_event: Event | None = None,
        on_output: Callable[[str], None] | None = None,
    ) -> ConversionResult:
        source = input_path.expanduser().resolve()
        destination_folder = output_folder.expanduser().resolve()
        output_path = self.preflight(source, destination_folder, output_format)
        if output_path.exists() and not overwrite:
            raise ConversionError(
                "The output file already exists and was not replaced."
            )

        temporary_path = destination_folder / (
            f".{output_path.stem}.bookforge-{uuid4().hex}{output_path.suffix}"
        )

        try:
            result = self._calibre.run(
                source,
                temporary_path,
                cancel_event=cancel_event,
                on_output=on_output,
            )
        except CalibreNotFoundError as exc:
            raise ConversionError(
                "Calibre was not found. Install Calibre before converting books."
            ) from exc
        except CalibreCancelledError as exc:
            _remove_partial_output(temporary_path)
            raise ConversionCancelled("Conversion cancelled.", log=exc.output) from exc
        except CalibreProcessError as exc:
            _remove_partial_output(temporary_path)
            detail = _last_useful_line(exc.output)
            message = "Calibre could not convert this book."
            if detail:
                message = f"{message} {detail}"
            raise ConversionError(message, log=exc.output) from exc
        except Exception:
            _remove_partial_output(temporary_path)
            raise

        if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
            _remove_partial_output(temporary_path)
            raise ConversionError(
                "Calibre finished, but the output file was not created.",
                log=result.output,
            )

        if output_path.exists() and not overwrite:
            _remove_partial_output(temporary_path)
            raise ConversionError(
                "The output file appeared during conversion and was not replaced.",
                log=result.output,
            )

        try:
            os.replace(temporary_path, output_path)
        except OSError as exc:
            _remove_partial_output(temporary_path)
            raise ConversionError(
                "The converted file could not be saved in the output folder.",
                log=result.output,
            ) from exc

        return ConversionResult(output_path=output_path, log=result.output)

    @staticmethod
    def _validate_source(input_path: Path) -> None:
        if not input_path.exists():
            raise ConversionError("The selected file no longer exists.")
        if not input_path.is_file():
            raise ConversionError("The selected path is not a file.")
        get_input_format(input_path.suffix)

    @staticmethod
    def _validate_destination_folder(output_folder: Path) -> None:
        if not output_folder.exists():
            raise ConversionError("The selected output folder does not exist.")
        if not output_folder.is_dir():
            raise ConversionError("The selected output path is not a folder.")
        if not os.access(output_folder, os.W_OK):
            raise ConversionError("The selected output folder is not writable.")


def _last_useful_line(output: str) -> str:
    """Return a short process detail suitable for a GUI error message."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return ""
    return lines[-1][:300]


def _remove_partial_output(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def get_input_format(input_format: str) -> BookFormat:
    """Return a validated input format definition."""
    normalized_format = _normalize_format(input_format, "input")
    try:
        return _FORMATS_BY_EXTENSION[normalized_format]
    except KeyError as exc:
        raise ConversionError(
            f"Unsupported input format: {input_format or 'unknown'}."
        ) from exc


def get_output_format(output_format: str) -> BookFormat:
    """Return a validated output format definition."""
    normalized_format = _normalize_format(output_format, "output")
    try:
        return _FORMATS_BY_EXTENSION[normalized_format]
    except KeyError as exc:
        raise ConversionError(
            f"Output format {output_format!r} is not supported."
        ) from exc


def _normalize_format(value: str, format_role: str) -> str:
    if not isinstance(value, str):
        raise ConversionError(f"The selected {format_role} format is not supported.")
    return value.strip().lower().removeprefix(".")


def _paths_are_same(first: Path, second: Path) -> bool:
    """Compare paths safely, including existing hard links on Windows."""
    try:
        return first.samefile(second)
    except OSError:
        first_key = os.path.normcase(str(first.expanduser().resolve()))
        second_key = os.path.normcase(str(second.expanduser().resolve()))
        return first_key == second_key
