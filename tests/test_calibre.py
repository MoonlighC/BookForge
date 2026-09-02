from __future__ import annotations

from pathlib import Path
import sys
from threading import Event, Thread
import time
import unittest

from bookforge.core.calibre import (
    BoundedLog,
    CalibreAdapter,
    CalibreCancelledError,
    parse_calibre_progress,
)


class PythonChildAdapter(CalibreAdapter):
    def __init__(self, script: str) -> None:
        super().__init__(Path(sys.executable))
        self._script = script

    def build_command(self, input_path: Path, output_path: Path) -> list[str]:
        return [sys.executable, "-u", "-c", self._script]


class CalibreProcessTests(unittest.TestCase):
    def test_progress_parser_accepts_only_valid_percentages(self) -> None:
        self.assertEqual(parse_calibre_progress("Converting input 42%\n"), 42)
        self.assertEqual(parse_calibre_progress("0% then 100%"), 100)
        self.assertIsNone(parse_calibre_progress("progress unavailable"))
        self.assertIsNone(parse_calibre_progress("999% malformed"))
        self.assertIsNone(parse_calibre_progress("-1% malformed"))

    def test_bounded_log_keeps_recent_output(self) -> None:
        log = BoundedLog(max_chars=80)
        log.append("old\n" * 30)
        log.append("final diagnostic\n")
        self.assertLessEqual(len(log.text), 80)
        self.assertIn("truncated", log.text)
        self.assertTrue(log.text.endswith("final diagnostic\n"))

    def test_streams_and_captures_child_output(self) -> None:
        adapter = PythonChildAdapter("print('25% working'); print('finished')")
        chunks: list[str] = []
        result = adapter.run(Path("input.txt"), Path("output.epub"), on_output=chunks.append)
        self.assertIn("25% working", result.output)
        self.assertIn("finished", "".join(chunks))

    def test_cancels_child_before_natural_completion(self) -> None:
        adapter = PythonChildAdapter(
            "import time; print('started', flush=True); time.sleep(10)"
        )
        cancel_event = Event()

        def cancel_soon() -> None:
            time.sleep(0.2)
            cancel_event.set()

        canceller = Thread(target=cancel_soon)
        canceller.start()
        started_at = time.monotonic()
        with self.assertRaises(CalibreCancelledError) as raised:
            adapter.run(
                Path("input.txt"),
                Path("output.epub"),
                cancel_event=cancel_event,
            )
        canceller.join()
        self.assertLess(time.monotonic() - started_at, 4.0)
        self.assertIn("started", raised.exception.output)


if __name__ == "__main__":
    unittest.main()
