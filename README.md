# BookForge

## Overview

BookForge is a local desktop application for converting e-books. The current development version accepts an EPUB file and uses Calibre's `ebook-convert` command-line tool to produce the selected output format.

The application is built with Python and PySide6 and is currently developed primarily for Windows 10 and Windows 11.

## Features

- Select an EPUB through a file dialog or drag and drop.
- Convert one book at a time to AZW3, EPUB, MOBI, PDF, FB2, DOCX, or TXT.
- Run conversions outside the GUI thread so the application remains responsive.
- Use the source folder as the default output folder, with an option to choose another location.
- Confirm before replacing an existing output file.
- Use a safe `_converted` filename when converting EPUB to EPUB.
- Display the completed filename and output path in a result panel.
- Open the converted file or its containing folder from the result panel.
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

1. Drop an EPUB onto the selection area, or click the area and browse for a file.
2. Select an output format. AZW3 is the default.
3. Select an output folder if necessary. The source folder is used by default.
4. Click the conversion button and wait for the operation to complete.
5. Use **Open file** or **Open folder** in the result panel when the conversion succeeds.

For example, converting `Dune.epub` to AZW3 creates `Dune.azw3`. EPUB-to-EPUB conversion uses a safe name such as `Dune_converted.epub`, preventing accidental replacement of the source file.

## Supported conversions

- EPUB → AZW3
- EPUB → EPUB
- EPUB → MOBI
- EPUB → PDF
- EPUB → FB2
- EPUB → DOCX
- EPUB → TXT

The practical availability and quality of a conversion depend on Calibre and the contents of the source EPUB.

## Development status

BookForge is currently at Phase 2: multiple output formats, explicit overwrite confirmation, and result actions are implemented.

A real EPUB → PDF conversion has been manually verified on Windows with a separately installed copy of Calibre. BookForge successfully invoked Calibre's `ebook-convert`, the PDF output file was created, and the result panel correctly displayed the completed filename, output path, **Open file**, and **Open folder** actions.

The other listed output formats are supported by the current interface and conversion pipeline, but they have not all been manually verified with real books yet.

## Current limitations

- EPUB is the only supported input format.
- Only one book can be processed at a time.
- There is no batch processing or conversion queue.
- Conversion cannot currently be cancelled after it starts.
- Calibre progress is represented by a busy indicator rather than a parsed percentage.
- Advanced Calibre conversion options are not exposed in the interface.
- There is no metadata editor, cover preview, conversion history, or packaged executable.
- Calibre must be installed separately.

## DRM

BookForge does not bypass or remove DRM. DRM-protected books are outside the scope of the application.
