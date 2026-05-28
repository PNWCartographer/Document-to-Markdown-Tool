# Installer and Uninstaller Requirements

## Installer Goal
The installer should make the tool easy for a non technical user to install on Windows.

## Installer File
The installer is an InnoSetup script compiled into a Windows `.exe` installer:

```text
installer/doctomarkdown.iss
```

The build is automated via `installer/build_installer.bat`, which runs PyInstaller to create the frozen application and then InnoSetup to compile the final installer executable.

## Installer Requirements
The installer should:
- Request administrator rights if needed
- Install required files into Program Files
- Install all required local dependencies (bundled by PyInstaller)
- Create required folders
- Ask whether the user wants a desktop shortcut
- Ask whether the user wants a Start Menu shortcut
- Create shortcuts when selected
- Confirm installation success
- Auto close when complete if practical

## Install Location
Install location:

```text
C:\Program Files\Doc to Markdown\
```

(InnoSetup `{autopf}\Doc to Markdown`)

## Installed Folder Structure
Installed structure:

```text
Doc to Markdown\
  app\
  config\
  assets\
```

## Uninstaller Goal
The uninstaller should remove the tool cleanly from the user's system.

Uninstallation is handled natively by InnoSetup. There is no separate uninstaller script or folder. The uninstaller is registered in Windows Add/Remove Programs during installation.

## Uninstaller Requirements
The uninstaller should:
- Request administrator rights if needed
- Remove installed application files
- Remove desktop shortcut if created
- Remove Start Menu shortcut if created
- Remove installed tool folder from Program Files
- Confirm removal
- Auto close when complete if practical

## Data Safety Question
Before deleting logs, settings, or output files, the uninstaller should consider whether user created output should be preserved or deleted. If output files are stored inside the install directory, the uninstaller should warn the user before deleting them.

Recommended stop gap:

```text
The uninstall process found output files or logs. Do you want to delete them too?
```

## Dependency Safety
The uninstaller should avoid removing shared system dependencies that may be used by other applications unless the dependency was installed only for this tool and can be safely removed.

## Bundled Dependencies

The installer must bundle the following key dependencies (managed via PyInstaller spec and requirements.txt):

### OCR and PDF Processing
- **RapidOCR** (Apache 2.0) — ONNX-based OCR using PaddleOCR models. Replaces PaddlePaddle for smaller install size and cross-platform GPU support.
- **ONNX Runtime** — inference engine for RapidOCR models. Includes GPU execution providers (CUDA, DirectML) when available.
- **ocrmypdf** (MPL-2.0) — Searchable PDF creation engine. Adds invisible OCR text layer to PDFs.
- **Tesseract OCR** — traditional OCR fallback. Installed as an external binary (Windows installer downloaded by setup.py).

### System Detection
- **psutil** — CPU and RAM detection for performance auto-configuration.
- **nvidia-ml-py** (optional) — NVIDIA GPU detection (imported as `pynvml`). Graceful fallback if not installed or no NVIDIA GPU present.

### Previously Bundled (Removed)
- **PaddlePaddle** — replaced by RapidOCR (ONNX Runtime). No longer required.
- **PaddleOCR** — replaced by RapidOCR. No longer required.

### macOS-Specific (Not Bundled in Windows Installer)
- **ocrmac** — Apple Vision Framework OCR wrapper. Installed separately on macOS.
- **ocrmypdf-appleocr** — ocrmypdf plugin for Apple Vision. Installed separately on macOS.

## Cross-Platform Installer Notes
The current installer targets Windows (InnoSetup-based .exe installer). macOS and Linux installers are planned as a separate milestone. The Python setup script (`setup.py`) supports all three platforms for development use.
