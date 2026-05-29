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
; Output: installer\Output\DocToMarkdown_Setup_1.2.0.exe
; ============================================================

#define MyAppName       "Doc to Markdown"
#define MyAppVersion    "1.2.0"
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
// ============================================================
// Optional Ghostscript guidance page (Searchable PDF feature)
//
// Ghostscript is NOT bundled (AGPL). This courtesy page points the
// user at the official download page. It is skipped entirely if
// Ghostscript is already installed, and never blocks installation.
// ============================================================
var
  GsPage: TWizardPage;
  GsStatusLabel: TNewStaticText;

function GsInDir(BaseDir: String): Boolean;
var
  FindRec: TFindRec;
begin
  Result := False;
  if FindFirst(BaseDir + '\*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
          if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
            if FileExists(BaseDir + '\' + FindRec.Name + '\bin\gswin64c.exe') or
               FileExists(BaseDir + '\' + FindRec.Name + '\bin\gswin32c.exe') then
            begin
              Result := True;
              Exit;
            end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

function GhostscriptInstalled(): Boolean;
begin
  Result := GsInDir(ExpandConstant('{commonpf}\gs')) or
            GsInDir(ExpandConstant('{commonpf32}\gs'));
end;

procedure UpdateGsStatus();
begin
  if GhostscriptInstalled() then
  begin
    GsStatusLabel.Caption := 'Status: Ghostscript detected. Searchable PDF is ready.';
    GsStatusLabel.Font.Color := clGreen;
  end
  else
  begin
    GsStatusLabel.Caption := 'Status: not detected. The app will guide you when you first use Searchable PDF.';
    GsStatusLabel.Font.Color := clMaroon;
  end;
end;

procedure OpenGsPageClick(Sender: TObject);
var
  ErrorCode: Integer;
begin
  ShellExec('open', 'https://ghostscript.com/releases/gsdnld.html',
            '', '', SW_SHOW, ewNoWait, ErrorCode);
end;

procedure CheckGsClick(Sender: TObject);
begin
  UpdateGsStatus();
end;

procedure InitializeWizard();
var
  Desc: TNewStaticText;
  OpenBtn, CheckBtn: TNewButton;
begin
  GsPage := CreateCustomPage(wpInstalling, 'Optional: Searchable PDF',
    'Ghostscript enables the optional Searchable PDF feature');

  Desc := TNewStaticText.Create(GsPage);
  Desc.Parent := GsPage.Surface;
  Desc.Left := 0;
  Desc.Top := 0;
  Desc.Width := GsPage.SurfaceWidth;
  Desc.AutoSize := False;
  Desc.Height := ScaleY(72);
  Desc.WordWrap := True;
  Desc.Caption :=
    'Doc to Markdown is ready to use. The optional Searchable PDF feature ' +
    'also needs Ghostscript, a free tool that is not bundled with this app. ' +
    'You can install it now or later — the app will guide you the first time ' +
    'you use Searchable PDF.';

  OpenBtn := TNewButton.Create(GsPage);
  OpenBtn.Parent := GsPage.Surface;
  OpenBtn.Top := Desc.Top + Desc.Height + ScaleY(8);
  OpenBtn.Left := 0;
  OpenBtn.Width := ScaleX(200);
  OpenBtn.Height := ScaleY(28);
  OpenBtn.Caption := 'Open Ghostscript Download Page';
  OpenBtn.OnClick := @OpenGsPageClick;

  CheckBtn := TNewButton.Create(GsPage);
  CheckBtn.Parent := GsPage.Surface;
  CheckBtn.Top := OpenBtn.Top;
  CheckBtn.Left := OpenBtn.Left + OpenBtn.Width + ScaleX(8);
  CheckBtn.Width := ScaleX(110);
  CheckBtn.Height := ScaleY(28);
  CheckBtn.Caption := 'Check again';
  CheckBtn.OnClick := @CheckGsClick;

  GsStatusLabel := TNewStaticText.Create(GsPage);
  GsStatusLabel.Parent := GsPage.Surface;
  GsStatusLabel.Left := 0;
  GsStatusLabel.Top := OpenBtn.Top + OpenBtn.Height + ScaleY(14);
  GsStatusLabel.Width := GsPage.SurfaceWidth;
  GsStatusLabel.AutoSize := False;
  GsStatusLabel.Height := ScaleY(20);
  UpdateGsStatus();
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  // Skip the Ghostscript guidance page if it's already installed.
  if (GsPage <> nil) and (PageID = GsPage.ID) then
    Result := GhostscriptInstalled();
end;

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
