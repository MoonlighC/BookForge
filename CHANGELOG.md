# Changelog

All notable BookForge releases are documented in this file.

## [1.0.0] - 2026-09-03

### Added

- Multi-format conversion for EPUB, AZW3, MOBI, FB2, DOCX, TXT, and PDF.
- Sequential batch queue with independent output formats for each book.
- Cancellation, progress reporting, bounded logs, retry actions, and existing-file policies.
- Metadata editing and validated cover replacement for converted outputs.
- English, German, and Russian interface localization.
- Persistent System, Light, and Dark themes and application preferences.
- Standalone Windows x64 portable distribution and per-user Windows installer.

### Safety

- Source books remain read-only conversion inputs.
- Same-format conversions use a `_converted` filename.
- Outputs are published transactionally so failed or cancelled work does not appear complete.

### Packaging

- Added Windows executable version metadata, MIT licensing, third-party notices, and canonical Inno Setup configuration.
