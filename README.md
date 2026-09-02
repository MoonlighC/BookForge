# BookForge

BookForge — локальное desktop-приложение для конвертации электронных книг. Оно использует установленный вместе с Calibre инструмент `ebook-convert`.

BookForge не обходит и не удаляет DRM. Защищённые DRM книги необходимо использовать в соответствии с лицензией и поддерживаемыми издателем приложениями.

## Требования

- Windows 10 или Windows 11;
- Python 3.12 или новее;
- [Calibre](https://calibre-ebook.com/) с доступным `ebook-convert`;
- PySide6 Essentials — официальный runtime с Qt Core/Gui/Widgets (устанавливается из `requirements.txt`).

## Установка

Откройте PowerShell в папке проекта и создайте виртуальное окружение:

```powershell
py -3.12 -m venv .venv
```

Если команда `py` недоступна, но `python` указывает на Python 3.12+, используйте:

```powershell
python -m venv .venv
```

Активируйте окружение и установите зависимости:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Если PowerShell запрещает запуск скрипта активации, можно выполнить команды напрямую через интерпретатор окружения:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Если проект расположен в очень глубокой папке и `pip` сообщает о превышении лимита длины пути Windows, создайте окружение по короткому пути:

```powershell
$BookForgeVenv = Join-Path $env:USERPROFILE ".venvs\bookforge"
py -3.12 -m venv $BookForgeVenv
& "$BookForgeVenv\Scripts\python.exe" -m pip install -r requirements.txt
```

## Запуск

С активированным виртуальным окружением:

```powershell
python .\main.py
```

Либо без активации:

```powershell
.\.venv\Scripts\python.exe .\main.py
```

При использовании короткого пути из примера выше:

```powershell
& "$BookForgeVenv\Scripts\python.exe" .\main.py
```

## Проверка Calibre

После установки Calibre перезапустите PowerShell и проверьте:

```powershell
Get-Command ebook-convert
ebook-convert --version
```

Если `ebook-convert` не добавлен в `PATH`, BookForge также проверяет стандартные папки установки Calibre на Windows. Приложение откроется и без Calibre, покажет предупреждение и не начнёт конвертацию.

## Использование

1. Перетащите EPUB в большую область окна или нажмите на неё и выберите файл.
2. При необходимости выберите папку результата. По умолчанию используется папка исходного EPUB.
3. Выберите выходной формат.
4. Нажмите кнопку **Convert**.
5. После завершения откройте готовый файл или его папку прямо из панели результата.

Для `Dune.epub` результат будет сохранён как `Dune.azw3`.

## Поддерживаемые конвертации

- EPUB → AZW3;
- EPUB → EPUB;
- EPUB → MOBI;
- EPUB → PDF;
- EPUB → FB2;
- EPUB → DOCX;
- EPUB → TXT.

При EPUB → EPUB используется безопасное имя вида `Dune_converted.epub`, поэтому исходная книга не перезаписывается. Фактическая возможность преобразования конкретной книги и качество результата зависят от Calibre и содержимого исходного EPUB.

## Ограничения Phase 2

- входной формат: только EPUB;
- обрабатывается одна книга за операцию;
- нет пакетной обработки, очереди и расширенных настроек Calibre;
- нет просмотра метаданных и обложки;
- нет встроенного обхода или удаления DRM;
- Calibre устанавливается пользователем отдельно.
