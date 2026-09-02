# BookForge 1.0.0

BookForge 1.0.0 is the first stable Windows release of the local desktop e-book converter.

## Highlights

- Drag-and-drop and multi-file batch conversion.
- Independent output format and metadata choices for each queued book.
- Cancellation, progress, conversion logs, retry, and safe overwrite policies.
- Metadata and cover editing that affects only converted output files.
- Persistent preferences and a polished native Windows interface.

## Supported formats

Input and output: EPUB, AZW3, MOBI, FB2, DOCX, TXT, and PDF.

Conversion quality depends on the source material and Calibre. PDF input is often less predictable because it is fixed-layout.

## Languages and themes

- Languages: English, German, and Russian.
- Themes: System, Light, and Dark.

Both are available under **Edit → Preferences**.

## Installation

- Installer: run `BookForge-Setup-1.0.0.exe` and follow the prompts.
- Portable: extract `BookForge-1.0.0-Windows-x64.zip`, then run `BookForge.exe`.

The first release is unsigned, so Windows SmartScreen may show a warning. Verify the SHA-256 checksums supplied with the release before running downloaded artifacts.

## Calibre requirement

Calibre must be installed separately. BookForge does not bundle Calibre. When available, BookForge invokes Calibre's `ebook-convert` and `ebook-meta` tools locally. If Calibre is missing, BookForge still opens and displays an explanatory warning, but conversion is unavailable.

## Privacy

BookForge has no accounts, analytics, telemetry, cloud upload, or network conversion service. Books are processed locally through the user's installed copy of Calibre.

## Known limitations

- DRM-protected books are unsupported; BookForge does not bypass or remove DRM.
- The queue is kept only for the current session.
- Percentage progress depends on output provided by Calibre.
- Advanced Calibre conversion options are intentionally not exposed.
- Calibre must be installed separately.
- Release binaries are not code-signed.
