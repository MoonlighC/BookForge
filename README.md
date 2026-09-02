# BookForge

## Overview

BookForge is a local desktop application for converting e-books and documents between common formats. It uses Calibre's `ebook-convert` command-line tool for conversion and `ebook-meta` for metadata and cover extraction.

The application is built with Python and PySide6 for Windows 10 and Windows 11. A one-folder Windows build runs without a separate Python installation; Calibre remains an external dependency.

## Features

- Add multiple EPUB, AZW3, MOBI, FB2, DOCX, TXT, and PDF files through a multi-select file dialog or drag and drop.
- Mix input formats in one in-memory conversion queue.
- Choose AZW3, EPUB, MOBI, PDF, FB2, DOCX, or TXT separately for every queued book.
- Apply one output format to the whole queue, then adjust individual rows as needed.
- Remember window geometry, a manually selected output folder, the global output format, and the existing-file policy between launches.
- Use a small native File/Help menu with Ctrl+O, Ctrl+Q, Ctrl+Enter, and an About dialog.
- Inspect and edit each book's title, authors, language, publisher, series, series index, and tags before conversion.
- Preview an extracted cover or choose a validated JPG, JPEG, or PNG replacement for the converted output.
- Keep metadata and cover edits per book, with a subtle **Metadata · Edited** indicator and Reset support.
- Load metadata asynchronously with at most two extraction tasks at once; extraction failures do not block conversion.
- Process the queue sequentially in one worker thread so the interface remains responsive and Calibre processes do not run concurrently.
- Use one shared output directory, initially set from the first queued book.
- Track Ready, Waiting, Converting, Completed, Failed, Cancelled, and Skipped states independently for every item.
- Cancel only the current conversion and continue with the next book, or cancel the current conversion and the rest of the batch.
- Display a real per-item percentage when Calibre emits a usable integer percentage; otherwise use an indeterminate progress indicator.
- Capture the most recent 64,000 characters of Calibre output and show it in an expandable, read-only Details panel.
- Retry individual Failed, Cancelled, or Skipped items, or reset all such items with **Retry failed**.
- Choose an existing-file policy: **Ask**, **Replace all**, or **Skip all**.
- Use a safe `_converted` filename whenever the input and output formats match.
- Convert through a temporary sibling file so failed and cancelled conversions are not published as completed results.
- Open a completed file or its containing folder directly from its queue row.
- Skip duplicate physical source paths already present in the queue.
- Handle missing files, unavailable folders, Calibre errors, and missing output files with concise messages.
- Switch the complete interface live between English, German, and Russian from **Edit → Preferences** without changing or clearing the queue.
- Use the system color scheme or choose a persistent light or dark theme with an application-wide palette and matching controls.

## Requirements

Running from source requires:

