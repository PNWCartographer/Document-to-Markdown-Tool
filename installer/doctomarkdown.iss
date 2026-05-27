; ============================================================
; Doc to Markdown — InnoSetup Installer Script
; by Darksquare  |  https://darksquare.dev
;
; Prerequisites:
;   1. Run PyInstaller to produce dist\DocToMarkdown\
;   2. Install Inno Setup 6+ from https://jrsoftware.org/isinfo.php
;   3. Compile this script:
;        iscc installer\doctomarkdown.iss
;
; Output: installer\Output\DocToMarkdown_Setup_1.0.0.exe
; ============================================================

#define MyAppName       "Doc to Markdown"
#define MyAppVersion    "1.0.0"
#define MyAppPublisher  "Darksquare"
#define MyAppURL        "https://darksquare.dev"
#define MyAppExeName    "DocToMarkdown.exe"
#define MyAppCopyright  "Copyright (c) 2025 Darksquare. All rights reserved."

[Setup]
; Basic identity
AppId={{E8F3A1B2-7C4D-4E5F-9A6B-1D2E3F4A5B6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright={#MyAppCopyright}

; Paths
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=DocToMarkdown_Setup_{#MyAppVersion}

; Installer appearance
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\DocToMarkdown.exe
UninstallDisplayName={#MyAppName}
WizardStyle=modern
WizardSizePercent=110
;WizardImageFile=compiler:WizModernImage-IS.bmp
;WizardSmallImageFile=compiler:WizModernSmallImage-IS.bmp

; Compression (LZMA2/ultra for smallest installer)
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Privileges
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; License display
LicenseFile=..\LICENSE

; Minimum Windows version (Windows 10)
MinVersion=10.0

; Uninstaller
Uninstallable=yes
CreateUninstallRegKey=yes

; Misc
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
AllowNoIcons=yes
CloseApplications=force
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; ============================================================
; Task checkboxes shown during installation
; ============================================================
[Tasks]
Name: "desktopicon";  Description: "Create a &desktop shortcut";       GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "startmenu";    Description: "Create a &Start Menu shortcut";    GroupDescription: "Additional shortcuts:"; Flags: checked
Name: "viewreadme";   Description: "View &README after installation";  GroupDescription: "After installation:";   Flags: unchecked

; ============================================================
; Files to install
; ============================================================
[Files]
; Main application (PyInstaller one-folder output)
Source: "..\dist\DocToMarkdown\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentation files (also bundled inside dist, but ensure top-level copies)
Source: "..\README.md";              DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE";                DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_LICENSES";   DestDir: "{app}"; Flags: ignoreversion

; Icon for shortcuts
Source: "..\assets\app_icon.ico";    DestDir: "{app}\assets"; Flags: ignoreversion

; ============================================================
; Shortcuts
; ============================================================
[Icons]
; Start Menu (when task selected)
Name: "{group}\{#MyAppName}";            Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: startmenu
Name: "{group}\Uninstall {#MyAppName}";  Filename: "{uninstallexe}";       Tasks: startmenu

; Desktop (when task selected)
Name: "{commondesktop}\{#MyAppName}";    Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: desktopicon

; ============================================================
; Registry — Add/Remove Programs metadata
; ============================================================
[Registry]
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version";     ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

; ============================================================
; Post-install action: open README
; ============================================================
[Run]
Filename: "notepad.exe"; Parameters: """{app}\README.md"""; Description: "View README"; Flags: nowait postinstall skipifsilent shellexec; Tasks: viewreadme

; ============================================================
; Uninstaller — clean removal of all files
; ============================================================
[UninstallDelete]
; Remove any runtime-generated files (settings, logs, cache)
Type: filesandordirs; Name: "{app}\*"
Type: dirifempty;     Name: "{app}"

; Remove AppData folder created by the app (settings, license data)
Type: filesandordirs; Name: "{localappdata}\DocToMarkdown"

[Code]
// ── Confirm AppData deletion during uninstall ──
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDataDir := ExpandConstant('{localappdata}\DocToMarkdown');
    if DirExists(AppDataDir) then
    begin
      if MsgBox('Doc to Markdown found user data (settings, license, logs) in:' + #13#10 +
                AppDataDir + #13#10#13#10 +
                'Do you want to remove this data as well?',
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        DelTree(AppDataDir, True, True, True);
      end;
    end;
  end;
end;
