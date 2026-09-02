from __future__ import annotations

from pathlib import Path
import unittest

from bookforge import __version__


ROOT = Path(__file__).resolve().parents[1]


class ReleasePreparationTests(unittest.TestCase):
    def test_release_version_is_consistent(self) -> None:
        self.assertEqual(__version__, "1.0.0")
        for name in ("README.md", "CHANGELOG.md", "RELEASE_NOTES_1.0.0.md"):
            self.assertIn("1.0.0", (ROOT / name).read_text(encoding="utf-8"), name)
        spec = (ROOT / "BookForge.spec").read_text(encoding="utf-8")
        self.assertIn('"bookforge" / "__init__.py"', spec)
        self.assertIn('GetEnv("BOOKFORGE_VERSION")', (ROOT / "installer" / "BookForge.iss").read_text(encoding="utf-8"))

    def test_license_and_third_party_notices_are_present(self) -> None:
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertTrue(license_text.startswith("MIT License"))
        self.assertIn("Copyright (c) 2026 Christian Rieb", license_text)
        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        for required in ("Python", "PySide6", "Qt", "Calibre", "GPL"):
            self.assertIn(required, notices)
        self.assertIn("not bundled or redistributed", notices)

    def test_installer_is_per_user_and_does_not_bundle_calibre(self) -> None:
        script = (ROOT / "installer" / "BookForge.iss").read_text(encoding="utf-8")
        self.assertIn("PrivilegesRequired=lowest", script)
        self.assertIn("{localappdata}", script)
        self.assertIn("LicenseFile=..\\LICENSE", script)
        self.assertNotIn("ebook-convert", script)
        self.assertNotIn("ebook-meta", script)


if __name__ == "__main__":
    unittest.main()
