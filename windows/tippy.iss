; Inno Setup recipe: turns the PyInstaller folder (dist\Tippy) into ONE installer file, Tippy-Setup.exe.
; Built in CI by .github/workflows/windows-app.yml; locally: windows\build.bat (needs Inno Setup).
; The installer needs no administrator rights: it installs for the current user only.
#define AppVersion GetEnv("TIPPY_VERSION")

[Setup]
AppId={{6F0E5D3C-2B7A-4C1E-9D55-7A1B3F0C2E11}
AppName=Tippy
AppVersion={#AppVersion}
AppPublisher=Tippy
DefaultDirName={localappdata}\Programs\Tippy
DefaultGroupName=Tippy
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Tippy-Setup-{#AppVersion}
SetupIconFile=Tippy.ico
UninstallDisplayIcon={app}\Tippy.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Put a Tippy icon on the desktop"; Flags: checkedonce

[Files]
Source: "..\dist\Tippy\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{userprograms}\Tippy"; Filename: "{app}\Tippy.exe"
Name: "{userdesktop}\Tippy"; Filename: "{app}\Tippy.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Tippy.exe"; Description: "Start Tippy now"; Flags: nowait postinstall skipifsilent

; The family's data (progress, PIN, settings) is in %APPDATA%\Tippy and is deliberately NOT removed when Tippy is
; uninstalled or updated, so installing a newer version keeps everything.
