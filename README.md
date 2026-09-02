# BookForge

## Overview

BookForge is a local desktop application for converting e-books and documents between common formats. It uses Calibre's `ebook-convert` command-line tool to produce the selected output format.

The application is built with Python and PySide6 and is currently developed primarily for Windows 10 and Windows 11.

## Features

- Add multiple EPUB, AZW3, MOBI, FB2, DOCX, TXT, and PDF files through a multi-select file dialog or drag and drop.
- Mix input formats in one in-memory conversion queue.
- Choose AZW3, EPUB, MOBI, PDF, FB2, DOCX, or TXT separately for every queued book.
- Apply one output format to the whole queue, then adjust individual rows as needed.
- Process the queue sequentially in one worker thread so the interface remains responsive and Calibre processes do not run concurrently.
- Use one shared output directory, initially set from the first queued book.
- Track Ready, Waiting, Converting, Completed, and Failed states independently for every item.
- Confirm before replacing each existing output file.
- Use a safe `_converted` filename whenever the input and output formats match.
- Open a completed file or its containing folder directly from its queue row.
- Skip duplicate physical source paths already present in the queue.
- Handle missing files, unavailable folders, Calibre errors, and missing output files with concise messages.

## Requirements

- Windows 10 or Windows 11
- Python 3.12 or later
- [Calibre](https://calibre-ebook.com/) installed separately, with `ebook-convert` available
- PySide6 Essentials, installed from `requirements.txt`

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

## Calibre dependency

BookForge delegates conversion to Calibre rather than implementing an e-book conversion engine:

```text
BookForge
    ↓
Calibre ebook-convert
    ↓
converted e-book
```

The current development version requires Calibre to be installed separately. Calibre is not bundled with BookForge. At startup, BookForge automatically looks for `ebook-convert` in `PATH` and in common Calibre installation locations on Windows. If it is not found, the application still opens and displays a clear warning, but conversion cannot begin.

After installing Calibre, restart PowerShell and verify the command with:

```powershell
Get-Command ebook-convert
ebook-convert --version
```

Calibre is open-source software distributed under GPLv3. Packaging and distribution of the conversion engine will be addressed in a later release phase.

## Usage

1. Drop one or more supported books or documents onto the drop area, or use **Add books** and select several files.
2. Choose an output format in each row. AZW3 is the default, except AZW3 sources default to EPUB to avoid a same-format conversion.
3. Optionally choose a format under **Set every book to** and click **Apply**. Individual rows remain editable afterward.
4. Select the shared output folder if necessary. The first book's source folder is used by default.
5. Click **Convert all**. BookForge converts the pending items one at a time and continues after individual failures.
6. Use **Open file** or **Open folder** on any completed row.

For example, converting `Dune.fb2` to AZW3 creates `Dune.azw3`, while converting `Dune.fb2` to FB2 uses the safe name `Dune_converted.fb2`. Same-format conversions never target the source path directly.

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

BookForge 0.4.0 is currently at Phase 4: a scrollable multi-book queue, mixed inputs, per-book output formats, sequential batch processing, duplicate prevention, per-item status and error reporting, and row-level result actions are implemented.

A real EPUB → PDF conversion has been manually verified on Windows with a separately installed copy of Calibre. BookForge successfully invoked Calibre's `ebook-convert`, the PDF output file was created, and the result panel correctly displayed the completed filename, output path, **Open file**, and **Open folder** actions.

The other listed formats and input/output combinations are supported by the current interface and conversion pipeline, but they have not all been manually verified with real books yet.

## Current limitations

- Conversion cannot currently be cancelled after it starts.
- Calibre progress is represented by a busy indicator rather than a parsed percentage.
- Existing output files use an ask-for-each-file policy; batch-wide replace and skip policies are not exposed yet.
- The queue is in memory only and is not restored after restarting BookForge.
- Conversions run sequentially; parallel conversion is intentionally not implemented.
- Advanced Calibre conversion options are not exposed in the interface.
- There is no metadata editor, cover preview, conversion history, or packaged executable.
- Calibre must be installed separately.

## DRM

BookForge does not bypass or remove DRM. DRM-protected books are outside the scope of the application.
