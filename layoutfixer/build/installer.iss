; installer.iss — Inno Setup script for LayoutFixer
; Build with: ISCC.exe build\installer.iss  (from the layoutfixer\ directory)
; Requires Inno Setup 6 (https://jrsoftware.org/isinfo.php)

#define AppName "LayoutFixer"
#define AppVersion "1.0.0"
#define AppPublisher "LayoutFixer"
#define AppURL "https://github.com/your-username/layoutfixer"
#define AppExeName "LayoutFixer.exe"

[Setup]
AppId={{A7B3C2D1-E4F5-6789-ABCD-EF0123456789}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; No admin rights required — installs to user's own AppData
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
LicenseFile=LICENSE.txt
OutputDir=Output
OutputBaseFilename=LayoutFixer_Setup_v{#AppVersion}
SetupIconFile=..\assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Start with Windows is checked by default — core value prop of the app
Name: "startupentry"; Description: "Start LayoutFixer with Windows"; GroupDescription: "Options:";
; Start Menu shortcut is checked by default
Name: "startmenu"; Description: "Add to Start Menu"; GroupDescription: "Options:";
; Desktop shortcut is opt-in
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Options:"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: startmenu
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Start with Windows — writes to HKCU so no admin required
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"""; Flags: uninsdeletevalue; Tasks: startupentry

[Run]
; Launch after install — "Launch LayoutFixer now" checkbox, checked by default
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Kill any running instance before uninstalling files
Filename: "taskkill"; Parameters: "/f /im {#AppExeName}"; Flags: runhidden; RunOnceId: "KillLayoutFixer"
