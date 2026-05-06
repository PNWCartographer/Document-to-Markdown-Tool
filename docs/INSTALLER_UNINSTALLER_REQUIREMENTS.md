# Installer and Uninstaller Requirements

## Installer Goal
The installer should make the tool easy for a non technical user to install on Windows.

## Installer File
The project should include an installer script, likely named:

```text
Installer.bat
```

## Installer Requirements
The installer should:
- Request administrator rights if needed
- Install required files into Program Files
- Install all required local dependencies
- Create required folders
- Ask whether the user wants a desktop shortcut
- Ask whether the user wants a Start Menu shortcut
- Create shortcuts when selected
- Confirm installation success
- Auto close when complete if practical

## Install Location
Recommended install location:

```text
C:\Program Files\Documentation to Markdown Converter Tool\
```

## Installed Folder Structure
Recommended installed structure:

```text
Documentation to Markdown Converter Tool\
  app\
  config\
  logs\
  output\
  assets\
  uninstaller\
```

## Uninstaller Goal
The uninstaller should remove the tool cleanly from the user's system.

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
