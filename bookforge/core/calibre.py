"""Adapter for Calibre's ``ebook-convert`` command-line tool."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess


class CalibreError(RuntimeError):
    """Base error raised by the Calibre adapter."""


class CalibreNotFoundError(CalibreError):
    """Raised when ``ebook-convert`` cannot be located."""


class CalibreProcessError(CalibreError):
    """Raised when Calibre exits unsuccessfully."""

    def __init__(self, message: str, *, output: str = "") -> None:
        super().__init__(message)
        self.output = output


@dataclass(frozen=True, slots=True)
class CalibreRunResult:
    """Successful Calibre process result."""

    command: tuple[str, ...]
    output: str


def find_ebook_convert() -> Path | None:
    """Find ``ebook-convert`` in PATH or common Windows install locations."""
    located = shutil.which("ebook-convert") or shutil.which("ebook-convert.exe")
    if located:
        return Path(located).resolve()

    candidate_roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("LOCALAPPDATA"),
    ]
    candidates: list[Path] = []
    for root in candidate_roots:
        if not root:
            continue
        base = Path(root)
        candidates.extend(
            (
                base / "Calibre2" / "ebook-convert.exe",
                base / "Programs" / "calibre" / "ebook-convert.exe",
            )
        )

    return next((path.resolve() for path in candidates if path.is_file()), None)


class CalibreAdapter:
    """Locate and invoke Calibre without involving shell command parsing."""

    def __init__(self, executable: Path | None = None) -> None:
        self._executable = executable or find_ebook_convert()

    @property
    def executable(self) -> Path | None:
        return self._executable

    @property
    def is_available(self) -> bool:
        return self._executable is not None and self._executable.is_file()

    def build_command(self, input_path: Path, output_path: Path) -> list[str]:
        if not self.is_available:
            raise CalibreNotFoundError(
                "Calibre was not found. Install Calibre before converting books."
            )
        assert self._executable is not None
        return [str(self._executable), str(input_path), str(output_path)]

    def run(self, input_path: Path, output_path: Path) -> CalibreRunResult:
        command = self.build_command(input_path, output_path)
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        try:
            completed = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                creationflags=creation_flags,
            )
        except OSError as exc:
            raise CalibreProcessError(
                "Calibre could not be started. Check the installation and try again."
            ) from exc

        process_output = completed.stdout or ""
        if completed.returncode != 0:
            raise CalibreProcessError(
                f"Calibre stopped with exit code {completed.returncode}.",
                output=process_output,
            )

        return CalibreRunResult(tuple(command), process_output)