- Windows 10 or Windows 11
- Python 3.12 or later
- [Calibre](https://calibre-ebook.com/) installed separately, with `ebook-convert` and `ebook-meta` available
- PySide6 Essentials, installed from `requirements.txt`

The packaged application does not require Python. Calibre must still be installed separately for conversion and metadata extraction.

## Installation

Open PowerShell in the project directory and create a virtual environment:

```powershell
py -3.12 -m venv .venv
```

If `py` is unavailable but `python` points to Python 3.12 or later, use:

```powershell
python -m venv .venv
```

Activate the environment and install the required dependency:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell does not allow the activation script to run, use the environment's interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If the project is stored under a very deep directory and `pip` reports a Windows path-length error, create the environment at a shorter path:

```powershell
$BookForgeVenv = Join-Path $env:USERPROFILE ".venvs\bookforge"
py -3.12 -m venv $BookForgeVenv
& "$BookForgeVenv\Scripts\python.exe" -m pip install -r requirements.txt
```

## Running BookForge

With the virtual environment active:

```powershell
python .\main.py
```

Without activating the local environment:

```powershell
.\.venv\Scripts\python.exe .\main.py
```

When using the shorter environment path shown above:

```powershell
& "$BookForgeVenv\Scripts\python.exe" .\main.py
```

## Build for Windows

Install the development requirements, then build the canonical one-folder GUI configuration:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-dev.txt
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm .\BookForge.spec
```

The build appears under:

```text
dist\BookForge\BookForge.exe
```

Run it with:

```powershell
.\dist\BookForge\BookForge.exe
```

`BookForge.spec` includes the Python runtime, PySide6 modules, application code, and BookForge assets. It creates a GUI executable without a console window. It deliberately does not include Calibre executables or DLLs.

## Calibre dependency

BookForge delegates conversion and metadata extraction to Calibre rather than implementing e-book parsers and a conversion engine:

```text
BookForge
    ↓
Calibre ebook-meta / ebook-convert
    ↓
converted e-book
```

Calibre is not bundled with BookForge. In source and packaged modes, BookForge looks for `ebook-convert` and `ebook-meta` in `PATH` and common Windows installation locations, including `C:\Program Files\Calibre2`. If `ebook-convert` is missing, the application still opens and displays a clear warning, but conversion cannot begin. If only `ebook-meta` is missing or metadata extraction fails for one file, that queue item remains convertible and its Metadata action reports that metadata is unavailable.

After installing Calibre, restart PowerShell and verify the command with:

```powershell
Get-Command ebook-convert
ebook-convert --version
Get-Command ebook-meta
ebook-meta --version
```

Calibre is open-source software distributed under GPLv3 and remains a separately installed dependency.

## Usage

1. Drop one or more supported books or documents onto the drop area, or click the drop area and select several files.
2. Choose an output format in each row. AZW3 is the default, except AZW3 sources default to EPUB to avoid a same-format conversion.
3. Wait for the row's **Metadata · Loading…** action to become available, then optionally open it to preview the cover and edit metadata. Separate multiple authors with semicolons and tags with commas. **Save** stores changes for that queue item, **Cancel** discards that dialog session, and **Reset** restores the values and cover extracted from the source.
4. Optionally choose a format under **Set every book to** and click **Apply**. Individual rows remain editable afterward.
5. Select the shared output folder if necessary. The first book's source folder is used by default.
6. Choose **Ask**, **Replace all**, or **Skip all** for existing output files.
7. Click **Convert all**. BookForge converts the ready items one at a time and continues after individual failures.
8. During conversion, use **Cancel current** to stop only the active book or **Cancel batch** to stop it and cancel every waiting book.
9. Expand **Details** to inspect bounded Calibre output. Use **Retry** or **Retry failed** to return unsuccessful items to Ready. Metadata overrides survive retry.
10. Use **Open file** or **Open folder** on any completed row.

Desktop shortcuts:

- Ctrl+O: add books with the multi-file picker
- Ctrl+Enter: convert all ready books when conversion is available
- Ctrl+Q: exit BookForge

BookForge remembers only application preferences: safe window geometry, a manually chosen output folder, the global output-format selection, the overwrite policy, interface language, and theme. It does not persist the queue, books, logs, metadata, or covers. If a saved window position is no longer visible after a monitor change, BookForge falls back to a centered window. If a saved output folder no longer exists, automatic first-book-folder behavior resumes.

**Ask** prompts for each existing output and offers Replace, Skip, or Cancel batch. **Replace all** replaces existing outputs without further prompts, but never bypasses source-path or internal queue-collision protection. **Skip all** marks items whose outputs already exist as Skipped without starting Calibre.

Progress percentages are shown only when Calibre emits a recognizable integer value from 0% through 100%. Some conversions do not expose usable percentage output; those remain indeterminate rather than displaying estimated progress.

For example, converting `Dune.fb2` to AZW3 creates `Dune.azw3`, while converting `Dune.fb2` to FB2 uses the safe name `Dune_converted.fb2`. Same-format conversions never target the source path directly.

## Metadata and covers

When a book enters the queue, BookForge runs Calibre's `ebook-meta` asynchronously and reads its OPF metadata output. Supported editable fields are title, multiple authors, language, publisher, series, numeric series index, and multiple tags. Fields Calibre does not provide remain empty. Calibre may infer defaults for metadata-poor formats—for example, a TXT filename can become its title—and can normalize values such as language codes.

The metadata dialog shows the extracted cover at its original aspect ratio, or a neutral **No cover** placeholder. A replacement must be a readable JPG, JPEG, or PNG. BookForge copies accepted replacements into an isolated temporary folder for that queue item; it never edits the selected image or embeds it into the source book. Per-item cover files are removed when that item is removed, when the queue is cleared, or when BookForge exits.

Edits are held only in the in-memory queue and passed as verified `ebook-convert` options when the output is built. The original source path is always used as read-only conversion input, and conversion continues to use a temporary sibling output before atomically publishing the completed file. Metadata changes therefore affect only converted output files. Reset and Save remove an item's overrides when all values match the extracted original.

## Supported formats

Supported input formats:

- EPUB
- AZW3
- MOBI
- FB2
- DOCX
- TXT
- PDF

Supported output formats:

- AZW3
- EPUB
- MOBI
- PDF
- FB2
- DOCX
- TXT

Examples include:

- FB2 → AZW3
- MOBI → EPUB
- TXT → PDF
- AZW3 → EPUB
- DOCX → TXT

BookForge does not artificially restrict input/output combinations. The practical availability and quality of a conversion depend on Calibre and the contents of the source file. PDF input can be less predictable because it is usually fixed-layout.

## Development status

BookForge 0.10.0 adds complete English, German, and Russian interface localization; live language switching; and persistent System, Light, and Dark themes. It also refines spacing, empty-queue presentation, focus and disabled states, menus, dialogs, and compact queue controls while retaining the native title bar and established BookForge style. Metadata, cover, batch, cancellation, progress, retry, overwrite, and transactional output behavior remain in place.

A real sequential batch has been verified on Windows with a separately installed copy of Calibre, including generated TXT → EPUB and TXT → PDF fixtures with spaces and Cyrillic characters in their paths. A generated TXT → EPUB metadata smoke test also verified an overridden title, author, generated PNG cover, and byte-for-byte source preservation. Completed rows retain **Open file** and **Open folder** actions.

The canonical PyInstaller one-folder build was also launched directly on Windows without a console. Its drop-area picker queued additional generated TXT files, Calibre metadata controls opened successfully, and a two-book TXT → EPUB batch produced non-empty outputs while leaving both sources unchanged. The completed output actions were enabled and invoked, and window geometry persisted across a packaged-app restart.

The other listed formats and input/output combinations are supported by the current interface and conversion pipeline, but they have not all been manually verified with real books yet. Generated build and smoke-test results are environment-specific and should be repeated before distributing a release.

## Current limitations

- Percentage progress depends on the text emitted by Calibre and is not available for every conversion.
- Progress is the current item's progress, not a computed whole-batch percentage.
- Logs are intentionally limited to the most recent 64,000 characters per item.
- The queue is in memory only and is not restored after restarting BookForge.
- Conversions run sequentially; parallel conversion is intentionally not implemented.
- Advanced Calibre conversion options are not exposed in the interface.
- Metadata extraction and output behavior depend on what Calibre supports for each input/output format. Metadata-poor formats can receive Calibre-inferred defaults, and Calibre may normalize values such as language codes.
- BookForge passes changed, non-empty metadata through Calibre's supported conversion options. Reliably clearing an existing field to an empty value is not supported in this phase and Calibre may retain the source value.
- Replacing a cover is supported; explicitly removing an existing cover is not exposed because it cannot be applied consistently across the supported formats.
- The one-folder build has no installer, code signing, or automatic update mechanism yet.
- The original development icon should receive a final visual review before 1.0.
- There is no conversion history, library database, Send to Kindle integration, or device synchronization.
- Calibre must be installed separately.

## DRM

BookForge does not bypass or remove DRM. DRM-protected books are outside the scope of the application.
