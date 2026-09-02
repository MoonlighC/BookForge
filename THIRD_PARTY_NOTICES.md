# Third-party notices

BookForge's own source code is licensed under the MIT License. The following
projects retain their own copyrights and licenses.

## Python

The standalone Windows distribution includes the Python runtime. Python is
developed by the Python Software Foundation and distributed under the Python
Software Foundation License Version 2. See
<https://docs.python.org/3/license.html>.

## PySide6 and Qt

BookForge uses PySide6, the official Qt for Python bindings, and Qt libraries.
The community edition is available under LGPLv3/GPLv3; commercial licensing is
also available from The Qt Company. BookForge uses dynamically linked Qt
libraries supplied by the PySide6 Essentials package. See
<https://doc.qt.io/qtforpython-6/> and
<https://doc.qt.io/qt-6/licensing.html>.

Qt and Qt for Python distributions also contain third-party components under
their respective licenses. See the Qt for Python license notices at
<https://doc.qt.io/qtforpython-6/licenses.html>.

## Calibre

Calibre is free and open-source software distributed under the GNU General
Public License version 3. Calibre is **not bundled or redistributed with
BookForge**. It is an external dependency that users install separately.
BookForge invokes Calibre's `ebook-convert` and `ebook-meta` command-line tools
when they are installed. See <https://calibre-ebook.com/> and
<https://github.com/kovidgoyal/calibre/blob/master/LICENSE>.

## PyInstaller

The standalone Windows executable is assembled with PyInstaller. PyInstaller
is distributed under GPLv2 with a special exception that permits distributing
bundled applications under the application's own license. See
<https://pyinstaller.org/en/stable/license.html>.

## Inno Setup

The optional Windows installer is built with Inno Setup. Inno Setup retains
its own copyright and license terms. See <https://jrsoftware.org/isinfo.php>.
