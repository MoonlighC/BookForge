"""Adapter for Calibre's ``ebook-convert`` command-line tool."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
from queue import Empty, Queue
import re
import shutil
import subprocess
from threading import Event, Thread


MAX_CALIBRE_LOG_CHARS = 64_000
_TRUNCATION_MARKER = "[Earlier Calibre output was truncated.]\n"
_PROGRESS_PATTERN = re.compile(r"(?<![\d.+-])(100|[1-9]?\d)\s*%(?![\d.])")


class CalibreError(RuntimeError):
    """Base error raised by the Calibre adapter."""


class CalibreNotFoundError(CalibreError):
    """Raised when ``ebook-convert`` cannot be located."""


class CalibreProcessError(CalibreError):
    """Raised when Calibre exits unsuccessfully."""

    def __init__(self, message: str, *, output: str = "") -> None:
        super().__init__(message)
        self.output = output


class CalibreCancelledError(CalibreProcessError):
    """Raised when BookForge stops the active Calibre child process."""


@dataclass(frozen=True, slots=True)
class CalibreRunResult:
    """Successful Calibre process result."""

    command: tuple[str, ...]
    output: str


class BoundedLog:
    """Keep the most recent process output within a fixed character budget."""

    def __init__(self, max_chars: int = MAX_CALIBRE_LOG_CHARS) -> None:
        if max_chars <= len(_TRUNCATION_MARKER):
            raise ValueError("The log limit is too small.")
        self._max_chars = max_chars
        self._text = ""
        self._truncated = False

    @property
    def text(self) -> str:
        return self._text

    def append(self, text: str) -> str:
        if not text:
            return self._text
        combined = self._text + text
        if len(combined) <= self._max_chars and not self._truncated:
            self._text = combined
            return self._text

        keep = self._max_chars - len(_TRUNCATION_MARKER)
        if self._truncated and combined.startswith(_TRUNCATION_MARKER):
            combined = combined[len(_TRUNCATION_MARKER) :]
        self._text = _TRUNCATION_MARKER + combined[-keep:]
        self._truncated = True
        return self._text


def parse_calibre_progress(output_chunk: str) -> int | None:
    """Return the last valid percentage in a Calibre output chunk, if any."""
    matches = _PROGRESS_PATTERN.findall(output_chunk)
    return int(matches[-1]) if matches else None


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
    """Start and observe one cancellable Calibre child process at a time."""

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

    def run(
        self,
        input_path: Path,
        output_path: Path,
        *,
        cancel_event: Event | None = None,
        on_output: Callable[[str], None] | None = None,
    ) -> CalibreRunResult:
        command = self.build_command(input_path, output_path)
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                shell=False,
                creationflags=creation_flags,
            )
        except OSError as exc:
            raise CalibreProcessError(
                "Calibre could not be started. Check the installation and try again."
            ) from exc

        output_queue: Queue[str | None] = Queue()
        output_log = BoundedLog()
        reader = Thread(
            target=self._read_output,
            args=(process, output_queue),
            name="BookForge-Calibre-output",
            daemon=True,
        )
        reader.start()
        reader_finished = False
        cancellation_started = False

        while process.poll() is None or not reader_finished:
            if (
                cancel_event is not None
                and cancel_event.is_set()
                and process.poll() is None
                and not cancellation_started
            ):
                cancellation_started = True
                self._stop_process(process)

            try:
                chunk = output_queue.get(timeout=0.05)
            except Empty:
                continue
            if chunk is None:
                reader_finished = True
                continue
            output_log.append(chunk)
            if on_output is not None:
                try:
                    on_output(chunk)
                except Exception:
                    # A presentation callback must never destabilize process control.
                    pass

        reader.join(timeout=1.0)
        if process.stdout is not None:
            process.stdout.close()

        process_output = output_log.text
        if cancellation_started:
            raise CalibreCancelledError(
                "Calibre conversion was cancelled.", output=process_output
            )
        if process.returncode != 0:
            raise CalibreProcessError(
                f"Calibre stopped with exit code {process.returncode}.",
                output=process_output,
            )

        return CalibreRunResult(tuple(command), process_output)

    @staticmethod
    def _read_output(
        process: subprocess.Popen[str], output_queue: Queue[str | None]
    ) -> None:
        try:
            if process.stdout is not None:
                for line in process.stdout:
                    output_queue.put(line)
        finally:
            output_queue.put(None)

    @staticmethod
    def _stop_process(process: subprocess.Popen[str]) -> None:
        """Stop only BookForge's exact child, escalating after a short wait."""
        if process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=2.0)
            return
        except (OSError, subprocess.TimeoutExpired):
            pass

        if process.poll() is None:
            try:
                process.kill()
                process.wait(timeout=2.0)
            except (OSError, subprocess.TimeoutExpired):
                pass
