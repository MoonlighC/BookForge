# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

project_root = Path(SPECPATH)
icon_path = project_root / "assets" / "bookforge.ico"
version_namespace = {}
exec(
    (project_root / "bookforge" / "__init__.py").read_text(encoding="utf-8"),
    version_namespace,
)
__version__ = version_namespace["__version__"]
version_tuple = tuple(int(part) for part in __version__.split(".")) + (0,)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_tuple, prodvers=version_tuple),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("CompanyName", "Christian Rieb"),
                        StringStruct("FileDescription", "BookForge"),
                        StringStruct("FileVersion", __version__),
                        StringStruct("InternalName", "BookForge"),
                        StringStruct(
                            "LegalCopyright",
                            "Copyright (c) 2026 Christian Rieb",
                        ),
                        StringStruct("OriginalFilename", "BookForge.exe"),
                        StringStruct("ProductName", "BookForge"),
                        StringStruct("ProductVersion", __version__),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(project_root / "assets"), "assets")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Qt's Windows wheel links to the unsuffixed ICU API provided by Windows.
# Do not let an unrelated development tool on PATH contribute its private,
# version-suffixed ICU DLL under the same filename and shadow the system copy.
path_derived_icu = {"icuuc.dll", "icudt78.dll"}
a.binaries = [
    entry for entry in a.binaries if Path(entry[0]).name.lower() not in path_derived_icu
]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BookForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
    version=version_info,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BookForge",
)
